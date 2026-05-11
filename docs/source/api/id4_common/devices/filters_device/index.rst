id4_common.devices.filters_device
=================================

.. py:module:: id4_common.devices.filters_device

.. autoapi-nested-parse::

   APS filter support









Module Contents
---------------

.. py:data:: NUM_FILTERS
   :value: 12


.. py:class:: FilterSlot(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Single filter slot with status, lock, material, and transmission readbacks.


   .. py:attribute:: status


   .. py:attribute:: lock


   .. py:attribute:: material


   .. py:attribute:: thickness


   .. py:attribute:: enable


   .. py:attribute:: transmission


.. py:function:: make_filter_slots(num: int)

   Return an OrderedDict of FilterSlot component definitions for a
   DynamicDeviceComponent.


.. py:class:: APSFilter(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   APS filter bank with energy-based transmission control and per-slot
   management.


   .. py:attribute:: energy_select


   .. py:attribute:: mono_energy


   .. py:attribute:: local_energy


   .. py:attribute:: status


   .. py:attribute:: transmission_readback


   .. py:attribute:: transmission_setpoint


   .. py:attribute:: transmission_factor


   .. py:attribute:: mask_readback


   .. py:attribute:: mask_setpoint


   .. py:attribute:: message


   .. py:attribute:: slots


   .. py:attribute:: wait_time


   .. py:attribute:: debug_level
