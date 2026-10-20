import aubellhop as bh
import numpy as np
import pandas as pd
import pytest
import scipy.signal as sp_signal

FS = 200000.0
FC = 20000.0


def _arrivals(times, phases, amps=None, freq=FC):
    amps = np.ones(len(times)) if amps is None else np.asarray(amps)
    return pd.DataFrame({
        'time_of_arrival': times,
        'arrival_amplitude': amps * np.exp(1j * np.deg2rad(phases)),
        'arrival_phase': phases,
        'frequency': freq,
    })


def _envelope(t, t0=1e-3, width=1e-4):
    return np.exp(-0.5 * ((t - t0) / width) ** 2)


def _pulse(t, t0=1e-3):
    return _envelope(t, t0) * np.cos(2 * np.pi * FC * (t - t0))


def test_phase_shifts_on_pulse():
    t = np.arange(400) / FS
    x = _pulse(t)
    hx = np.imag(sp_signal.hilbert(x))
    for phase, expected in [(0.0, x), (180.0, -x), (90.0, -hx)]:
        y = bh.arrivals_to_timeseries(_arrivals([0.5], [phase]), x, FS)
        assert len(y) == len(x)
        assert np.allclose(y, expected, atol=1e-6)


def test_fractional_delay():
    t = np.arange(600) / FS
    x = _pulse(t)
    tau = 1e-4 + 0.37 / FS
    y = bh.arrivals_to_timeseries(_arrivals([0.2, 0.2 + tau], [0.0, 0.0], [1.0, 0.5]), x, FS)
    t_out = np.arange(len(y)) / FS
    assert len(y) == len(x) + int(np.ceil(tau * FS))
    assert np.allclose(y, _pulse(t_out) + 0.5 * _pulse(t_out, 1e-3 + tau), atol=1e-6)


def test_baseband_matches_passband():
    t = np.arange(600) / FS
    arr = _arrivals([0.3, 0.3 + 1.23e-4, 0.3 + 2.5e-4], [0.0, 180.0, 117.0], [1.0, 0.6, 0.3])
    y = bh.arrivals_to_timeseries(arr, _envelope(t) * np.cos(2 * np.pi * FC * t), FS)
    y_bb = bh.arrivals_to_timeseries(arr, _envelope(t).astype(complex), FS, baseband=True)
    t_out = np.arange(len(y)) / FS
    assert np.allclose(y, np.real(y_bb * np.exp(2j * np.pi * FC * t_out)), atol=1e-6)


def test_baseband_impulse_response_matches_arrival_amplitude():
    env = bh.Environment()
    arr = bh.compute_arrivals(env)
    fs = 1e7
    ir = bh.arrivals_to_impulse_response(arr, fs=fs, abs_time=True, baseband=True)
    ndx = np.round(arr.time_of_arrival.to_numpy() * fs).astype(int)
    assert np.allclose(ir[ndx], arr.arrival_amplitude.to_numpy())


def test_timeseries_from_bellhop():
    env = bh.Environment()
    arr = bh.compute_arrivals(env)
    fs = 192000
    t = np.arange(0, 1e-3, 1 / fs)
    pulse = np.sin(2 * np.pi * env['frequency'] * t) * np.hanning(len(t))
    rx = bh.arrivals_to_timeseries(arr, pulse, fs)
    delay = arr.time_of_arrival.to_numpy() - arr.time_of_arrival.min()
    assert np.isrealobj(rx)
    assert len(rx) == len(pulse) + int(np.ceil(delay.max() * fs))
    # the direct path (phase 0) arrives first and nothing else overlaps its first half-period
    first = arr.time_of_arrival.idxmin()
    assert arr.arrival_phase[first] == 0
    n = int(fs / env['frequency'] / 2)
    assert np.allclose(rx[:n], np.abs(arr.arrival_amplitude[first]) * pulse[:n], atol=1e-9)


def test_timeseries_errors():
    arr = _arrivals([0.1], [0.0])
    with pytest.raises(ValueError, match="must be real"):
        bh.arrivals_to_timeseries(arr, np.ones(10, dtype=complex), FS)
    with pytest.raises(ValueError, match="Carrier frequency unknown"):
        bh.arrivals_to_timeseries(arr.drop(columns='frequency'), np.ones(10, dtype=complex), FS, baseband=True)
    multi = pd.concat([arr.assign(receiver_depth_ndx=0), arr.assign(receiver_depth_ndx=1)])
    with pytest.raises(ValueError, match="more than one source/receiver"):
        bh.arrivals_to_timeseries(multi, np.ones(10), FS)
