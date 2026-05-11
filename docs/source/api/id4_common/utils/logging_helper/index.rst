id4_common.utils.logging_helper
===============================

.. py:module:: id4_common.utils.logging_helper

.. autoapi-nested-parse::

   Centralized bluesky-session logging configuration for POLAR beamlines.







Module Contents
---------------

.. py:data:: logger

.. py:function:: setup_logging()

   Configure bluesky logging from the LOGGING block of iconfig.yml.

   The block is translated to the apsbits `file_logs`/`ipython_logs` schema
   on the fly (via a temporary YAML file passed to apsbits'
   ``configure_logging(extra_logging_configs_path=...)``) so polar-bits keeps
   a single config file.

   Falls back to the apsbits default directory (``<cwd>/.logs/``) when no
   LOG_PATH is configured or when the centralized directory cannot be
   created — typically a developer machine without access to the beamline
   filesystem.  The IPython log file always uses our filename
   (``ipython_logs.log``), regardless of which directory wins.

   Idempotent: subsequent calls are no-ops so importing several beamline
   packages (or importing one whose ``__init__.py`` chains through
   id4_common) doesn't re-run `%logstart` and re-print the settings block.
