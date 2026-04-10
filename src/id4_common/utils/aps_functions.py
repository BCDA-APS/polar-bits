"""
APS utility helper functions.
=============================

``aps_dm_setup`` was removed from apsbits in 2.0+. It is vendored here
as a temporary measure until it can be properly integrated into apstools
(see apstools issue #1147).

.. autosummary::

    ~aps_dm_setup
"""

import logging
import os
import pathlib

logger = logging.getLogger(__name__)


def aps_dm_setup(dm_setup_file_path):
    """
    APS Data Management setup.

    Read the bash shell script file used by DM to setup the environment.
    Parse any ``export`` lines and add their environment variables to this
    session. This is done by brute force here since the APS DM environment
    setup requires different Python code than bluesky and the two often clash.

    This setup must be done before any of the DM package libraries are called.
    """
    if dm_setup_file_path is not None:
        bash_script = pathlib.Path(dm_setup_file_path)
        if bash_script.exists():
            logger.info("APS DM environment file: %s", str(bash_script))
            environment = {}
            for line in open(bash_script).readlines():
                if not line.startswith("export "):
                    continue
                export_part = line.strip().split("export ", 1)[-1]
                if not export_part:
                    continue
                if "=" in export_part:
                    k, v = export_part.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                else:
                    k = export_part.strip()
                    v = ""
                environment[k] = v
            os.environ.update(environment)

            workflow_owner = os.environ.get("DM_STATION_NAME", "").lower()
            logger.info("APS DM workflow owner: %s", workflow_owner)
        else:
            logger.warning(
                "APS DM setup file does not exist: '%s'", bash_script
            )
