id4_common.devices.table_4idb
=============================

.. py:module:: id4_common.devices.table_4idb

.. autoapi-nested-parse::

   Table in middle of 4idb





Module Contents
---------------

.. py:class:: Table4idb(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Optical table in 4IDB with upstream/downstream X and Y positioning motors.


   .. py:attribute:: x_us


   .. py:attribute:: x_ds


   .. py:attribute:: y_us


   .. py:attribute:: y_ds_in


   .. py:attribute:: y_ds_out


