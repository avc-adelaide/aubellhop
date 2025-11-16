#!/usr/bin/env python3
"""Simple script to test bellhop wheel installation and functionality.

This script can be used to validate wheels built by cibuildwheel.
"""

import sys
import os
from pathlib import Path


def test_import():
    """Test that bellhop can be imported."""
    try:
        import bellhop
        print("✓ bellhop imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import bellhop: {e}")
        return False


def test_executables():
    """Test that executables can be found."""
    try:
        from bellhop.bellhop import _find_executable
        
        bellhop_exe = _find_executable('bellhop.exe')
        bellhop3d_exe = _find_executable('bellhop3d.exe')
        
        if bellhop_exe is None:
            print("✗ bellhop.exe not found")
            return False
        if bellhop3d_exe is None:
            print("✗ bellhop3d.exe not found")
            return False
        
        print(f"✓ Found bellhop.exe at: {bellhop_exe}")
        print(f"✓ Found bellhop3d.exe at: {bellhop3d_exe}")
        
        # Check they're executable
        if not os.access(bellhop_exe, os.X_OK):
            print(f"✗ bellhop.exe is not executable")
            return False
        if not os.access(bellhop3d_exe, os.X_OK):
            print(f"✗ bellhop3d.exe is not executable")
            return False
        
        print("✓ Executables have correct permissions")
        return True
        
    except Exception as e:
        print(f"✗ Failed to check executables: {e}")
        return False


def test_models():
    """Test that models can be loaded."""
    try:
        from bellhop.models import Models
        
        model = Models.get('bellhop')
        if not model.supports():
            print("✗ Model does not support execution")
            return False
        
        print("✓ Model loaded and supports execution")
        return True
        
    except Exception as e:
        print(f"✗ Failed to load models: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing bellhop wheel installation...")
    print()
    
    tests = [
        ("Import", test_import),
        ("Executables", test_executables),
        ("Models", test_models),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"Testing {name}...")
        result = test_func()
        results.append(result)
        print()
    
    if all(results):
        print("All tests passed! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
