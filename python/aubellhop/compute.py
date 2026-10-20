"""Computing wrappers for aubellhop.

These functions make use of the `Models` registry, selecting appropriate `BellhopSimulator` models (or loading explicitly request ones):

* `compute(env, ...)` — writes the environment to file and then executes an appropriate Bellhop model;

* `compute_from_file(model, filename)` uses specified model with pre-existing environment file.

The `compute()` function allows calculation with multiple environments, tasks, and models, and returns the results in a dictionary of metadata and results.

Simpler once-off wrapper functions are also provided for convenience (`compute_arrivals()` etc.).

"""

from __future__ import annotations

from typing import Any, cast
import numpy as np
import pandas as pd
import scipy.fft as sp_fft
import scipy.signal as sp_signal
from numpy.typing import NDArray

from .constants import BHStrings, EnvDefaults, FileExt
from .environment import Environment
from .models import Models

def compute_from_file(
                      model: str,
                      fname: str,
                      debug: bool = False
                     ) -> dict[str, Any]:
    """Compute Bellhop model directly from existing .env file.

    Parameters
    ----------
    model: str
        Name of model to run that has been defined in the `Models` registry.
    fname: str
        Filename of environment file (with or w/o extension).
    debug : bool
        Whether to print diagnostics to the console.

    Returns
    -------
    results : dict
        Dictionary of metadata and results.

    Notes
    -----
    The environment file is parsed simply to read the specified task; the bellhop executable is run on the original file "in place" in the filesystem. A copy of the parsed environment file is stored in the metadata.
    """

    ext = FileExt.env
    if fname.endswith(ext):
        nchar = len(ext)
        fname_base = fname[:-nchar]
    else:
        fname_base = fname
        fname = fname + ext

    model_fn = Models.get(model)
    env_tmp = Environment.from_file(fname)
    task = env_tmp['task']

    return {
             "name": env_tmp["name"],
             "model": model,
             "task": task,
             "results": model_fn.run(task, fname_base, rm_files=False, debug=debug),
             "env": env_tmp.copy(),
           }


