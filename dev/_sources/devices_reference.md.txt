# Device Reference

All devices are defined in `src/id4_common/configs/devices.yml` and loaded at
session startup based on their labels. Use `find_loadable_devices()` to query
available devices interactively.

```python
find_loadable_devices()                    # all devices
find_loadable_devices(label="4idg")        # filter by hutch
find_loadable_devices(label="detector")    # filter by function
find_loadable_devices(name="kb")           # substring search by name
```

---

## Core Devices

Loaded by **all** hutches (label: `"core"`).

### Beam Source and Diagnostics

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `aps_xbpm` | `MyXBPM` | `S04` | APS X-ray BPM (sector 4) | `source`, `baseline` |
| `undulators` | `PolarUndulatorPair` | `S04ID:` | Upstream + downstream undulator pair | `source`, `energy device`, `baseline` |
| `status_aps` | `StatusAPS` | — | APS machine status (current, mode) | `source`, `status`, `baseline` |
| `status_polar` | `Status4ID` | `S04ID-PSS:` | POLAR beamline PSS status | `status`, `baseline` |

### Monochromator and Energy

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `mono` | `MonoDevice` | `4idVDCM:` | Si(111) double-crystal monochromator | `monochromator`, `energy device`, `baseline` |
| `mono_feedback` | `MonoFeedback` | `4idbSoft:` | Monochromator feedback (EPID) | `monochromator`, `feedback`, `baseline` |
| `energy` | `EnergySignal` | — | Beamline energy (tracks `mono`) | `energy device`, `baseline` |

### Phase Retarders

| Name | Class | EPICS Prefix | Motors | Labels |
|------|-------|-------------|--------|--------|
| `pr1` | `PRDevice` | `4ida` | `x=m1, y=m2, th=m4` | `phase retarder`, `energy device`, `track_energy`, `baseline` |
| `pr2` | `PRDevice` | `4ida` | `x=m6, y=m7, th=m9` | `phase retarder`, `energy device`, `track_energy`, `baseline` |
| `pr3` | `PRDeviceBase` | `4ida` | `x=m10, y=m11, th=m12` | `phase retarder`, `energy device`, `track_energy`, `baseline` |

### Optics and Beam Conditioning

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `hhl_mirror` | `ToroidalMirror` | `4idHHLM:` | HHL (high-heat-load) toroidal mirror | `mirror`, `baseline` |
| `t_mirror` | `ToroidalMirror` | `4idbToro:` | Toroidal focusing mirror | `optics`, `mirror`, `baseline` |
| `wbslt` | `SlitDevice` | `4idVDCM:` | White-beam slits (`hor, diag, pitch, yaw`) | `slit`, `baseline` |
| `monoslt` | `SlitDevice` | `4idVDCM:` | Post-monochromator slits (`top, bot, out, inb`) | `slit`, `baseline` |
| `diamond_window` | `WindowStages` | `4idbSoft:` | Diamond window insertion stages | `baseline` |

### Shutters

| Name | Class | Description | Labels |
|------|-------|-------------|--------|
| `ashutter` | `PolarShutter` | Front-end shutter (A-shutter) | `shutter`, `baseline` |
| `bshutter` | `ApsPssShutterWithStatus` | Secondary shutter (B-shutter) | `shutter`, `baseline` |

### Data Management and Misc

| Name | Class | Description | Labels |
|------|-------|-------------|--------|
| `dm_workflow` | `DM_WorkflowConnector` | APS DM workflow submission | `dm`, `baseline` |
| `dm_experiment` | `ophyd.Signal` | DM experiment name (soft signal) | `dm`, `baseline` |
| `labjack_4ida` | `CustomLabJackT7` | LabJack T7 DAQ at 4IDA | `baseline` |
| `qxscan_setup` | `QxscanParams` | Parameters for Q-space scans | `qxscan`, `energy device`, `baseline` |

---

## Scalers and Counters (4IDB, 4IDG, 4IDH)

