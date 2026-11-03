"""
Copy an hklpy2 diffractometer's orientation setup onto another one.

Used by the simulated diffractometers' ``sync_setup()`` and by
``reload_all_devices()``, which rebuilds every diffractometer and would
otherwise leave the new objects with hklpy2's default sample.

Imports nothing beyond the standard library, so it loads (and can be tested)
where libhkl is not installed.
"""

import copy


def copy_setup(source, target):
    """Copy the orientation setup of ``source`` into ``target``.

    Replaces the target's samples (lattice, reflections, U and UB), active
    sample, constraints, extras, presets and mode.  Never moves a motor, and
    leaves the target's wavelength alone.

    ``source.configuration`` would also read the beam wavelength and the
    auxiliary motors over EPICS, so the target's own configuration is used as
    the template and only the orientation sections are taken from the source.
    Every ``restore_*`` flag is passed explicitly: hklpy2 skips samples,
    extras and mode by default on a hardware-backed target.

    Parameters
    ----------
    source, target : hklpy2 DiffractometerBase
        Device copied from, and device written to.
    """
    core = source.core
    config = target.configuration
    config["samples"] = copy.deepcopy(
        {name: sample._asdict() for name, sample in core._samples.items()}
    )
    config["sample_name"] = core.sample.name
    config["constraints"] = copy.deepcopy(core.constraints._asdict())
    config["axes"]["extra_axes"] = dict(core.all_extras)
    config["presets"] = copy.deepcopy(core._mode_presets)
    target.restore(
        config,
        clear=True,
        restore_constraints=True,
        restore_wavelength=False,
        restore_mode=False,
        restore_samples=True,
        restore_extras=True,
        restore_presets=True,
    )
    target.core.mode = core.mode
