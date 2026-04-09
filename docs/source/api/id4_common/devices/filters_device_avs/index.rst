id4_common.devices.filters_device_avs
=====================================

.. py:module:: id4_common.devices.filters_device_avs

.. autoapi-nested-parse::

   APS filter support



Attributes
----------

.. autoapisummary::

   id4_common.devices.filters_device_avs.NUM_FILTERS


Classes
-------

.. autoapisummary::

   id4_common.devices.filters_device_avs.FilterSlot
   id4_common.devices.filters_device_avs.APSFilter


Functions
---------

.. autoapisummary::

   id4_common.devices.filters_device_avs.make_filter_slots


Module Contents
---------------

.. py:data:: NUM_FILTERS
   :value: 12


.. py:class:: FilterSlot

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: setpoint


   .. py:attribute:: readback


   .. py:attribute:: lock


   .. py:attribute:: enable


   .. py:attribute:: material


   .. py:attribute:: thickness


   .. py:attribute:: control_pv


   .. py:attribute:: control_in_value


   .. py:attribute:: readback_pv


   .. py:attribute:: readback_in_value


.. py:function:: make_filter_slots(num: int)

.. py:class:: APSFilter

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: energy_select


   .. py:attribute:: mono_energy


   .. py:attribute:: local_energy


   .. py:attribute:: energy


   .. py:attribute:: status


   .. py:attribute:: attenuation_setpoint


   .. py:attribute:: attenuation_readback


   .. py:attribute:: sorted_index


   .. py:attribute:: attenuation_2e_harmonic


   .. py:attribute:: attenuation_3e_harmonic


   .. py:attribute:: inter_filter_delay


   .. py:attribute:: filters


