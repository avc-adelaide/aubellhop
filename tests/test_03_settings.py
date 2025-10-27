import pytest
import bellhop as bh


def test_settings():
    """Test settings."""

    env1 = bh.Environment()
    env2 = bh.Environment(beam_angle_min=-45,frequency=100)

    env1.check()
    env2.check()

    for s in ["frequency","beam_angle_min"]:
        assert env1[s] is not None, f"Setting should be set ({s})"
        assert env1[s] != env2[s], f"Default setting should not equal manual setting ({s})"


def test_syntax():

    env = bh.Environment()
    env.frequency = 555
    assert env['frequency'] == 555, "Settings should just work"

    env['frequency'] = 666
    assert env.frequency == 666, "Settings should just work"

def test_errors():

    env = bh.Environment()
    with pytest.raises(KeyError, match="Unknown environment configuration parameter: 'quefrency'"):
        env.quefrency = 500

    env = bh.Environment()
    with pytest.raises(ValueError, match="Invalid value for 'soundspeed_interp'"):
        env.soundspeed_interp = "plines"
