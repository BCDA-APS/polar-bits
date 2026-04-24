id4_common.utils.aps_dm_setup
=============================

.. py:module:: id4_common.utils.aps_dm_setup

.. autoapi-nested-parse::

   APS Data Management setup
   =========================

   Read the bash shell script file used by DM to setup the environment. Parse any
   ``export`` lines and add their environment variables to this session.  This is
   done by brute force here since the APS DM environment setup requires different
   Python code than bluesky and the two often clash.

   This setup must be done before any of the DM package libraries are called.
