"""Tests for the beam shift (Goos-Hanchen displacement) option on reflection.

BELLHOP enables it with 'S' in the 7th character of the run type. At each
reflection from an acousto-elastic half-space the ray is displaced along the
boundary by the Goos-Hanchen shift -d(arg R)/dk_x of the Rayleigh reflection
coefficient, and its travel time is increased to match.
"""

import numpy as np
import pytest

import aubellhop as bh
from aubellhop.constants import BHStrings

C_WATER = 1500.0
C_BOTTOM = 1700.0
RHO_BOTTOM = 1.5  # relative to water
DEPTH = 100.0


def _env(shift, **kw):
    params = dict(bottom_depth=DEPTH, soundspeed=C_WATER, bottom_soundspeed=C_BOTTOM,
                  bottom_density=RHO_BOTTOM * 1000, bottom_attenuation=0.0,
                  source_depth=50, receiver_depth=50, receiver_range=1000,
                  frequency=1000, beam_reflection_shift=shift)
    params.update(kw)
    return bh.Environment(**params)


def _goos_hanchen_shift(grazing_deg, freq):
    """Lateral shift -d(arg R)/dk_x for a lossless fluid half-space, by numerical differentiation."""
    k1 = 2 * np.pi * freq / C_WATER
    k2 = 2 * np.pi * freq / C_BOTTOM

    def phase(kx):
        g1 = np.sqrt(k1**2 - kx**2 + 0j)
        g2 = np.sqrt(k2**2 - kx**2 + 0j)
        return np.angle((RHO_BOTTOM * g1 - g2) / (RHO_BOTTOM * g1 + g2))

    kx = k1 * np.cos(np.deg2rad(grazing_deg))
    h = 1e-6 * k1
    return -(phase(kx + h) - phase(kx - h)) / (2 * h)


def _boundary_jumps(ray, depth):
    """Range jump between the incoming and reflected ray points at a boundary depth."""
    at = np.isclose(ray[:-1, 1], depth) & np.isclose(ray[1:, 1], depth)
    return np.diff(ray[:, 0])[at]


def _single_ray(shift, angle, **kw):
    env = _env(shift, beam_num=1, beam_angle_min=angle, beam_angle_max=angle, **kw)
    return bh.compute_rays(env).iloc[0]["ray"]


def test_run_type_flag_written_and_read(tmp_path):
    for shift in (False, True):
        fname = str(tmp_path / f"shift_{shift}")
        env = _env(shift)
        env.check()  # to_file expects a checked environment
        env.to_file(fname, task=BHStrings.rays)
        runtype = next(line for line in open(fname + ".env") if "RUN TYPE" in line).split("'")[1]
        assert (runtype[6:7] == "S") == shift
        assert runtype[0] == "R"
        assert bh.Environment.from_file(fname + ".env")["beam_reflection_shift"] is shift


def test_default_is_off():
    assert bh.Environment()["beam_reflection_shift"] is False


def test_print_file_reports_beam_shift(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for shift, msg in ((True, "Beam shift in effect"), (False, "No beam shift in effect")):
        bh.compute_rays(_env(shift, beam_num=1, beam_angle_min=20, beam_angle_max=20), fname_base="bs", debug=True)
        assert msg in (tmp_path / "bs.prt").read_text()


@pytest.mark.parametrize("angle, freq", [(5, 1000), (20, 1000), (20, 2000), (27, 1000), (40, 1000)])
def test_bottom_shift_matches_goos_hanchen(angle, freq):
    """Below the critical angle (28.07 deg) the shift is the Goos-Hanchen shift; above it, zero."""
    jumps = _boundary_jumps(_single_ray(True, angle, frequency=freq), DEPTH)
    assert len(jumps) > 0
    assert np.allclose(jumps, _goos_hanchen_shift(angle, freq), rtol=1e-5, atol=1e-6)


def test_no_shift_when_disabled():
    ray = _single_ray(False, 20)
    assert np.allclose(_boundary_jumps(ray, DEPTH), 0.0)


def test_no_shift_at_vacuum_surface():
    ray = _single_ray(True, 20)
    surface = _boundary_jumps(ray, 0.0)
    assert len(surface) > 0
    assert np.allclose(surface, 0.0)


def test_arrivals_with_beam_shift():
    """Shallow paths (below critical at every bounce) arrive at the same times: the added
    delay is cancelled by the shorter path, and a lossless bottom adds no group delay.
    Only the amplitudes of bottom-reflected arrivals change. Steep paths (above critical)
    have no shift, so they are unchanged."""
    off = bh.compute_arrivals(_env(False))
    on = bh.compute_arrivals(_env(True))
    cols = ["angle_of_departure", "time_of_arrival", "surface_bounces", "bottom_bounces"]
    for lo, hi in ((0, 23), (29, 90)):
        a, b = (x[x.angle_of_departure.abs().between(lo, hi)].sort_values(cols[:2]) for x in (off, on))
        assert len(a) > 2
        assert np.allclose(a[cols].to_numpy(), b[cols].to_numpy(), rtol=0, atol=1e-6)
        amp_a, amp_b = np.abs(a.arrival_amplitude.to_numpy()), np.abs(b.arrival_amplitude.to_numpy())
        bottom = a.bottom_bounces.to_numpy() > 0
        assert np.allclose(amp_a[~bottom], amp_b[~bottom])
        if lo == 0:
            assert not np.allclose(amp_a[bottom], amp_b[bottom])
        else:
            assert np.allclose(amp_a, amp_b)


def test_steep_reflections_keep_energy():
    """Regression: with a lossless bottom the beam-width update evaluated sign(0) * 0 = 0/0
    above the critical angle, so every steep bottom reflection lost all its energy."""
    kw = dict(beam_angle_min=33, beam_angle_max=40, beam_num=200)
    field_off = bh.compute_transmission_loss(_env(False, **kw)).iloc[0, 0]
    field_on = bh.compute_transmission_loss(_env(True, **kw)).iloc[0, 0]
    assert abs(field_off) > 0
    assert np.isclose(field_on, field_off)
