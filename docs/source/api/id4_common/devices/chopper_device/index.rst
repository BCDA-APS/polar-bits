id4_common.devices.chopper_device
=================================

.. py:module:: id4_common.devices.chopper_device

.. autoapi-nested-parse::

   Chopper





Module Contents
---------------

.. py:class:: ChopperDevice(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Photon chopper with translation motor, Newport controller, and frequency
   readback.


   .. py:attribute:: translation


   .. py:attribute:: status


   .. py:attribute:: frequency_readback


   .. py:attribute:: frequency_setpoint


   .. py:attribute:: phase


   .. py:attribute:: wheel


   .. py:attribute:: sync


   .. py:attribute:: mode
