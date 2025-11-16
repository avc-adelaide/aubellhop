from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

import tempfile
from typing import Any, Dict, Tuple

from .constants import ModelDefaults, BHStrings, _File_Ext
from .environment import Environment
from .readers import read_shd, read_arrivals, read_rays

"""Provides BellhopSimulator class for interacting with bellhop models.

This class is instantiated within `models.py` and supports the standard 
`bellhop.exe` and `bellhop3d.exe` Fortran interfaces.

New classes could be written to replicate the interfaces if
further models wished to be tested with different internals.

Instances of BellhopSimulator are used as follows in `compute.py`:

    >>> model_fn = Models.select(this_env, this_task, this_model, debug)
    >>> fname_base = model_fn.write_env(this_env, this_task, fname_base)
    >>> model_fn.run(this_task, fname_base, debug=debug),

In the code above `model_fn` is the instance. `Models` is a utility
cass which contains a global registry of BellhopSimulator instances.
Internally `Models.select` uses `model_fn.supports()` to
identify the BellhopSimulator model (instance) to use.

Writing the environment file appears circuitous:

    ~~bellhop.py~~         ~~environment.py~~   ~~writers.py~~
    model_fn.write_env() → env.to_file()      → EnvironmentWriter().write()

These indirections are partially for modularity and partly for
encapsulation. 
"""


def _find_executable(exe_name: str) -> str | None:
    """Find the bellhop executable.
    
    First checks the package's bin directory (for installed wheels),
    then falls back to searching PATH.
    
    Parameters
    ----------
    exe_name : str
        Name of the executable (e.g., 'bellhop.exe')
    
    Returns
    -------
    str | None
        Path to the executable, or None if not found
    """
    # Try package bin directory first (for installed wheels)
    try:
        package_dir = Path(__file__).parent
        package_bin = package_dir / "bin" / exe_name
        if package_bin.exists() and os.access(package_bin, os.X_OK):
            return str(package_bin)
    except Exception:
        pass
    
    # Fall back to PATH
    return shutil.which(exe_name)


