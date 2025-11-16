"""Setup script for bellhop package with Fortran binary compilation.

This setup.py is used to build wheels with pre-compiled Fortran binaries
for distribution on PyPI. The binaries are compiled during wheel building
and included in the package.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class FortranBuildExt(build_ext):
    """Custom build extension to compile Fortran binaries."""

    def run(self):
        """Build the Fortran executables."""
        # Get the root directory
        root_dir = Path(__file__).parent.absolute()
        fortran_dir = root_dir / "fortran"
        
        # Check for gfortran (including versioned variants on macOS)
        gfortran_path = shutil.which("gfortran")
        if gfortran_path is None:
            # Try to find versioned gfortran (gfortran-15, gfortran-14, etc.)
            for version in range(20, 10, -1):  # Check versions 20 down to 11
                versioned_gfortran = f"gfortran-{version}"
                gfortran_path = shutil.which(versioned_gfortran)
                if gfortran_path is not None:
                    break
        
        if gfortran_path is None:
            raise RuntimeError(
                "gfortran compiler not found. Please install gfortran to build this package.\n"
                "On Ubuntu/Debian: sudo apt-get install gfortran\n"
                "On macOS with Homebrew: brew install gcc\n"
                "On Windows with MSYS2: pacman -S mingw-w64-x86_64-gcc-fortran"
            )
        
        # Set FC environment variable for make
        build_env = os.environ.copy()
        build_env['FC'] = os.path.basename(gfortran_path)
        
        # Build using the Makefile
        print("Building Fortran executables...")
        print(f"Using Fortran compiler: {gfortran_path}")
        try:
            subprocess.check_call(["make", "clean"], cwd=root_dir, env=build_env)
            subprocess.check_call(["make"], cwd=root_dir, env=build_env)
            subprocess.check_call(["make", "install"], cwd=root_dir, env=build_env)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build Fortran executables: {e}")
        
        # Verify binaries were created
        bin_dir = root_dir / "bin"
        bellhop_exe = bin_dir / "bellhop.exe"
        bellhop3d_exe = bin_dir / "bellhop3d.exe"
        
        if not bellhop_exe.exists() or not bellhop3d_exe.exists():
            raise RuntimeError(
                f"Failed to create executables. Expected files:\n"
                f"  {bellhop_exe}\n"
                f"  {bellhop3d_exe}"
            )
        
        # Copy binaries to the package directory
        package_dir = Path(self.build_lib) / "bellhop" / "bin"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Copying executables to {package_dir}...")
        shutil.copy2(bellhop_exe, package_dir / "bellhop.exe")
        shutil.copy2(bellhop3d_exe, package_dir / "bellhop3d.exe")
        
        # Make them executable
        (package_dir / "bellhop.exe").chmod(0o755)
        (package_dir / "bellhop3d.exe").chmod(0o755)
        
        print("Fortran executables built and copied successfully.")


# Dummy extension to trigger build_ext
ext_modules = [
    Extension("bellhop._fortran", sources=[]),
]


if __name__ == "__main__":
    setup(
        ext_modules=ext_modules,
        cmdclass={
            "build_ext": FortranBuildExt,
        },
    )
