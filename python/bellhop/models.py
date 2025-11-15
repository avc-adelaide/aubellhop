"""Defining the Model Registry for bellhop.py to allow multiple BellhopSimulators to be run.

This model defines the class and then initialises it.
As this is a utility class, the initialised class operates
as a global container of methods and the `_models` register
of `BellhopSimulator` models.

See file `bellhop.py` for the class definition of `BellhopSimulator`.
"""


from __future__ import annotations

from typing import Any

from .constants import ModelDefaults
from .environment import Environment
from .bellhop import BellhopSimulator

class Models:
    """Registry for BellhopSimulator models.

    This is a *Utility Class* which consists of only class methods and a global registry
    of defined models.
    """

    _models: list[BellhopSimulator] = []  # class-level storage for all models

    @classmethod
    def init(cls) -> None:
        """Create default 2D and 3D models."""
        cls.new(name=ModelDefaults.name_2d, exe=ModelDefaults.exe_2d, dim=ModelDefaults.dim_2d)
        cls.new(name=ModelDefaults.name_3d, exe=ModelDefaults.exe_3d, dim=ModelDefaults.dim_3d)

    @classmethod
    def reset(cls) -> None:
        """Clear all models from the registry."""
        cls._models.clear()

    @classmethod
    def new(cls, name: str, **kwargs: Any) -> BellhopSimulator:
        """Instantiate a new Bellhop model and add it to the registry.

        Parameters
        ----------
        name : str
            The (unique) name of the BellhopSimulator model
        kwargs : Any
            Arguments to pass onto the BellhopSimulator constructor

        Returns
        -------
        BellhopSimulator
            The defined model which was just added to the registry.
        """
        for m in cls._models:
            if name == m.name:
                raise ValueError(f"Bellhop model with this name ('{name}') already exists.")
        model = BellhopSimulator(name=name, **kwargs)
        cls._models.append(model)
        return model

    @classmethod
    def list(cls, env: Environment | None = None, task: str | None = None, dim: int | None = None) -> list[str]:
        """List available models by name, maybe narrowed by env, task, and/or dimension."""
        if env is not None:
            env.check()
        rv: list[str] = []
        for m in cls._models:
            if m.supports(env=env, task=task, dim=dim):
                rv.append(m.name)
        return rv

    @classmethod
    def get(cls, name: str) -> BellhopSimulator:
        """Get a model by name.

        Parameters
        ----------
        name : str
            The name of the BellhopSimulator model

        Returns
        -------
        BellhopSimulator
            The first model in the registry which matches the specified name.
        """
        for m in cls._models:
            if m.name == name:
                return m
        raise KeyError(f"Unknown model: '{name}'")

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
        if debug:
            print(f'Models found: {models}')
        if len(models) > 0:
            return cls.get(models[0])
        raise ValueError('No suitable propagation model available')

    def __new__(cls, *args: Any, **kwargs: Any) -> "Models":
        raise TypeError("This utility class cannot be instantiated")

Models.init()
