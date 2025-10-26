
import os as _os
import subprocess as _proc
import shutil

from tempfile import mkstemp as _mkstemp
from typing import Any, Dict, List, Optional, Tuple

from .constants import Defaults, _Strings, _File_Ext
from .environment import Environment
from .readers import read_shd, read_arrivals, read_rays

class BellhopSimulator:
    """
    Interface to the Bellhop underwater acoustics ray tracing propagation model.

    Two public methods are defined: `supports()` and `run()`.
    Both take arguments of environment and task, and respectively
    report whether the executable can perform the task, and to do so.

    Parameters
    ----------
    name : str
        User-fancing name for the model
    exe : str
        Filename of Bellhop executable
    """

    def __init__(self, name: str = Defaults.model_name_2d,
                       exe: str = Defaults.model_exe_2d,
                       dim: int = Defaults.model_dim,
                ) -> None:
        self.name: str = name
        self.exe: str = exe
        self.dim: int = dim

    def supports(self, env: Optional[Environment] = None,
                       task: Optional[str] = None,
                       exe: Optional[str] = None,
                       dim: Optional[int] = None,
                ) -> bool:
        """Check whether the model supports the task.

           This function is supposed to diagnose whether this combination of environment
           and task is supported by the model."""

        if env is not None:
            dim = dim or env._dimension

        which_bool = shutil.which(exe or self.exe) is not None
        task_bool = (task is None) or (task in self.taskmap)
        dim_bool = (dim is None) or (dim == self.dim)

        return (which_bool and task_bool and dim_bool)

    def run(self, env: Environment,
                  task: str,
                  debug: bool = False,
                  fname_base: Optional[str] = None,
           ) -> Any:
        """
        High-level interface function which runs the model.

        The function definition performs setup and cleanup tasks
        and passes the execution off to an auxiliary function.

        Uses the `taskmap` data structure to relate input flags to
        processng stages, in particular how to select specific "tasks"
        to be executed.
        """

        task_flag, load_task_data, task_ext = self.taskmap[task]

        fd, fname_base = self._prepare_env_file(fname_base)
        with _os.fdopen(fd, "w") as fh:
            env.write(task_flag, fh, fname_base)

        self._run_exe(fname_base)
        results = load_task_data(fname_base + task_ext)

        if debug:
            print('[DEBUG] Bellhop working files NOT deleted: '+fname_base+'.*')
        else:
            self._rm_files(fname_base)

        return results

    @property
    def taskmap(self) -> Dict[Any, List[Any]]:
        """Dictionary which maps tasks to execution functions and their parameters"""
        return {
            _Strings.arrivals:     ['A', read_arrivals, _File_Ext.arr],
            _Strings.eigenrays:    ['E', read_rays,     _File_Ext.ray],
            _Strings.rays:         ['R', read_rays,     _File_Ext.ray],
            _Strings.coherent:     ['C', read_shd,      _File_Ext.shd],
            _Strings.incoherent:   ['I', read_shd,      _File_Ext.shd],
            _Strings.semicoherent: ['S', read_shd,      _File_Ext.shd],
        }

    def _prepare_env_file(self, fname_base: Optional[str]) -> Tuple[int, str]:
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
            fname = fname_base + _File_Ext.env
            fh = _os.open(_os.path.abspath(fname), _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC)
        else:
            fh, fname = _mkstemp(suffix = _File_Ext.env)
            fname_base = fname[:-len(_File_Ext.env)]
        self._rm_files(fname_base, not_env=True) # delete all other files
        return fh, fname_base

    def _rm_files(self, fname_base: str, not_env: bool = False) -> None:
        """Remove files that would be constructed as bellhop inputs or created as bellhop outputs."""
        all_ext = [v for k, v in vars(_File_Ext).items() if not k.startswith('_')]
        if not_env:
            all_ext.remove(_File_Ext.env)
        for ext in all_ext:
            self._unlink(fname_base + ext)

    def _run_exe(self, fname_base: str,
                       args: str = "",
                       debug: bool = False,
                       exe: Optional[str] = None,
                ) -> None:
        """Run the executable and raise exceptions if there are errors."""

        exe_path = shutil.which(exe or self.exe)
        if exe_path is None:
            raise FileNotFoundError(f"Executable ({exe_path}) not found in PATH.")

        runcmd = [exe_path, fname_base] + args.split()
        if debug:
            print("RUNNING:", " ".join(runcmd))
        result = _proc.run(runcmd, stderr=_proc.STDOUT, stdout=_proc.PIPE, text=True)

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


    def _check_error(self, fname_base: str) -> Optional[str]:
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
        return err if err != "" else None

    def _unlink(self, f: str) -> None:
        """Delete file only if it exists"""
        try:
            _os.unlink(f)
        except FileNotFoundError:
            pass

