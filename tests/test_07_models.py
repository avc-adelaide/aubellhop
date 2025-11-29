import pytest
import aubellhop as bh
import numpy as np

def test_models():

    env = bh.Environment()
    models = bh.Models.supported()
    print(models)
    assert models is not None


def test_models_task():

    env = bh.Environment()
    models = bh.Models.supported(env,"coherent")
    print(models)
    assert models is not None


def test_models_task():
    """I would expect this to error but it doesn't :)"""
    env = bh.Environment()
    models = bh.Models.supported(env,"foobar")
    print("foobar model?")
    print(models)
    assert models is not None
