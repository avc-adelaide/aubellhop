##############################################################################
#
# Copyright (c) 2025-, Will Robertson
# Copyright (c) 2018-2025, Mandar Chitre
#
# This file was originally part of arlpy, released under Simplified BSD License.
# It has been relicensed in this repository to be compatible with the Bellhop licence (GPL).
#
##############################################################################

"""Underwater acoustic propagation modeling toolbox.

This toolbox uses the Bellhop acoustic propagation model. For this model
to work, the complete bellhop.py package must be built and installed
and `bellhop.exe` should be in your PATH.
"""

from typing import Any, List, Tuple

import numpy as np
import pandas as pd

from bellhop.constants import BHStrings, EnvDefaults, ModelDefaults

# this format to explicitly mark the functions as public:
from bellhop.readers import read_ssp as read_ssp
from bellhop.readers import read_ati as read_ati
from bellhop.readers import read_bty as read_bty
from bellhop.readers import read_sbp as read_sbp
from bellhop.readers import read_trc as read_trc
from bellhop.readers import read_brc as read_brc

from bellhop.readers import read_shd as read_shd
from bellhop.readers import read_rays as read_rays
from bellhop.readers import read_arrivals as read_arrivals

from bellhop.environment import Environment
from bellhop.bellhop import BellhopSimulator

