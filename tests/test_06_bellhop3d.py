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
