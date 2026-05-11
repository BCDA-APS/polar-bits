id4_common.devices.table_4idh
=============================

.. py:module:: id4_common.devices.table_4idh

.. autoapi-nested-parse::

   Table in middle of 4idb





Module Contents
---------------

.. py:class:: Table4idh(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Optical table in 4IDH with individual leg motors and combined X/Y/pitch/yaw
   pseudo-axes.


   .. py:attribute:: x_us


   .. py:attribute:: x_ds


   .. py:attribute:: y_us


   .. py:attribute:: y_ds


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: ax


   .. py:attribute:: ay