These are shared across the three downstream hutches.

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `scaler1` | `LocalScalerCH` | `4idCTR8_1:scaler1` | Multi-channel scaler (bank 1) | `detector`, `scaler`, `4idb`, `4idg`, `4idh` |
| `scaler2` | `LocalScalerCH` | `4idCTR8_1:scaler2` | Multi-channel scaler (bank 2) | `detector`, `scaler`, `4idb`, `4idg`, `4idh` |
| `ctr8` | `CustomMeasCompCtr` | `4idCTR8_1:` | USB-CTR8 counter/timer | `detector`, `4idb`, `4idg`, `4idh`, `baseline` |

---

## 4IDB Devices

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `bslt` | `SlitDevice` | `4idbSoft:` | 4IDB beam-defining slits (`top, bot, out, inb`) | `slit`, `baseline` |
| `bkb` | `KBMirror` | `4idbSoft:` | KB mirror pair | `optics`, `baseline` |
| `bfilter` | `APSFilter` | `4idbSoft:filter:` | Attenuator filter bank | `filter`, `baseline` |
| `btetramm` | `TetrAMMRO` | `4idbSoft:TetrAMM:` | TetrAMM quad-electrometer / XBPM | `detector`, `xbpm`, `baseline` |
| `emag` | `Magnet2T` | `4idb:` / `4idbSoft:BOP:PS1:` | 2T electromagnet + Kepco power supply | `magnet`, `baseline` |
| `pol` | `PolAnalyzer` | `4idbSoft:` | Polarimeter / analyzer | `baseline` |
| `midtable_4idb` | `Table4idb` | `4idbSoft:` | Sample positioning table | `baseline` |
| `labjack_4idb` | `CustomLabJackT7` | `4idbSoft:LJ:` | LabJack T7 at 4IDB | `baseline` |
| `preamp_4idbI0` | `LocalPreAmp` | `4idbSoft:A3` | I0 pre-amplifier | `preamp`, `baseline` |
| `preamp_4idbI` | `LocalPreAmp` | `4idbSoft:A4` | I (transmitted) pre-amplifier | `preamp`, `baseline` |

---

## 4IDG Devices

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `huber_euler` | `CradleDiffractometer` | `4idgSoft:` | Huber Euler 6-circle diffractometer | `diffractometer`, `baseline` |
| `huber_euler_psi` | `CradlePSI` | `4idgSoft:` | Huber Euler — psi engine | `diffractometer`, `baseline` |
| `huber_hp` | `HPDiffractometer` | `4idgSoft:` | HP (high-pressure) diffractometer | `diffractometer`, `baseline` |
| `huber_hp_psi` | `HPPSI` | `4idgSoft:` | HP diffractometer — psi engine | `diffractometer`, `baseline` |
| `gkb` | `GKBDevice` | `4idgKB:` | KB mirror pair (4IDG) | `optics`, `kb`, `baseline` |
| `transfocator` | `TransfocatorClass` | `4idPyCRL:CRL4ID:` | Compound refractive lens (shared 4IDG/4IDH) | `optics`, `track_energy`, `baseline` |
| `gfilter` | `APSFilter` | `4idPyFilter:FL1:` | Attenuator filter bank (4IDG) | `filter`, `baseline` |
| `gxbpm` | `XBPM` | `4idgSoft:` | XBPM with positioning motors (`x=m48, y=m47`) | `baseline` |
| `gsydor` | `SydorEMRO` | `4idgSydor:T4U_BPM:` | Sydor EM T4U beam position monitor | `detector`, `xbpm`, `baseline` |
| `eiger` | `Eiger1MDetector` | `4idEiger:` | Dectris Eiger 1M area detector | `detector` |
| `temp_336_4idg` | `LakeShore336Device` | `4idgSoft:LS336:TC1:` | LakeShore 336 temperature controller | `temperature`, `baseline` |
| `temp_340_4idg` | `LakeShore340Device` | `4idgSoftX:LS340:TC1:` | LakeShore 340 temperature controller | `temperature`, `baseline` |
| `i0g` | `I04idg` | `4idgSoft:` | I0 monitor motors (4IDG) | `baseline` |
| `preamp_4idgI0` | `LocalPreAmp` | `4idgSoftX:A1` | I0 pre-amplifier (4IDG) | `preamp`, `baseline` |
| `preamp_4idgI` | `LocalPreAmp` | `4idgSoftX:A2` | I (transmitted) pre-amplifier (4IDG) | `preamp`, `baseline` |

