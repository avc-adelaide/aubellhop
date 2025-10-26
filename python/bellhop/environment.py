
"""
Environment configuration for BELLHOP.

This module provides dataclass-based environment configuration with automatic validation,
replacing manual option checking with field validators.
"""

from collections.abc import MutableMapping
from dataclasses import dataclass, asdict, fields
from typing import Optional, Union, Any, Dict, Iterator, List, TextIO

from pprint import pformat
import warnings
from itertools import product

import numpy as _np
import pandas as _pd

from .constants import _Strings, _Maps, Defaults

@dataclass
class Environment(MutableMapping[str, Any]):
    """Dataclass for underwater acoustic environment configuration.

    This class provides automatic validation of environment parameters,
    eliminating the need for manual checking of option validity.

    These entries are either intended to be set or edited by the user, or with `_` prefix are
    internal state read from a .env file or inferred by other data. Some others are ignored."""

    # Basic environment properties
    name: str = 'bellhop/python default'
    dimension: str = _Strings.two_d
    _dimension: int = 2
    frequency: float = 25000.0  # Hz
    _num_media: int = 1 # must always = 1 in bellhop

    # Sound speed parameters
    soundspeed: Union[float, Any] = Defaults.sound_speed  # m/s
    soundspeed_interp: str = _Strings.linear

    # Depth parameters
    depth: Union[float, Any] = 25.0  # m
    depth_interp: str = _Strings.linear
    _mesh_npts: int = 0 # ignored by bellhop
    _depth_sigma: float = 0.0 # ignored by bellhop
    depth_max: Optional[float] = None  # m
    range_max: Optional[float] = None  # m -- not used in the environment file

    # Flags to read/write from separate files
    _bathymetry: str = _Strings.flat  # set to "from-file" if multiple bottom depths
    _altimetry: str = _Strings.flat  # set to "from-file" if multiple surface heights
    _sbp_file: str = _Strings.default # set to "from-file" if source_directionality defined

    # Bottom parameters
    bottom_interp: Optional[str] = None
    bottom_soundspeed: float = Defaults.sound_speed # m/s
    _bottom_soundspeed_shear: float = 0.0  # m/s (ignored)
    bottom_density: float = Defaults.density  # kg/m^3
    bottom_attenuation: Optional[float] = None  # dB/wavelength
    _bottom_attenuation_shear: Optional[float] = None  # dB/wavelength (ignored)
    bottom_roughness: float = 0.0  # m (rms)
    bottom_beta: Optional[float] = None
    bottom_transition_freq: Optional[float] = None  # Hz
    bottom_boundary_condition: str = _Strings.acousto_elastic
    bottom_reflection_coefficient: Optional[Any] = None

    # Surface parameters
    surface: Optional[Any] = None  # surface profile
    surface_interp: str = _Strings.linear  # curvilinear/linear
    surface_boundary_condition: str = _Strings.vacuum
    surface_reflection_coefficient: Optional[Any] = None
    surface_depth: float = 0.0  # m
    surface_soundspeed: float = Defaults.sound_speed # m/s
    _surface_soundspeed_shear: float = 0.0  # m/s (ignored)
    surface_density: float = Defaults.density  # kg/m^3
    surface_attenuation: Optional[float] = None  # dB/wavelength
    _surface_attenuation_shear: Optional[float] = None  # dB/wavelength (ignored)

    # Source parameters
    source_type: str = 'default'
    source_range: Union[float, Any] = 0.0
    source_cross_range: Union[float, Any] = 0.0
    source_depth: Union[float, Any] = 5.0  # m - Any allows for np.ndarray
    source_ndepth: Optional[int] = None
    source_nrange: Optional[int] = None
    source_ncrossrange: Optional[int] = None
    source_directionality: Optional[Any] = None  # [(deg, dB)...]

    # Receiver parameters
    receiver_depth: Union[float, Any] = 10.0  # m - Any allows for np.ndarray
    receiver_range: Union[float, Any] = 1000.0  # m - Any allows for np.ndarray
    receiver_bearing: Union[float, Any] = 0.0  # deg - Any allows for np.ndarray
    receiver_ndepth: Optional[int] = None
    receiver_nrange: Optional[int] = None
    receiver_nbearing: Optional[int] = None

    # Beam settings
    beam_type: str = _Strings.default
    beam_angle_min: Optional[float] = None  # deg
    beam_angle_max: Optional[float] = None  # deg
    beam_bearing_min: Optional[float] = None  # deg
    beam_bearing_max: Optional[float] = None  # deg
    beam_num: int = 0  # (0 = auto)
    beam_bearing_num: int = 0
    single_beam_index: Optional[int] = None
    _single_beam: str = _Strings.default # value inferred from `single_beam_index`

    # Solution parameters
    step_size: Optional[float] = 0.0 # (0 = auto)
    box_depth: Optional[float] = None
    box_range: Optional[float] = None
    box_cross_range: Optional[float] = None
    grid_type: str = 'default'
    task: Optional[str] = None
    interference_mode: Optional[str] = None # subset of `task` for providing TL interface

    # Attenuation parameters
    volume_attenuation: str = 'none'
    attenuation_units: str = Defaults.attenuation_units
    biological_layer_parameters: Optional[Any] = None

    # Francois-Garrison volume attenuation parameters
    fg_salinity: Optional[float] = None
    fg_temperature: Optional[float] = None
    fg_pH: Optional[float] = None
    fg_depth: Optional[float] = None

    comment_pad: int = Defaults.env_comment_pad

    def reset(self) -> "Environment":
        """Delete values for all user-facing parameters."""
        for k in self.keys():
            if not k.startswith("_"):
                self[k] = None
        return self

    def check(self) -> "Environment":
        """Finalise environment parameters and perform assertion checks."""
        self._finalise()
        try:
            self._check_env_header()
            self._check_env_surface()
            self._check_env_depth()
            self._check_env_ssp()
            self._check_env_sbp()
            self._check_env_beam()
            return self
        except AssertionError as e:
            raise ValueError(f"Env check error: {str(e)}") from None

    def _finalise(self) -> "Environment":
        """Reviews the data within an environment and updates settings for consistency.

        This function is run as the first step of `.check()`.
        """

        if self.dimension == _Strings.two_d:
            self._dimension = 2
        elif self.dimension == _Strings.two_half_d or self.dimension == _Strings.three_d:
            self._dimension = 3

        if _np.size(self['depth']) > 1:
            self["_bathymetry"] = _Strings.from_file
        if self["surface"] is not None:
            self["_altimetry"] = _Strings.from_file
        if self["bottom_reflection_coefficient"] is not None:
            self["bottom_boundary_condition"] = _Strings.from_file
        if self["surface_reflection_coefficient"] is not None:
            self["surface_boundary_condition"] = _Strings.from_file

        if self['depth_max'] is None:
            if _np.size(self['depth']) == 1:
                self['depth_max'] = self['depth']
            else:
                # depth : Nx2 array = [ranges,depths]
                self['depth_max'] = _np.max(self['depth'][:,1])

        if not isinstance(self['soundspeed'], _pd.DataFrame):
            if _np.size(self['soundspeed']) == 1:
                speed = [float(self["soundspeed"]), float(self["soundspeed"])]
                depth = [0, float(self['depth_max'])]
                self["soundspeed"] = _pd.DataFrame(speed, columns=["speed"], index=depth)
                self["soundspeed"].index.name = "depth"
            elif self['soundspeed'].shape[0] == 1 and self['soundspeed'].shape[1] == 2:
                speed = [float(self["soundspeed"][0,1]), float(self["soundspeed"][0,1])]
                d1 = float(min([0.0, self["soundspeed"][0,0]]))
                d2 = float(max([self["soundspeed"][0,0], self['depth_max']]))
                self["soundspeed"] = _pd.DataFrame(speed, columns=["speed"], index=[d1, d2])
                self["soundspeed"].index.name = "depth"
            elif self['soundspeed'].ndim == 2 and self['soundspeed'].shape[1] == 2:
                depth = self['soundspeed'][:,0]
                speed = self['soundspeed'][:,1]
                self["soundspeed"] = _pd.DataFrame(speed, columns=["speed"], index=depth)
                self["soundspeed"].index.name = "depth"
            else:
                raise ValueError("Soundspeed array must be a 2xN array (better to use a DataFrame)")

        if "depth" in self["soundspeed"].columns:
            self["soundspeed"] = self["soundspeed"].set_index("depth")

        if len(self['soundspeed'].columns) > 1:
            self['soundspeed_interp'] == _Strings.quadrilateral

        # Beam angle ranges default to half-space if source is left-most, otherwise full-space:
        if self['beam_angle_min'] is None:
            if _np.min(self['receiver_range']) < 0:
                self['beam_angle_min'] = - Defaults.beam_angle_fullspace
            else:
                self['beam_angle_min'] = - Defaults.beam_angle_halfspace
        if self['beam_angle_max'] is None:
            if _np.min(self['receiver_range']) < 0:
                self['beam_angle_max'] =  Defaults.beam_angle_fullspace
            else:
                self['beam_angle_max'] = Defaults.beam_angle_halfspace

        # Identical logic for bearing angles
        if _np.min(self['receiver_range']) < 0:
            angle_min = -Defaults.beam_bearing_fullspace
            angle_max = +Defaults.beam_bearing_fullspace
        else:
            angle_min = -Defaults.beam_bearing_halfspace
            angle_max = +Defaults.beam_bearing_halfspace

        self._or_default('beam_bearing_min', angle_min)
        self._or_default('beam_bearing_max', angle_max)

        bearing_max = _np.max([
            abs(self['beam_bearing_max']),
            abs(self['beam_bearing_min'])
        ])

        self._or_default('box_depth', 1.01 * self['depth_max'])
        self._or_default('box_range',
            1.01 * (_np.max(self['receiver_range']) - min(0, _np.min(self['receiver_range'])))
        )
        self._or_default('box_cross_range',
            1.01 * _np.max(self['receiver_range']) * _np.sin(_np.deg2rad(bearing_max))
        )
        return self


    def _check_env_header(self) -> None:
        assert self["_num_media"] == 1, f"BELLHOP only supports 1 medium, found {self['_num_media']}"

    def _check_env_surface(self) -> None:
        max_range = _np.max(self['receiver_range'])
        if self['surface'] is not None:
            assert _np.size(self['surface']) > 1, 'surface must be an Nx2 array'
            assert self['surface'].ndim == 2, 'surface must be a scalar or an Nx2 array'
            assert self['surface'].shape[1] == 2, 'surface must be a scalar or an Nx2 array'
            assert self['surface'][0,0] <= 0, 'First range in surface array must be 0 m'
            assert self['surface'][-1,0] >= max_range, 'Last range in surface array must be beyond maximum range: '+str(max_range)+' m'
            assert _np.all(_np.diff(self['surface'][:,0]) > 0), 'surface array must be strictly monotonic in range'
        if self["surface_reflection_coefficient"] is not None:
            assert self["surface_boundary_condition"] == _Strings.from_file, "TRC values need to be read from file"

    def _check_env_depth(self) -> None:
        max_range = _np.max(self['receiver_range'])
        if _np.size(self['depth']) > 1:
            assert self['depth'].ndim == 2, 'depth must be a scalar or an Nx2 array [ranges, depths]'
            assert self['depth'].shape[1] == 2, 'depth must be a scalar or an Nx2 array [ranges, depths]'
            assert self['depth'][-1,0] >= max_range, 'Last range in depth array must be beyond maximum range: '+str(max_range)+' m'
            assert _np.all(_np.diff(self['depth'][:,0]) > 0), 'Depth array must be strictly monotonic in range'
            assert self["_bathymetry"] == _Strings.from_file, 'len(depth)>1 requires BTY file'
        if self["bottom_reflection_coefficient"] is not None:
            assert self["bottom_boundary_condition"] == _Strings.from_file, "BRC values need to be read from file"
        assert _np.max(self['source_depth']) <= self['depth_max'], 'source_depth cannot exceed water depth: '+str(self['depth_max'])+' m'
        assert _np.max(self['receiver_depth']) <= self['depth_max'], 'receiver_depth cannot exceed water depth: '+str(self['depth_max'])+' m'

    def _check_env_ssp(self) -> None:
        assert isinstance(self['soundspeed'], _pd.DataFrame), 'Soundspeed should always be a DataFrame by this point'
        assert self['soundspeed'].size > 1, "Soundspeed DataFrame should have been constructed internally to be two elements"
        if self['soundspeed'].size > 1:
            if len(self['soundspeed'].columns) > 1:
                assert self['soundspeed_interp'] == _Strings.quadrilateral, "SVP DataFrame with multiple columns implies quadrilateral interpolation."
            if self['soundspeed_interp'] == _Strings.spline:
                assert self['soundspeed'].shape[0] > 3, 'soundspeed profile must have at least 4 points for spline interpolation'
            else:
                assert self['soundspeed'].shape[0] > 1, 'soundspeed profile must have at least 2 points'
            assert self['soundspeed'].index[0] <= 0.0, 'First depth in soundspeed array must be 0 m'
            assert _np.all(_np.diff(self['soundspeed'].index) > 0), 'Soundspeed array must be strictly monotonic in depth'
            if self['depth_max'] != self['soundspeed'].index[-1]:
                if self['soundspeed'].shape[1] > 1:
                    # TODO: generalise interpolation trimming from np approach below
                    assert self['soundspeed'].index[-1] == self['depth_max'], '2D SSP: Final entry in soundspeed array must be at the maximum water depth: '+str(self['depth_max'])+' m'
                else:
                    indlarger = _np.argwhere(self['soundspeed'].index > self['depth_max'])[0][0]
                    prev_ind = self['soundspeed'].index[:indlarger].tolist()
                    insert_ss_val = _np.interp(self['depth_max'], self['soundspeed'].index, self['soundspeed'].iloc[:,0])
                    new_row = _pd.DataFrame([self['depth_max'], insert_ss_val], columns=self['soundspeed'].columns)
                    self['soundspeed'] = _pd.concat([
                            self['soundspeed'].iloc[:(indlarger-1)],  # rows before insertion
                            new_row,                             # new row
                        ], ignore_index=True)
                    self['soundspeed'].index = prev_ind + [self['depth_max']]
                    warnings.warn("Bellhop.py has used linear interpolation to ensure the sound speed profile ends at the max depth. Ensure this is what you want.", UserWarning)
                    print("ATTEMPTING TO FIX")
            # TODO: check soundspeed range limits

    def _check_env_sbp(self) -> None:
        if self['source_directionality'] is not None:
            assert _np.size(self['source_directionality']) > 1, 'source_directionality must be an Nx2 array'
            assert self['source_directionality'].ndim == 2, 'source_directionality must be an Nx2 array'
            assert self['source_directionality'].shape[1] == 2, 'source_directionality must be an Nx2 array'
            assert _np.all(self['source_directionality'][:,0] >= -180) and _np.all(self['source_directionality'][:,0] <= 180), 'source_directionality angles must be in (-180, 180]'

    def _check_env_beam(self) -> None:
        assert self['beam_angle_min'] >= -180 and self['beam_angle_min'] <= 180, 'beam_angle_min must be in range (-180, 180]'
        assert self['beam_angle_max'] >= -180 and self['beam_angle_max'] <= 180, 'beam_angle_max must be in range (-180, 180]'
        if self['_single_beam'] == _Strings.single_beam:
            assert self['single_beam_index'] is not None, 'Single beam was requested with option I but no index was provided in NBeam line'


    def unwrap(self, *keys: str) -> list["Environment"]:
        """Return a list of Environment copies expanded over the given keys.

        If multiple keys are provided, all combinations are produced.
        Each unwrapped Environment gets a unique `.name` derived from the
        parent name and the expanded field values.
        """

        # Ensure keys are valid
        for k in keys:
            if k not in self:
                raise KeyError(f"Environment has no field '{k}'")

        # Prepare value lists (convert scalars → singletons)
        values: list[Any] = []
        for k in keys:
            v = self[k]
            if isinstance(v, (list, tuple, _np.ndarray)):
                values.append(v)
            else:
                values.append([v])

        combos = product(*values)
        envs = []

        base_name = str(self.get("name", "env"))

        for combo in combos:
            env_i = self.copy()
            name_parts = [base_name]
            for k, v in zip(keys, combo):
                env_i[k] = v
                # Replace disallowed chars and truncate floats nicely
                if isinstance(v, float):
                    v_str = f"{v:g}"
                else:
                    v_str = str(v)
                name_parts.append(f"{k}{v_str}")
            env_i["name"] = "-".join(name_parts)
            envs.append(env_i)

        return envs

    def write(self, taskcode: str, fh: TextIO, fname_base: str) -> None:
        """Writes a complete .env file for specifying a Bellhop simulation

        Parameters
        ----------
        env : dict
            Environment dict
        taskcode : str
            Task string which defines the computation to run
        fh : file object
            File reference (already opened)
        fname_base : str
            Filename base (without extension)
        :returns fname_base: filename base (no extension) of written file

        We liberally insert comments and empty lines for readability and take care to
        ensure that comments are consistently aligned.
        This doesn't make a difference to bellhop.exe, it just makes debugging far easier.
        """

        self._print_env_line(fh,"")
        self._write_env_header(fh)
        self._print_env_line(fh,"")
        self._write_env_surface_depth(fh)
        self._write_env_sound_speed(fh)
        self._print_env_line(fh,"")
        self._write_env_bottom(fh)
        self._print_env_line(fh,"")
        self._write_env_source_receiver(fh)
        self._print_env_line(fh,"")
        self._write_env_task(fh, taskcode)
        self._write_env_beam_footer(fh)
        self._print_env_line(fh,"","End of Bellhop environment file")

        if self['surface_boundary_condition'] == _Strings.from_file:
            self._create_refl_coeff_file(fname_base+".trc", self['surface_reflection_coefficient'])
        if self['surface'] is not None:
            self._create_bty_ati_file(fname_base+'.ati', self['surface'], self['surface_interp'])
        if self['soundspeed_interp'] == _Strings.quadrilateral:
            self._create_ssp_quad_file(fname_base+'.ssp', self['soundspeed'])
        if _np.size(self['depth']) > 1:
            self._create_bty_ati_file(fname_base+'.bty', self['depth'], self['depth_interp'])
        if self['bottom_boundary_condition'] == _Strings.from_file:
            self._create_refl_coeff_file(fname_base+".brc", self['bottom_reflection_coefficient'])
        if self['source_directionality'] is not None:
            self._create_sbp_file(fname_base+'.sbp', self['source_directionality'])

    def _write_env_header(self, fh: TextIO) -> None:
        """Writes header of env file."""
        self._print_env_line(fh,"'"+self['name']+"'","Bellhop environment name/description")
        self._print_env_line(fh,self['frequency'],"Frequency (Hz)")
        self._print_env_line(fh,1,"NMedia -- always =1 for Bellhop")

    def _write_env_surface_depth(self, fh: TextIO) -> None:
        """Writes surface boundary and depth lines of env file."""

        svp_interp = _Maps.soundspeed_interp_rev[self['soundspeed_interp']]
        svp_boundcond = _Maps.surface_boundary_condition_rev[self['surface_boundary_condition']]
        svp_attenuation_units = _Maps.attenuation_units_rev[self['attenuation_units']]
        svp_volume_attenuation = _Maps.volume_attenuation_rev[self['volume_attenuation']]
        svp_alti = _Maps._altimetry_rev[self['_altimetry']]
        svp_singlebeam = _Maps._single_beam_rev[self['_single_beam']]

        # Line 4
        comment = "SSP parameters: Interp / Top Boundary Cond / Attenuation Units / Volume Attenuation)"
        topopt = self._quoted_opt(svp_interp, svp_boundcond, svp_attenuation_units, svp_volume_attenuation, svp_alti, svp_singlebeam)
        self._print_env_line(fh,f"{topopt}",comment)

        if self['volume_attenuation'] == _Strings.francois_garrison:
            comment = "Francois-Garrison volume attenuation parameters (sal, temp, pH, depth)"
            self._print_env_line(fh,f"{self['fg_salinity']} {self['fg_temperature']} {self['fg_pH']} {self['fg_depth']}",comment)

        # Line 4a
        if self['surface_boundary_condition'] == _Strings.acousto_elastic:
            comment = "DEPTH_Top (m)  TOP_SoundSpeed (m/s)  TOP_SoundSpeed_Shear (m/s)  TOP_Density (g/cm^3)  [ TOP_Absorp [ TOP_Absorp_Shear ] ]"
            array_str = self._array2str([
              self['depth_max'],
              self['surface_soundspeed'],
              self['_surface_soundspeed_shear'],
              self._float(self['surface_density'],scale=1/1000),
              self['surface_attenuation'],
              self['_surface_attenuation_shear']
            ])
            self._print_env_line(fh,array_str,comment)

        # Line 4b
        if self['biological_layer_parameters'] is not None:
            self._write_env_biological(fh, self['biological_layer_parameters'])

    def _write_env_biological(self, fh: TextIO, biol: _pd.DataFrame) -> None:
        """Writes biological layer parameters to env file."""
        self._print_env_line(fh, biol.shape[0], "N_Biol_Layers / z1 z2 w0 Q a0")
        for j, row in enumerate(biol.values):
            self._print_env_line(fh, self._array2str(row), f"biol_{j}")

    def _write_env_sound_speed(self, fh: TextIO) -> None:
        """Writes sound speed profile lines of env file."""
        svp = self['soundspeed']

        comment = "[Npts - ignored]  [Sigma - ignored]  Depth_Max"
        self._print_env_line(fh,f"{self['_mesh_npts']} {self['_depth_sigma']} {self['depth_max']}",comment)

        svp_interp = _Maps.soundspeed_interp_rev[self['soundspeed_interp']]
        if isinstance(svp, _pd.DataFrame) and len(svp.columns) == 1:
            svp = _np.hstack((_np.array([svp.index]).T, _np.asarray(svp)))
        if svp.size == 1:
            self._print_env_line(fh,self._array2str([0.0, svp]),"Min_Depth SSP_Const")
            self._print_env_line(fh,self._array2str([self['depth_max'], svp]),"Max_Depth SSP_Const")
        elif svp_interp == "Q":
            for j in range(svp.shape[0]):
                self._print_env_line(fh,self._array2str([svp.index[j], svp.iloc[j,0]]),f"ssp_{j}")
        else:
            for j in range(svp.shape[0]):
                self._print_env_line(fh,self._array2str([svp[j,0], svp[j,1]]),f"ssp_{j}")

    def _write_env_bottom(self, fh: TextIO) -> None:
        """Writes bottom boundary lines of env file."""
        bot_bc = _Maps.bottom_boundary_condition_rev[self['bottom_boundary_condition']]
        dp_flag = _Maps._bathymetry_rev[self['_bathymetry']]
        bot_str = self._quoted_opt(bot_bc,dp_flag)
        comment = "BOT_Boundary_cond / BOT_Roughness"
        self._print_env_line(fh,f"{bot_str} {self['bottom_roughness']}",comment)
        if self['bottom_boundary_condition'] == "acousto-elastic":
            comment = "Depth_Max  BOT_SoundSpeed  BOT_SS_Shear  BOT_Density  BOT_Absorp  BOT_Absorp Shear"
            array_str = self._array2str([
              self['depth_max'],
              self['bottom_soundspeed'],
              self['_bottom_soundspeed_shear'],
              self._float(self['bottom_density'],scale=1/1000),
              self['bottom_attenuation'],
              self['_bottom_attenuation_shear']
            ])
            self._print_env_line(fh,array_str,comment)

    def _write_env_source_receiver(self, fh: TextIO) -> None:
        """Writes source and receiver lines of env file."""
        if self._dimension == 2:
            self._print_array(fh, self['source_depth'], nn=self['source_ndepth'], label="Source depth (m)")
            self._print_array(fh, self['receiver_depth'], nn=self['receiver_ndepth'], label="Receiver depth (m)")
            self._print_array(fh, self['receiver_range']/1000, nn=self['receiver_nrange'], label="Receiver range (km)")
        elif self._dimension == 3:
            self._print_array(fh, self['source_range']/1000, nn=self['source_nrange'], label="Source range (km)")
            self._print_array(fh, self['source_cross_range']/1000, nn=self['source_ncrossrange'], label="Source cross range (km)")
            self._print_array(fh, self['source_depth'], nn=self['source_ndepth'], label="Source depth (m)")
            self._print_array(fh, self['receiver_depth'], nn=self['receiver_ndepth'], label="Receiver depth (m)")
            self._print_array(fh, self['receiver_range']/1000, nn=self['receiver_nrange'], label="Receiver range (km)")
            self._print_array(fh, self['receiver_bearing'], nn=self['receiver_nbearing'], label="Receiver bearing (°)")

    def _write_env_task(self, fh: TextIO, taskcode: str) -> None:
        """Writes task lines of env file."""
        beamtype = _Maps.beam_type_rev[self['beam_type']]
        beampattern = " " if self['source_directionality'] is None else "*"
        txtype = _Maps.source_type_rev[self['source_type']]
        gridtype = _Maps.grid_type_rev[self['grid_type']]
        runtype_str = self._quoted_opt(taskcode, beamtype, beampattern, txtype, gridtype)
        self._print_env_line(fh,f"{runtype_str}","RUN TYPE")

    def _write_env_beam_footer(self, fh: TextIO) -> None:
        """Writes beam and footer lines of env file."""
        self._print_env_line(fh,self._array2str([self['beam_num'], self['single_beam_index']]),"Num_Beams_Inclination [ Single_Beam_Index ]")
        self._print_env_line(fh,f"{self['beam_angle_min']} {self['beam_angle_max']} /","Inclination angle min/max (°)")
        if self._dimension == 3:
            self._print_env_line(fh,f"{self['beam_bearing_num']}","Num_Beams_Bearing")
            self._print_env_line(fh,f"{self['beam_bearing_min']} {self['beam_bearing_max']} /","Bearing angle min/max (°)")
        if self._dimension == 2:
            self._print_env_line(fh,f"{self['step_size']} {self['box_depth']} {self['box_range'] / 1000}","Step_Size (m), ZBOX (m), RBOX (km)")
        elif self._dimension == 3:
            self._print_env_line(fh,f"{self['step_size']} {self['box_range'] / 1000} {self['box_cross_range'] / 1000} {self['box_depth']}","Step_Size (m), BoxRange (x) (km), BoxCrossRange (y) (km), BoxDepth (z) (m)")

    def _print(self, fh: TextIO, s: str, newline: bool = True) -> None:
        """Write a line of text with or w/o a newline char to the output file"""
        fh.write(s+'\n' if newline else s)

    def _print_env_line(self, fh: TextIO, data: Any, comment: str = "") -> None:
        """Write a complete line to the .env file with a descriptive comment

        We do some char counting (well, padding and stripping) to ensure the code comments all start from the same char.
        """
        data_str = data if isinstance(data,str) else f"{data}"
        comment_str = comment if isinstance(comment,str) else f"{comment}"
        line_str = (data_str + " " * self.comment_pad)[0:max(len(data_str),self.comment_pad)]
        if comment_str != "":
            line_str = line_str + " ! " + comment_str
        self._print(fh,line_str)

    def _print_array(self, fh: TextIO, a: Any, label: str = "", nn: Optional[int] = None) -> None:
        """Print a 1D array to the .env file, prefixed by a count of the array length"""
        na = _np.size(a)
        if nn is None:
            nn = na
        if nn == 1 or na == 1:
            self._print_env_line(fh, 1, f"{label} (single value)")
            self._print_env_line(fh, f"{a} /",f"{label} (single value)")
        else:
            self._print_env_line(fh, nn, f"{label}s ({nn} values)")
            for j in a:
                self._print(fh, f"{j} ", newline=False)
            self._print(fh, " /")

    def _create_bty_ati_file(self, filename: str, depth: Any, interp: _Strings) -> None:
        with open(filename, 'wt') as f:
            f.write(f"'{_Maps.depth_interp_rev[interp]}'\n")
            f.write(str(depth.shape[0])+"\n")
            for j in range(depth.shape[0]):
                f.write(f"{depth[j,0]/1000} {depth[j,1]}\n")

    def _create_sbp_file(self, filename: str, dir: Any) -> None:
        """Write data to sbp file"""
        with open(filename, 'wt') as f:
            f.write(str(dir.shape[0])+"\n")
            for j in range(dir.shape[0]):
                f.write(f"{dir[j,0]}  {dir[j,1]}\n")

    def _create_refl_coeff_file(self, filename: str, rc: Any) -> None:
        """Write data to brc/trc file"""
        with open(filename, 'wt') as f:
            f.write(str(rc.shape[0])+"\n")
            for j in range(rc.shape[0]):
                f.write(f"{rc[j,0]}  {rc[j,1]}  {rc[j,2]}\n")

    def _create_ssp_quad_file(self, filename: str, svp: _pd.DataFrame) -> None:
        """Write 2D SSP data to file"""
        with open(filename, 'wt') as f:
            f.write(str(svp.shape[1])+"\n") # number of SSP points
            for j in range(svp.shape[1]):
                f.write("%0.6f%c" % (svp.columns[j]/1000, '\n' if j == svp.shape[1]-1 else ' '))
            for k in range(svp.shape[0]):
                for j in range(svp.shape[1]):
                    f.write("%0.6f%c" % (svp.iloc[k,j], '\n' if j == svp.shape[1]-1 else ' '))

    def _array2str(self, values: List[Any]) -> str:
        """Format list into space-separated string, trimmed at first None, ending with '/'."""
        try:
            values = values[:values.index(None)]
        except ValueError:
            pass
        return " ".join(
            f"{v}" if isinstance(v, (int, float)) else str(v)
            for v in values
        ) + " /"

    def _quoted_opt(self, *args: str) -> str:
        """Concatenate N input _Strings. strip whitespace, surround with single quotes
        """
        combined = "".join(args).strip()
        return f"'{combined}'"

    def _float(self, x: Optional[float], scale: float = 1) -> Optional[float]:
        """Permissive floatenator"""
        return None if x is None else float(x) * scale

    def __getitem__(self, key: str) -> Any:
        if not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.__setattr__(key, value)

    def __setattr__(self, key: str, value: Any) -> None:
        if not hasattr(self, key):
            raise KeyError(f"Unknown environment configuration parameter: {key!r}")
        # Generalized validation of values
        allowed = getattr(_Maps, key, None)
        if allowed is not None and value is not None and value not in set(allowed.values()):
            raise ValueError(f"Invalid value for {key!r}: {value}. Allowed: {set(allowed.values())}")
        # coerce types
        if not (
            value is None or
            isinstance(value,_pd.DataFrame) or
            _np.isscalar(value)
               ):
            if not isinstance(value[0],str):
                value = _np.asarray(value, dtype=_np.float64)
        object.__setattr__(self, key, value)

    def __delitem__(self, key: str) -> None:
        raise KeyError("Environment parameters cannot be deleted")

    def __iter__(self) -> Iterator[str]:
        return (f.name for f in fields(self))

    def __len__(self) -> int:
        return len(fields(self))

    def __repr__(self) -> str:
        return pformat(self.to_dict())

    def to_dict(self) -> Dict[str,Any]:
        """Return a dictionary representation of the environment."""
        return asdict(self)

    def copy(self) -> "Environment":
        """Return a shallow copy of the environment."""
        # Copy all fields
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        # Return a new instance
        new_env = type(self)(**data)
        return new_env

    def _or_default(self, key: str, default: Any) -> Any:
        """Return the current value if not None, otherwise return and set a default."""
        val = getattr(self, key, None)
        if val is None:
            setattr(self, key, default)
            return default
        return val