class BellhopSimulator:
    """
    Interface to the Bellhop underwater acoustics ray tracing propagation model.

    The following methods are defined:

    * `supports()`
    * `write_env()`
    * `run()`

    Parameters
    ----------
    name : str
        User-fancing name for the model
    exe : str
        Filename of Bellhop executable
    dim : int
        Number of dimensions in the model (`2` or `3`)
    """

    def __init__(self, name: str = ModelDefaults.name_2d,
                       exe:  str = ModelDefaults.exe_2d,
                       dim:  int = ModelDefaults.dim_2d,
                ) -> None:
        self.name: str = name
        self.exe: str = exe
        self.dim: int = dim

    def supports(self, env: Environment | None = None,
                       task: str | None = None,
                       exe: str | None = None,
                       dim: int | None = None,
                ) -> bool:
        """Check whether the model supports the task.

           This function is supposed to diagnose whether this combination of environment
           and task is supported by the model."""
        if env is not None:
            dim = dim or env._dimension
        which_bool = _find_executable(exe or self.exe) is not None
        task_bool = (task is None) or (task in self.taskmap)
        dim_bool = (dim is None) or (dim == self.dim)
        return (which_bool and task_bool and dim_bool)

    def write_env(self, env: Environment,
                        task: str,
                        fname_base: str | None = None,
                        debug: bool = False,
                 ) -> str:
        """
        Writes the environment to .env file prior to running the model.

        Uses the `taskmap` data structure to relate input flags to
        processng stages, in particular how to select specific "tasks"
        to be executed.
        """
        task_flag, load_task_data, task_ext = self.taskmap[task]
        fname_base, fname = self._prepare_env_file(fname_base)
        with open(fname, "w") as fh:
            env.to_file(fh, fname_base, task_flag)

        return fname_base

    def run(self, task: str,
                  fname_base: str,
                  rm_files: bool = True,
                  debug: bool = False,
           ) -> Any:
        """
        High-level interface function which runs the model.
        """
        task_flag, load_task_data, task_ext = self.taskmap[task]
        self._run_exe(fname_base)
        results = load_task_data(fname_base + task_ext)
        if rm_files:
            if debug:
                print('[DEBUG] Bellhop working files NOT deleted: '+fname_base+'.*')
            else:
                self._rm_files(fname_base)
        return results

    @property
    def taskmap(self) -> Dict[Any, list[Any]]:
        """Dictionary which maps tasks to execution functions and their parameters"""
        return {
            BHStrings.arrivals:     ['A', read_arrivals, _File_Ext.arr],
            BHStrings.eigenrays:    ['E', read_rays,     _File_Ext.ray],
            BHStrings.rays:         ['R', read_rays,     _File_Ext.ray],
            BHStrings.coherent:     ['C', read_shd,      _File_Ext.shd],
            BHStrings.incoherent:   ['I', read_shd,      _File_Ext.shd],
            BHStrings.semicoherent: ['S', read_shd,      _File_Ext.shd],
        }

    def _prepare_env_file(self, 
                                fname_base: str | None,
                         ) -> Tuple[str, str]:
        """Opens a file for writing the .env file, in a temp location if necessary, and delete other files with same basename.

        Parameters
        ----------
        fname_base : str, optional
            Filename base (no extension) for writing -- if not specified a temporary file (and location) will be used instead

        Returns
        -------
        fh : int
            File descriptor
    fname_base : str
            Filename base
        """
        if fname_base is not None:
            fname = os.path.abspath(fname_base + _File_Ext.env)
            os.makedirs(os.path.dirname(fname), exist_ok=True)
            open(fname, "w").close()
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=_File_Ext.env, delete=False, mode="w")
            fname = tmp.name
            fname_base = fname[: -len(_File_Ext.env)]
            tmp.close()

        self._rm_files(fname_base, not_env=True)
        return fname_base, fname

    def _rm_files(self, fname_base: str,
                        not_env: bool = False,
                 ) -> None:
        """Remove files that would be constructed as bellhop inputs or created as bellhop outputs."""
        all_ext = [v for k, v in vars(_File_Ext).items() if not k.startswith('_')]
        if not_env:
            all_ext.remove(_File_Ext.env)
        for ext in all_ext:
            self._unlink(fname_base + ext)

    def _run_exe(self, fname_base: str,
                       args: str = "",
                       debug: bool = False,
                       exe: str | None = None,
                ) -> None:
        """Run the executable and raise exceptions if there are errors."""

        exe_path = _find_executable(exe or self.exe)
        if exe_path is None:
            raise FileNotFoundError(
                f"Executable '{exe or self.exe}' not found in package bin directory or PATH.\n"
                f"Please ensure the package is installed correctly or bellhop executables are in your PATH."
            )

        runcmd = [exe_path, fname_base] + args.split()
        if debug:
            print("RUNNING:", " ".join(runcmd))
        result = subprocess.run(runcmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)

        if debug and result.stdout:
            print(result.stdout.strip())

        if result.returncode != 0:
            err = self._check_error(fname_base)
            raise RuntimeError(
                f"Execution of '{exe_path}' failed with return code {result.returncode}.\n"
                f"\nCommand: {' '.join(runcmd)}\n"
                f"\nOutput:\n{result.stdout.strip()}\n"
                f"\nExtract from PRT file:\n{err}"
            )

    def _check_error(self,
                           fname_base: str,
                    ) -> str:
        """Extracts Bellhop error text from the .prt file"""
        try:
            err = ""
            fatal = False
            with open(fname_base + _File_Ext.prt, 'rt') as f:
                for s in f:
                    if fatal and len(s.strip()) > 0:
                        err += '[FATAL] ' + s.strip() + '\n'
                    if '*** FATAL ERROR ***' in s:
                        fatal = True
        except FileNotFoundError:
            pass
        return err

    def _unlink(self, f: str) -> None:
        """Delete file only if it exists"""
        try:
            os.unlink(f)
        except FileNotFoundError:
            pass

