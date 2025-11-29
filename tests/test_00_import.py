import pytest
from aubellhop.constants import ModelDefaults

def test_import_arlpy():
    try:
        import aubellhop as bh
    except ImportError as e:
        pytest.exit(f"❌ Cannot import aubellhop: {e}", returncode=1)

    # sanity check: make sure bellhop is registered
    if ModelDefaults.name_2d not in bh.Models.supported():
        pytest.exit("❌ default 'Bellhop' model not available. This probably means that bellhop.exe is not available on the current $PATH.", returncode=1)

    # If everything is fine, the test passes
    assert True
