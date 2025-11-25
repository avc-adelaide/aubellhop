import pytest
import aubellhop as bh
import os
import tempfile


def test_demo_function_exists():
    """Test that the demo function exists and is callable."""
    assert hasattr(bh, 'demo')
    assert callable(bh.demo)


def test_demo_runs():
    """Test that the demo function runs without errors and returns results."""
    import pandas as pd
    
    # Run in a temporary directory to avoid cluttering the test directory
    original_dir = os.getcwd()
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Run the demo
            results = bh.demo()
            
            # Check that results were returned
            assert results is not None
            assert isinstance(results, pd.DataFrame)
            
            # Check that arrivals were computed
            assert "time_of_arrival" in results.columns
            assert len(results["time_of_arrival"]) > 0
            
            # Check that demo file was created
            assert os.path.exists("bellhop_demo.py")
            
            # Verify the demo file is not empty
            with open("bellhop_demo.py", 'r') as f:
                content = f.read()
                assert len(content) > 0
                assert "import aubellhop" in content
                assert "compute_arrivals" in content
                
    finally:
        os.chdir(original_dir)


def test_demo_file_is_runnable():
    """Test that the generated demo file can be executed."""
    import subprocess
    
    original_dir = os.getcwd()
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Generate the demo file
            bh.demo()
            
            # Try to run it (just check syntax)
            result = subprocess.run(
                ["python3", "-m", "py_compile", "bellhop_demo.py"],
                capture_output=True,
                text=True
            )
            
            # Should compile without errors
            assert result.returncode == 0, f"Demo file has syntax errors: {result.stderr}"
            
    finally:
        os.chdir(original_dir)
