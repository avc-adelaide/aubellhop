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

from typing import Any, List

from .constants import ModelDefaults
from .environment import Environment
from .bellhop import BellhopSimulator

class ModelRegistry:
    """Registry for Bellhop simulator models."""

    def __init__(self) -> None:
        self._models: List[BellhopSimulator] = []
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Create default models."""
        self.new(name=ModelDefaults.name_2d, exe=ModelDefaults.exe_2d, dim=ModelDefaults.dim_2d)
        self.new(name=ModelDefaults.name_3d, exe=ModelDefaults.exe_3d, dim=ModelDefaults.dim_3d)

    def new(self, name: str, **kwargs: Any) -> BellhopSimulator:
        """Instantiate a new Bellhop model and add it to the registry."""
        for m in self._models:
            if name == m.name:
                raise ValueError(f"Bellhop model with this name ('{name}') already exists.")
        model = BellhopSimulator(name=name, **kwargs)
        self._models.append(model)
        return model

    def list(self, env: Environment | None = None, task: str | None = None, dim: int | None = None) -> List[str]:
        """List available models."""
        if env is not None:
            env.check()
        rv: List[str] = []
        for m in self._models:
            if m.supports(env=env, task=task, dim=dim):
                rv.append(m.name)
        return rv

    def get(self, name: str) -> BellhopSimulator:
        """Get a model by name."""
        for m in self._models:
            if m.name == name:
                return m
        raise KeyError(f"Unknown model: '{name}'")

    def reset(self) -> None:
        """Clear all models and reinitialize defaults (useful for testing)."""
        self._models.clear()
        self._initialize_defaults()

    def select( self,
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
        Bellhop
            The model function to evaluate its `.run()` method

        Notes
        -----
        The intention of this function is to allow multiple models to be "loaded" and the
        first appropriate model found is used for the computation.

        This is likely to be more useful once we extend the code to handle things like 3D
        bellhop models, GPU bellhop models, and so on.
        """
        if model is not None:
            return self.get(model)
        debug and print("Searching for propagation model:")
        for mm in self._models:
            if mm.supports(env=env, task=task, dim=env._dimension):
                debug and print(f'Model found: {mm.name}')
                return mm
        raise ValueError('No suitable propagation model available')

