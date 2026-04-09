id4_common.devices.aps_undulator
================================

.. py:module:: id4_common.devices.aps_undulator

.. autoapi-nested-parse::

   Undulator support



Classes
-------

.. autoapisummary::

   id4_common.devices.aps_undulator.PolarUndulatorPositioner
   id4_common.devices.aps_undulator.PolarUndulator
   id4_common.devices.aps_undulator.PhaseShifterDevice
   id4_common.devices.aps_undulator.PolarUndulatorPair


Module Contents
---------------

.. py:class:: PolarUndulatorPositioner

   Bases: :py:obj:`apstools.devices.aps_undulator.UndulatorPositioner`


   .. py:method:: set(new_position: Any, *, timeout: float = None, moved_cb: Callable = None, wait: bool = False) -> ophyd.status.StatusBase


.. py:class:: PolarUndulator

   Bases: :py:obj:`apstools.devices.STI_Undulator`


   .. py:attribute:: tracking


   .. py:attribute:: energy_offset


   .. py:attribute:: energy_deadband


   .. py:attribute:: energy


   .. py:attribute:: version_hpmu
      :value: None



.. py:class:: PhaseShifterDevice(*args, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: gap


   .. py:attribute:: start_button


   .. py:attribute:: stop_button


   .. py:attribute:: done


   .. py:attribute:: gap_deadband


   .. py:attribute:: device_limit


   .. py:attribute:: device


   .. py:attribute:: location


   .. py:attribute:: message1


   .. py:attribute:: message2


.. py:class:: PolarUndulatorPair

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: us


   .. py:attribute:: ds


   .. py:attribute:: phase_shifter


