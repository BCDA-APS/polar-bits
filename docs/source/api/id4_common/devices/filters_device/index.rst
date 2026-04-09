id4_common.devices.filters_device
=================================

.. py:module:: id4_common.devices.filters_device

.. autoapi-nested-parse::

   APS filter support



Attributes
----------

.. autoapisummary::

   id4_common.devices.filters_device.NUM_FILTERS


Classes
-------

.. autoapisummary::

   id4_common.devices.filters_device.FilterSlot
   id4_common.devices.filters_device.APSFilter


Functions
---------

.. autoapisummary::

   id4_common.devices.filters_device.make_filter_slots


Module Contents
---------------

.. py:data:: NUM_FILTERS
   :value: 12


.. py:class:: FilterSlot

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: status


   .. py:attribute:: lock


   .. py:attribute:: material


   .. py:attribute:: thickness


   .. py:attribute:: enable


   .. py:attribute:: transmission


.. py:function:: make_filter_slots(num: int)

.. py:class:: APSFilter

   Bases: :py:obj:`ophyd.Device`


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


