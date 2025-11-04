from __future__ import annotations

from typing import Any, Self

from .constants import ModelDefaults
from .environment import Environment
from .bellhop import BellhopSimulator

##############################################################################
#
# Copyright (c) 2025-, Will Robertson
# Copyright (c) 2018-2025, Mandar Chitre
#
# This file was originally part of arlpy, released under Simplified BSD License.
# It has been relicensed in this repository to be compatible with the Bellhop licence (GPL).
#
##############################################################################

"""Defining the Model Registry for bellhop.py to allow multiple BellhopSimulators to be run.
"""

class Models:
    """Registry for BellhopSimulator models.

    This is a *Utility Class* which consists of only class methods and a global registry
    of defined models.
    """

    _models: list[BellhopSimulator] = []  # class-level storage for all models

    @classmethod
    def init(cls) -> None:
        """Create default models."""
        cls.new(name=ModelDefaults.name_2d, exe=ModelDefaults.exe_2d, dim=ModelDefaults.dim_2d)
        cls.new(name=ModelDefaults.name_3d, exe=ModelDefaults.exe_3d, dim=ModelDefaults.dim_3d)

    @classmethod
    def new(cls, name: str, **kwargs: Any) -> BellhopSimulator:
        """Instantiate a new Bellhop model and add it to the registry."""
        for m in cls._models:
            if name == m.name:
                raise ValueError(f"Bellhop model with this name ('{name}') already exists.")
        model = BellhopSimulator(name=name, **kwargs)
        cls._models.append(model)
        return model

    @classmethod
    def list(cls, env: Environment | None = None, task: str | None = None, dim: int | None = None) -> list[str]:
        """List available models, maybe narrowed by env, task, and/or dimension."""
        if env is not None:
            env.check()
        rv: list[str] = []
        for m in cls._models:
            if m.supports(env=env, task=task, dim=dim):
                rv.append(m.name)
        return rv

    @classmethod
    def get(cls, name: str) -> BellhopSimulator:
        """Get a model by name."""
        for m in cls._models:
            if m.name == name:
                return m
        raise KeyError(f"Unknown model: '{name}'")

    @classmethod
    def reset(cls) -> None:
        """Clear all models."""
        cls._models.clear()

    @classmethod
    def select( cls,
                 env: Environment,
                task: str,
               model: str | None = None,
               debug: bool = False,
              ) -> BellhopSimulator:
        """Finds a model to use, or if a model is requested validate it.

        Parameters
        ----------
        env : dict
            The environment dictionary
        task : str
            The task to be computed
        model : str, optional
            Specified model to use
        debug : bool, default=False
            Whether to print diagnostics

        Returns
        -------
        BellhopSimulator
            The first model in the list which satisfies the input parameters. 

        """
        if model is not None:
            return cls.get(model)
        models = cls.list(env=env, task=task, dim=env._dimension)
        debug and print(f'Models found: {models}')
        if len(models) > 0:
            return cls.get(models[0])
        raise ValueError('No suitable propagation model available')

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        raise TypeError("This utility class cannot be instantiated")

Models.init()