def compute(
            env: Environment | list[Environment],
            model: Any | None = None,
            task: Any | None = None,
            debug: bool = False,
            fname_base: str | None = None,
            overwrite: bool = False,
           ) -> dict[str, Any] | tuple[list[dict[str, Any]], pd.DataFrame]:
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
    overwrite : bool, default=False
        If True, remove any existing working/output files that share the same `fname_base`.

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
    >>> import aubellhop as bh
    >>> env = bh.Environment.from_file("...")
    >>> output = bh.compute(env)
    >>> assert output['task'] == "arrivals"
    >>> bh.plot_arrivals(output['results'])

    Multiple tasks:
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> output, ind_df = bh.compute(env,task=["arrivals", "eigenrays"])
    >>> bh.plot_arrivals(output[0]['results'])
    """
    if isinstance(env, list):
        envs = cast(list[Environment], env)
    else:
        envs = [env]
    models_ = model if isinstance(model, list) else [model]
    tasks = task if isinstance(task, list) else [task]
    results: list[dict[str, Any]] = []
    this_env: Environment
    for this_env in envs:
        for this_model in models_:
            for this_task in tasks:
                if debug:
                    print(f"Using environment: {this_env['name']}")
                    print(f"Using model: {'[None] (default)' if this_model is None else this_model.get('name')}")
                    print(f"Using task: {this_task}")
                this_env.check()
                this_task = this_task or this_env.get('task')
                if this_task is None:
                    raise ValueError("Task must be specified in env or as parameter")
                model_fn = Models.select(this_env, this_task, this_model, debug)
                fname_base = model_fn.write_env(this_env, this_task, fname_base, overwrite=overwrite)
                results.append({
                       "name": this_env["name"],
                       "model": this_model,
                       "task": this_task,
                       "results": model_fn.run(this_task, fname_base, debug=debug),
                       "env": this_env.copy(),
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


def compute_arrivals(env: Environment, model: Any | None = None, debug: bool = False, fname_base: str | None = None, overwrite: bool = False) -> Any:
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
    overwrite : bool, default=False
        If True, remove any existing working/output files that share the same `fname_base`.

    Returns
    -------
    pandas.DataFrame
        Arrival times and coefficients for all transmitter-receiver combinations

    Examples
    --------
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> arrivals = bh.compute_arrivals(env)
    >>> bh.plot_arrivals(arrivals)
    """
    output = compute(env, model, BHStrings.arrivals, debug, fname_base, overwrite)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_eigenrays(env: Environment, source_depth_ndx: int = 0, receiver_depth_ndx: int = 0, receiver_range_ndx: int = 0, model: Any | None = None, debug: bool = False, fname_base: str | None = None, overwrite: bool = False) -> Any:
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
    overwrite : bool, default=False
        If True, remove any existing working/output files that share the same `fname_base`.

    Returns
    -------
    pandas.DataFrame
        Eigenrays paths

    Examples
    --------
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> rays = bh.compute_eigenrays(env)
    >>> bh.plot_rays(rays, width=1000)
    """
    env = env.copy()
    env.check()
    if np.size(env['source_depth']) > 1:
        env['source_depth'] = env['source_depth'][source_depth_ndx]
        env['source_ndepth'] = None  # count is recomputed on the next check()
    if np.size(env['receiver_depth']) > 1:
        env['receiver_depth'] = env['receiver_depth'][receiver_depth_ndx]
        env['receiver_ndepth'] = None
    if np.size(env['receiver_range']) > 1:
        env['receiver_range'] = env['receiver_range'][receiver_range_ndx]
        env['receiver_nrange'] = None
    output = compute(env, model, BHStrings.eigenrays, debug, fname_base, overwrite)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_rays(env: Environment, source_depth_ndx: int = 0, model: Any | None = None, debug: bool = False, fname_base: str | None = None, overwrite: bool = False) -> Any:
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
    overwrite : bool, default=False
        If True, remove any existing working/output files that share the same `fname_base`.

    Returns
    -------
    pandas.DataFrame
        Ray paths

    Examples
    --------
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> rays = bh.compute_rays(env)
    >>> bh.plot_rays(rays, width=1000)
    """
    env = env.copy()
    env.check()
    if np.size(env['source_depth']) > 1:
        env['source_depth'] = env['source_depth'][source_depth_ndx]
        env['source_ndepth'] = None  # count is recomputed on the next check()
    output = compute(env, model, BHStrings.rays, debug, fname_base, overwrite)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def compute_transmission_loss(env: Environment, source_depth_ndx: int = 0, mode: str | None = None, model: Any | None = None, debug: bool = False, fname_base: str | None = None, overwrite: bool = False) -> Any:
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
    overwrite : bool, default=False
        If True, remove any existing working/output files that share the same `fname_base`.

    Returns
    -------
    numpy.ndarray
        Complex transmission loss at each receiver depth and range

    Examples
    --------
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> tloss = bh.compute_transmission_loss(env, mode="incoherent")
    >>> bh.plot_transmission_loss(tloss, width=1000)
    """
    env = env.copy()
    task = mode or env.get("interference_mode") or EnvDefaults.interference_mode
    env['interference_mode'] = task
    env.check()
    if np.size(env['source_depth']) > 1:
        env['source_depth'] = env['source_depth'][source_depth_ndx]
        env['source_ndepth'] = None  # count is recomputed on the next check()
    output = compute(env, model, task, debug, fname_base, overwrite)
    assert isinstance(output, dict), "Single env should return single result"
    return output['results']

def _arrival_taps(arrivals: Any, abs_time: bool, baseband: bool, fc: float | None
                  ) -> tuple[NDArray[np.float64], NDArray[np.complex128]]:
    """Delays (s, relative to the output time origin) and complex tap coefficients of a set of arrivals."""
    pair_cols = [c for c in ('source_depth_ndx', 'receiver_depth_ndx', 'receiver_range_ndx') if c in arrivals.columns]
    if pair_cols and len(arrivals[pair_cols].drop_duplicates()) > 1:
        raise ValueError("Arrivals contain more than one source/receiver pair; select a single pair first")
    t = np.real(np.asarray(arrivals.time_of_arrival, dtype=np.complex128))
    amp = np.asarray(arrivals.arrival_amplitude, dtype=np.complex128)
    if 'arrival_phase' in arrivals.columns:
        amp = np.abs(amp) * np.exp(1j * np.deg2rad(np.asarray(arrivals.arrival_phase, dtype=np.float64)))
    delay = t - (0 if abs_time else np.min(t))
    if baseband:
        if fc is None:
            if 'frequency' not in arrivals.columns:
                raise ValueError("Carrier frequency unknown: pass fc or include a 'frequency' column")
            fc = float(np.asarray(arrivals.frequency)[0])
        amp = amp * np.exp(-2j * np.pi * fc * delay)
    return delay, amp


def arrivals_to_impulse_response(arrivals: Any, fs: float, abs_time: bool = False,
                                 baseband: bool = False, fc: float | None = None) -> Any:
    """Convert arrival times and coefficients to an impulse response.

    Parameters
    ----------
    arrivals : pandas.DataFrame
        Arrivals times (s) and coefficients for a single source/receiver pair
    fs : float
        Sampling rate (Hz)
    abs_time : bool, default=False
        Absolute time (True) or relative time (False)
    baseband : bool, default=False
        Return the complex baseband impulse response (True) or the passband one (False)
    fc : float, optional
        Carrier frequency (Hz) for the baseband response; defaults to the simulation frequency

    Returns
    -------
    numpy.ndarray
        Complex impulse response

    Notes
    -----
    If `abs_time` is set to True, the impulse response is placed such that
    the zero time corresponds to the time of transmission of signal.

    Each arrival contributes a tap at its delay, rounded to the nearest sample;
    arrivals that fall in the same sample are summed. Attenuation from the
    imaginary part of the delay is included, evaluated at the simulation frequency.

    The passband response has taps ``A * exp(i * phase)``. It applies to the analytic
    signal ``sa`` of a real passband transmission: ``y = Re(convolve(sa, ir))``.
    Taking the real part of the response first discards the phase shifts from
    reflections, so this is not the same as convolving a real signal with ``ir.real``.

    The baseband response has taps ``A * exp(i * phase) * exp(-i * 2 * pi * fc * delay)``
    and applies to a complex baseband signal ``b`` with carrier ``exp(i * 2 * pi * fc * t)``.

    Use :func:`arrivals_to_timeseries` to apply arrivals to a signal without rounding the delays.

    If the arrivals cover more than one source or receiver, select one pair first,
    e.g. ``arrivals[(arrivals.receiver_depth_ndx == 0) & (arrivals.receiver_range_ndx == 0)]``.

    Examples
    --------
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> arrivals = bh.compute_arrivals(env)
    >>> ir = bh.arrivals_to_impulse_response(arrivals, fs=192000)
    """
    delay, amp = _arrival_taps(arrivals, abs_time, baseband, fc)
    ndx = np.round(delay * fs).astype(int)
    ir = np.zeros(np.max(ndx) + 1, dtype=np.complex128)
    np.add.at(ir, ndx, amp)
    return ir


def arrivals_to_timeseries(arrivals: Any, signal: Any, fs: float, abs_time: bool = False,
                           baseband: bool = False, fc: float | None = None) -> Any:
    """Compute the received time series for a transmitted signal.

    Parameters
    ----------
    arrivals : pandas.DataFrame
        Arrivals times (s) and coefficients for a single source/receiver pair
    signal : array_like
        Transmitted signal sampled at `fs`: real passband, or complex baseband if `baseband` is True
    fs : float
        Sampling rate (Hz)
    abs_time : bool, default=False
        Absolute time (True) or relative time (False)
    baseband : bool, default=False
        Treat `signal` and the output as complex baseband (True) or real passband (False)
    fc : float, optional
        Carrier frequency (Hz) for baseband signals; defaults to the simulation frequency

    Returns
    -------
    numpy.ndarray
        Received signal: real for passband, complex for baseband.
        Its length is ``len(signal)`` plus the delay spread in samples.

    Notes
    -----
    Each arrival is applied as a gain ``A * exp(i * phase)`` on the analytic
    signal, so phase shifts from reflections are kept: a phase of 180 degrees
    inverts the pulse and 90 degrees gives its Hilbert transform
    (negated). Delays are
    applied exactly (including fractions of a sample) in the frequency domain.
    For baseband signals the output uses the carrier ``exp(i * 2 * pi * fc * t)``,
    so the passband equivalent is ``Re(y * exp(i * 2 * pi * fc * t))``.

    Reflection phases and attenuation are those computed at the simulation
    frequency, and the passband signal must be sampled above twice its highest frequency.

    Examples
    --------
    >>> import numpy as np
    >>> import aubellhop as bh
    >>> env = bh.Environment()
    >>> arrivals = bh.compute_arrivals(env)
    >>> fs = 192000
    >>> t = np.arange(0, 1e-3, 1 / fs)
    >>> pulse = np.sin(2 * np.pi * env['frequency'] * t) * np.hanning(len(t))
    >>> rx = bh.arrivals_to_timeseries(arrivals, pulse, fs)
    """
    x = np.asarray(signal)
    if x.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    if not baseband and np.iscomplexobj(x):
        raise ValueError("Passband signal must be real; set baseband=True for complex baseband signals")
    delay, amp = _arrival_taps(arrivals, abs_time, baseband, fc)
    nout = len(x) + int(np.ceil(np.max(delay) * fs))
    nfft = sp_fft.next_fast_len(nout + len(x))  # padding keeps fractional-delay tails from wrapping
    if baseband:
        spec = np.fft.fft(x.astype(np.complex128), nfft)
    else:
        spec = np.fft.fft(sp_signal.hilbert(x.astype(np.float64), nfft))
    f = np.fft.fftfreq(nfft, 1 / fs)
    h = np.zeros(nfft, dtype=np.complex128)
    for d, a in zip(delay, amp):
        h += a * np.exp(-2j * np.pi * f * d)
    y = np.fft.ifft(spec * h)[:nout]
    return y if baseband else np.real(y)
