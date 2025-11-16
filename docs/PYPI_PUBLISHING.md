# Building and Publishing Wheels to PyPI

This document describes how to build and publish bellhop wheels with pre-compiled Fortran binaries to PyPI.

## Overview

The bellhop package includes pre-compiled Fortran executables (`bellhop.exe` and `bellhop3d.exe`) in the Python wheels for easy installation. The build process compiles these executables during wheel building for each target platform.

## Building Wheels Locally

### Prerequisites

- Python 3.12+
- gfortran compiler
- build and wheel packages

### Building

1. Install build dependencies:
   ```bash
   pip install build wheel
   ```

2. Build the wheel:
   ```bash
   python -m build --wheel
   ```

   The wheel will be created in the `dist/` directory.

3. Test the wheel:
   ```bash
   pip install dist/bellhop-*.whl
   python -c "import bellhop; print('Success!')"
   ```

## Building Wheels for Multiple Platforms

The repository includes a GitHub Actions workflow (`.github/workflows/build-wheels.yml`) that automatically builds wheels for:

- Linux (x86_64)
- macOS (x86_64 and arm64)
- Windows (x86_64)

### Triggering the Workflow

The workflow runs automatically on:
- Pushes to main/master branch
- Pull requests
- Tag pushes (for releases)
- Manual workflow dispatch

### Manual Trigger

To manually trigger the workflow:
1. Go to the Actions tab in GitHub
2. Select "Build Wheels" workflow
3. Click "Run workflow"

## Publishing to PyPI

### Prerequisites

1. Create a PyPI account at https://pypi.org
2. Generate an API token:
   - Go to Account Settings → API tokens
   - Create a new token with appropriate scope
3. Add the token as a GitHub secret:
   - Repository Settings → Secrets → Actions
   - Add secret named `PYPI_API_TOKEN`

### Publishing Process

#### Automatic Publishing (Recommended)

The workflow automatically publishes to PyPI when you push a version tag:

1. Update version in `pyproject.toml`:
   ```toml
   [project]
   version = "0.2.0"
   ```

2. Commit and push:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git push
   ```

3. Create and push a tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

The workflow will automatically build wheels for all platforms and publish them to PyPI.

#### Manual Publishing

If you need to publish manually:

1. Download wheel artifacts from the GitHub Actions workflow run

2. Install twine:
   ```bash
   pip install twine
   ```

3. Upload to PyPI:
   ```bash
   twine upload dist/*
   ```

   Or to TestPyPI first (recommended):
   ```bash
   twine upload --repository testpypi dist/*
   ```

## Platform-Specific Notes

### Linux

- Wheels are built using manylinux containers
- gfortran is installed via yum/apt during build

### macOS

- Separate wheels for Intel (x86_64) and Apple Silicon (arm64)
- gfortran installed via Homebrew during build

### Windows

- Uses MSYS2 with MinGW-w64 for gfortran
- Executables include necessary runtime libraries

## Troubleshooting

### Build Failures

If wheel building fails:

1. Check that gfortran is available in the build environment
2. Verify Makefile and setup.py are correct
3. Check build logs in GitHub Actions for specific errors

### Import Errors

If the installed package can't find executables:

1. Verify executables are in the wheel:
   ```bash
   unzip -l dist/bellhop-*.whl | grep bin/
   ```

2. Check executable permissions are correct (should be 0755)

3. Test the `_find_executable` function:
   ```python
   from bellhop.bellhop import _find_executable
   print(_find_executable('bellhop.exe'))
   ```

### Runtime Errors

If executables fail to run:

1. Check they're executable: `ls -la <path>/bin/`
2. Test running directly: `<path>/bin/bellhop.exe`
3. Check for missing dynamic libraries: `ldd <path>/bin/bellhop.exe` (Linux)

## CI/CD Integration

The build-wheels workflow integrates with the existing CI:

- Runs on all PRs to validate wheel building
- Publishes only on tagged releases
- Includes basic import tests for each platform
- Uploads wheel artifacts for review

## Testing Wheels

Before publishing:

1. Download wheel artifacts from Actions
2. Install in a clean virtual environment
3. Run test suite:
   ```bash
   pip install bellhop-*.whl
   pip install pytest
   pytest tests/
   ```

## Version Management

The package version is specified in `pyproject.toml`:

```toml
[project]
version = "0.1"
```

Update this before creating a release tag.

## Further Information

- [Python Packaging User Guide](https://packaging.python.org/)
- [cibuildwheel documentation](https://cibuildwheel.readthedocs.io/)
- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
