import pytest
import bellhop as bh

def test_grain_read_data():
    """Test using a Bellhop example that ENV file parameters are being picked up properly.
    """

    env = bh.Environment.from_file("tests/halfspace/lower_halfB_grain.env")

    assert env['bottom_boundary_condition'] == 'grain'
    assert env['_bottom_depth'] == 5000.0
    assert env['bottom_grain_size'] == 1.5
