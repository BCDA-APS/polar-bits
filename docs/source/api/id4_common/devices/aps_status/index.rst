id4_common.devices.aps_status
=============================

.. py:module:: id4_common.devices.aps_status

.. autoapi-nested-parse::

   APS status





Module Contents
---------------

.. py:class:: StatusAPS(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Device exposing APS ring current and operational status signals.


   .. py:attribute:: current


   .. py:attribute:: machine_status


   .. py:attribute:: operating_mode


   .. py:attribute:: shutter_status


