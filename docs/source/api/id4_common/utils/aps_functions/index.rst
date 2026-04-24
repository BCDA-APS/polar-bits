id4_common.utils.aps_functions
==============================

.. py:module:: id4_common.utils.aps_functions

.. autoapi-nested-parse::

   APS utility helper functions.
   =============================

   ``aps_dm_setup`` was removed from apsbits in 2.0+. It is vendored here
   as a temporary measure until it can be properly integrated into apstools
   (see apstools issue #1147).

   .. autosummary::

       ~aps_dm_setup







Module Contents
---------------

.. py:data:: logger

.. py:function:: aps_dm_setup(dm_setup_file_path)

   APS Data Management setup.

   Read the bash shell script file used by DM to setup the environment.
   Parse any ``export`` lines and add their environment variables to this
   session. This is done by brute force here since the APS DM environment
   setup requires different Python code than bluesky and the two often clash.

   This setup must be done before any of the DM package libraries are called.