class ModelRegistry:
    """Registry for Bellhop simulator models."""
    
    def __init__(self):
        self._models: List[BellhopSimulator] = []
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Create default models."""
        self.new_model(name=ModelDefaults.name_2d, exe=ModelDefaults.exe_2d, dim=ModelDefaults.dim_2d)
        self.new_model(name=ModelDefaults.name_3d, exe=ModelDefaults.exe_3d, dim=ModelDefaults.dim_3d)
    
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
    
    def reset(self):
        """Clear all models and reinitialize defaults (useful for testing)."""
        self._models.clear()
        self._initialize_defaults()

    def select( self,
                 env: Environment,
                task: str,
               model: str | None = None,
               debug: bool = False,
              ) -> Any:
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


# Create a global instance for convenience
models = ModelRegistry()




def compute(
            env: Environment | List[Environment],
            model: Any | None = None,
            task: Any | None = None,
            debug: bool = False,
            fname_base: str | None = None
           ) ->   Any | Environment | Tuple[List[Environment], pd.DataFrame]:
    """Compute Bellhop task(s) for given model(s) and environment(s).

    Parameters
    ----------
    env : dict or list of dict
        Environment definition (which includes the task specification)
    model : str, optional
        Propagation model to use (None to auto-select)
    task : str or list of str, optional
        Optional task or list of tasks ("arrivals", etc.)
    debug : bool, default=False
        Generate debug information for propagation model
    fname_base : str, optional
        Base file name for Bellhop working files, default (None), creates a temporary file

    Returns
    -------
    dict
        Single run result (and associated metadata) if only one computation is performed.
    tuple of (list of dict, pandas.DataFrame)
        List of results and an index DataFrame if multiple computations are performed.

    Notes
    -----
    If any of env, model, and/or task are lists then multiple runs are performed
    with a list of dictionary outputs returned. The ordering is based on loop iteration
    but might not be deterministic; use the index DataFrame to extract and filter the
    output logically.

    Examples
    --------
    Single task based on reading a complete `.env` file:
    >>> import bellhop as bh
    >>> env = bh.Environment.from_file("...")
    >>> output = bh.compute(env)
    >>> assert output['task'] == "arrivals"
    >>> bh.plot_arrivals(output['results'])

    Multiple tasks:
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> output, ind_df = bh.compute(env,task=["arrivals", "eigenrays"])
    >>> bh.plot_arrivals(output[0]['results'])
    """
    envs = env if isinstance(env, list) else [env]
    models_ = model if isinstance(model, list) else [model]
    tasks = task if isinstance(task, list) else [task]
    results: List[Any] = []
    for this_env in envs:
        debug and print(f"Using environment: {this_env['name']}")
        for this_model in models_:
            debug and print(f"Using model: {'[None] (default)' if this_model is None else this_model.get('name')}")
            for this_task in tasks:
                debug and print(f"Using task: {this_task}")
                this_env.check()
                this_task = this_task or this_env.get('task')
                if this_task is None:
                    raise ValueError("Task must be specified in env or as parameter")
                model_fn = models.select(this_env, this_task, this_model, debug)
                results.append({
                       "name": this_env["name"],
                       "model": this_model,
                       "task": this_task,
                       "results": model_fn.run(this_env, this_task, debug, fname_base),
                      })
    assert len(results) > 0, "No results generated"
    index_df = pd.DataFrame([
        {
            "i": i,
            "name": r["name"],
            "model": getattr(r["model"], "name", str(r["model"])) if r["model"] is not None else None,
            "task": r["task"],
        }
        for i, r in enumerate(results)
    ])
    index_df.set_index("i", inplace=True)
    if len(results) > 1:
        return results, index_df
    else:
        return results[0]


def compute_arrivals(env: Environment, model: Any | None = None, debug: bool = False, fname_base: str | None = None) -> Any:
    """Compute arrivals between each transmitter and receiver.

    Parameters
    ----------
    env : dict
        Environment definition
    model : str, optional
        Propagation model to use (None to auto-select)
    debug : bool, default=False
        Generate debug information for propagation model
    fname_base : str, optional
        Base file name for Bellhop working files, default (None), creates a temporary file

    Returns
    -------
    pandas.DataFrame
        Arrival times and coefficients for all transmitter-receiver combinations

    Examples
    --------
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> arrivals = bh.compute_arrivals(env)
    >>> bh.plot_arrivals(arrivals)
    """
    output = compute(env, model, BHStrings.arrivals, debug, fname_base)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_eigenrays(env: Environment, source_depth_ndx: int = 0, receiver_depth_ndx: int = 0, receiver_range_ndx: int = 0, model: Any | None = None, debug: bool = False, fname_base: str | None = None) -> Any:
    """Compute eigenrays between a given transmitter and receiver.

    Parameters
    ----------
    env : dict
        Environment definition
    source_depth_ndx : int, default=0
        Transmitter depth index
    receiver_depth_ndx : int, default=0
        Receiver depth index
    receiver_range_ndx : int, default=0
        Receiver range index
    model : str, optional
        Propagation model to use (None to auto-select)
    debug : bool, default=False
        Generate debug information for propagation model
    fname_base : str, optional
        Base file name for Bellhop working files, default (None), creates a temporary file

    Returns
    -------
    pandas.DataFrame
        Eigenrays paths

    Examples
    --------
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> rays = bh.compute_eigenrays(env)
    >>> bh.plot_rays(rays, width=1000)
    """
    env.check()
    env = env.copy()
    if np.size(env['source_depth']) > 1:
        env['source_depth'] = env['source_depth'][source_depth_ndx]
    if np.size(env['receiver_depth']) > 1:
        env['receiver_depth'] = env['receiver_depth'][receiver_depth_ndx]
    if np.size(env['receiver_range']) > 1:
        env['receiver_range'] = env['receiver_range'][receiver_range_ndx]
    output = compute(env, model, BHStrings.eigenrays, debug, fname_base)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_rays(env: Environment, source_depth_ndx: int = 0, model: Any | None = None, debug: bool = False, fname_base: str | None = None) -> Any:
    """Compute rays from a given transmitter.

    Parameters
    ----------
    env : dict
        Environment definition
    source_depth_ndx : int, default=0
        Transmitter depth index
    model : str, optional
        Propagation model to use (None to auto-select)
    debug : bool, default=False
        Generate debug information for propagation model
    fname_base : str, optional
        Base file name for Bellhop working files, default (None), creates a temporary file

    Returns
    -------
    pandas.DataFrame
        Ray paths

    Examples
    --------
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> rays = bh.compute_rays(env)
    >>> bh.plot_rays(rays, width=1000)
    """
    env.check()
    if np.size(env['source_depth']) > 1:
        env = env.copy()
        env['source_depth'] = env['source_depth'][source_depth_ndx]
    output = compute(env, model, BHStrings.rays, debug, fname_base)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_transmission_loss(env: Environment, source_depth_ndx: int = 0, mode: str | None = None, model: Any | None = None, debug: bool = False, fname_base: str | None = None) -> Any:
    """Compute transmission loss from a given transmitter to all receviers.

    Parameters
    ----------
    env : dict
        Environment definition
    source_depth_ndx : int, default=0
        Transmitter depth index
    mode : str, optional
        Coherent, incoherent or semicoherent
    model : str, optional
        Propagation model to use (None to auto-select)
    debug : bool, default=False
        Generate debug information for propagation model
    fname_base : str, optional
        Base file name for Bellhop working files, default (None), creates a temporary file

    Returns
    -------
    numpy.ndarray
        Complex transmission loss at each receiver depth and range

    Examples
    --------
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> tloss = bh.compute_transmission_loss(env, mode=bh.incoherent)
    >>> bh.plot_transmission_loss(tloss, width=1000)
    """
    env = env.copy()
    task = mode or env.get("interference_mode") or EnvDefaults.interference_mode
    env['interference_mode'] = task
    debug and print(f"  {task=}")
    env.check()
    if np.size(env['source_depth']) > 1:
        env['source_depth'] = env['source_depth'][source_depth_ndx]
    output = compute(env, model, task, debug, fname_base)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def arrivals_to_impulse_response(arrivals: Any, fs: float, abs_time: bool = False) -> Any:
    """Convert arrival times and coefficients to an impulse response.

    Parameters
    ----------
    arrivals : pandas.DataFrame
        Arrivals times (s) and coefficients
    fs : float
        Sampling rate (Hz)
    abs_time : bool, default=False
        Absolute time (True) or relative time (False)

    Returns
    -------
    numpy.ndarray
        Impulse response

    Notes
    -----
    If `abs_time` is set to True, the impulse response is placed such that
    the zero time corresponds to the time of transmission of signal.

    Examples
    --------
    >>> import bellhop as bh
    >>> env = bh.Environment()
    >>> arrivals = bh.compute_arrivals(env)
    >>> ir = bh.arrivals_to_impulse_response(arrivals, fs=192000)
    """
    t0 = 0 if abs_time else min(arrivals.time_of_arrival)
    irlen = int(np.ceil((max(arrivals.time_of_arrival)-t0)*fs))+1
    ir = np.zeros(irlen, dtype=np.complex128)
    for _, row in arrivals.iterrows():
        ndx = int(np.round((row.time_of_arrival.real-t0)*fs))
        ir[ndx] = row.arrival_amplitude
    return ir

### Export module names for auto-importing in __init__.py

__all__ = [
    name for name in globals() if not name.startswith("_")  # ignore private names
]
