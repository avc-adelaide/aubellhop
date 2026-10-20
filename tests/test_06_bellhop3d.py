import pytest
import aubellhop as bh
import numpy as np

def test_model_new():
    """Just check that there are no import errors.
    """

    assert "bellhop3d" in bh.Models.supported(), "Bellhop3D model should exist"
    assert bh.Models.supported(dim=2) == ["bellhop"], "Model of dim 2 not found"
    assert bh.Models.supported(dim=3) == ["bellhop3d"], "Model of dim 3 not found"

def test_model_env():
    """Check we can switch between bellhop 2d & 3d easily.
    """

    env2d = bh.Environment(dimension="2D").check()
    env3d = bh.Environment(dimension="3D").check()

    assert env2d._dimension == 2
    assert env3d._dimension == 3

    assert bh.Models.supported(env=env2d) == ["bellhop"], "Model 2D not found"
    assert bh.Models.supported(env=env3d) == ["bellhop3d"], "Model 3D not found"


@pytest.mark.parametrize("dimension, flag", [("2D", ""), ("2.5D", "2"), ("3D", "3")])
@pytest.mark.parametrize("shift", [False, True])
def test_run_type_dimension_flag(tmp_path, dimension, flag, shift):
    """The 6th run-type character selects Nx2D ('2') or full 3D ('3'); Bellhop3D treats blank as Nx2D,
    so "3D" environments previously ran as Nx2D. The 7th character (beam shift) must stay in place."""
    env = bh.Environment(dimension=dimension, beam_reflection_shift=shift)
    env.check()
    fname = env.to_file(str(tmp_path / "dim"), task="coherent")
    runtype = next(line for line in open(fname + ".env") if "RUN TYPE" in line).split("'")[1]
    assert runtype[5:6].strip() == flag
    assert (runtype[6:7] == "S") == shift
    env_read = bh.Environment.from_file(fname + ".env")
    assert env_read["dimension"] == dimension
    assert env_read["beam_reflection_shift"] is shift


def test_read_blank_dimension_flag_3d(tmp_path):
    """A 3D env file with no 6th run-type character is Nx2D in Bellhop3D."""
    env = bh.Environment(dimension="2.5D")
    env.check()
    fname = env.to_file(str(tmp_path / "blank"), task="coherent")
    text = open(fname + ".env").read().replace("'C    2'", "'C'")
    assert "'C'" in text
    open(fname + ".env", "w").write(text)
    assert bh.Environment.from_file(fname + ".env")["dimension"] == "2.5D"