---

## 4IDH Devices

| Name | Class | EPICS Prefix | Description | Labels |
|------|-------|-------------|-------------|--------|
| `magnet911` | `Magnet911` | `4idhSoft:` | 9T-1T-1T superconducting vector magnet | `magnet`, `baseline` |
| `hkb` | `HKBDevice` | `4idhKB:` | KB mirror pair (4IDH) | `optics`, `kb`, `baseline` |
| `transfocator` | `TransfocatorClass` | `4idPyCRL:CRL4ID:` | Compound refractive lens (shared 4IDG/4IDH) | `optics`, `track_energy`, `baseline` |
| `hfilter` | `APSFilter` | `4idPyFilter:FL2:` | Attenuator filter bank (4IDH) | `filter`, `baseline` |
| `hxbpm` | `XBPM` | `4idhSoft:` | XBPM with positioning motors (`x=m6, y=m5`) | `baseline` |
| `hsydor` | `SydorEMRO` | `4idhSydor:T4U_BPM:` | Sydor EM T4U beam position monitor | `detector`, `xbpm`, `baseline` |
| `table_4idh` | `Table4idh` | `4idhSoft:` | Sample positioning table | `table`, `baseline` |
| `i0h` | `I04idh` | `4idhSoft:` | I0 monitor motors (4IDH) | `baseline` |
| `preamp_4idhI0` | `LocalPreAmp` | `4idhSoft:A1` | I0 pre-amplifier (4IDH) | `preamp`, `baseline` |
| `preamp_4idhI1` | `LocalPreAmp` | `4idhSoft:A2` | I1 pre-amplifier (4IDH) | `preamp`, `baseline` |
| `preamp_4idhI2` | `LocalPreAmp` | `4idhSoft:A3` | I2 pre-amplifier (4IDH) | `preamp`, `baseline` |

---

## Shared Cameras and Flags

These diagnostic cameras are loaded on demand (not in a hutch's default station set).

| Name | Class | EPICS Prefix | Location | Labels |
|------|-------|-------------|----------|--------|
| `flagcam_hhl` | `VimbaDetector` | `4idaPostMirrBeam:` | Post-HHL mirror | `camera`, `detector`, `flag` |
| `flagcam_mono` | `VimbaDetector` | `4idaPostMonoBeam:` | Post-monochromator | `camera`, `detector`, `flag` |
| `flagcam_toro` | `VimbaDetector` | `4idbPostToroBeam:` | Post-toroidal mirror | `camera`, `detector`, `flag` |
| `flagcam_xeye` | `VimbaDetector` | `4idXrayEye:` | X-ray eye | `camera`, `detector`, `flag` |
| `flagmotor_hhl` | `EpicsMotor` | `4idVDCM:m6` | Flag motor post-HHL | `motor`, `flag`, `baseline` |
| `flagmotor_mono` | `EpicsMotor` | `4idVDCM:m7` | Flag motor post-mono | `motor`, `flag`, `baseline` |
| `flagmotor_toro` | `EpicsMotor` | `4idbSoft:m3` | Flag motor post-toro | `motor`, `flag`, `baseline` |
| `chopper` | `ChopperDevice` | `4idChopper:` | Chopper (time-resolved mode) | `baseline` |
| `sgz_vortex` | `SGZVortex` | `4iddMZ0:` | SoftGlueZynq Vortex MCA | `detector` |
