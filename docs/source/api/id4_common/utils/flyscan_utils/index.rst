id4_common.utils.flyscan_utils
==============================

.. py:module:: id4_common.utils.flyscan_utils

.. autoapi-nested-parse::

   Utility functions for flyscans



Attributes
----------

.. autoapisummary::

   id4_common.utils.flyscan_utils.logger


Functions
---------

.. autoapisummary::

   id4_common.utils.flyscan_utils.read_flyscan_stream
   id4_common.utils.flyscan_utils.find_eiger_triggers


Module Contents
---------------

.. py:data:: logger

.. py:function:: read_flyscan_stream(fname, base_key='stream')

   Reads a flyscan HDF5 stream file.


.. py:function:: find_eiger_triggers(fname, key='Attocube 1 ch. 3')

   Finds the points where the Eiger was triggered


