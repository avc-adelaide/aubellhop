import pytest
import bellhop as bh
import numpy as np

def test_models():

    env = bh.Environment()
    models = bh.Models.list()
    print(models)
    assert models is not None


def test_models_task():

    env = bh.Environment()
    models = bh.Models.list(env,"coherent")
    print(models)
    assert models is not None


def test_models_task():
    """I would expect this to error but it doesn't :)"""
    env = bh.Environment()
    models = bh.Models.list(env,"foobar")
    print("foobar model?")
    print(models)
    assert models is not None
