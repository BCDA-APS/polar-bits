id4_common.devices.transfocator_device
======================================

.. py:module:: id4_common.devices.transfocator_device

.. autoapi-nested-parse::

   Transfocator.









Module Contents
---------------

.. py:data:: logger

.. py:data:: DEFAULT_MOTORS_IOC
   :value: '4idgSoft:'


.. py:data:: EPICS_ENERGY_SLEEP
   :value: 0.15


.. py:class:: PyCRLSingleLens(prefix='', *, limits=None, name=None, read_attrs=None, configuration_attrs=None, parent=None, egu='', **kwargs)

   Bases: :py:obj:`ophyd.PVPositioner`


   Single CRL lens stack positioner.


   .. py:attribute:: readback


   .. py:attribute:: setpoint


   .. py:attribute:: done


   .. py:attribute:: done_value
      :value: 1



   .. py:attribute:: num_lenses


   .. py:attribute:: radius


   .. py:attribute:: location


   .. py:attribute:: material


   .. py:attribute:: thickness_error


   .. py:attribute:: in_limit


   .. py:method:: set(new_position, *, timeout: float = None, moved_cb=None, wait: bool = False)

      Set lens position, returning immediately if already there.



.. py:class:: PyCRLSignal(read_pv, write_pv=None, *, put_complete=False, string=False, limits=False, name=None, **kwargs)

   Bases: :py:obj:`ophyd.EpicsSignal`


   EpicsSignal with a value sub-component and EGU readback.


   .. py:attribute:: value

      The signal's value


   .. py:attribute:: egu


.. py:class:: PyCRL(*args, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   PyCRL compound refractive lens controller.


   .. py:attribute:: energy_mono


   .. py:attribute:: energy_local


   .. py:attribute:: energy_select


   .. py:attribute:: slit_hor_size


   .. py:attribute:: slit_hor_pv


   .. py:attribute:: slit_vert_size


   .. py:attribute:: slit_vert_pv


   .. py:attribute:: focal_size_setpoint


   .. py:attribute:: focal_size_readback


   .. py:attribute:: focal_power_index


   .. py:attribute:: focal_sizes


   .. py:attribute:: minimize_button


   .. py:attribute:: system_done


   .. py:attribute:: dq


   .. py:attribute:: q


   .. py:attribute:: z_offset


   .. py:attribute:: z_offset_pv


   .. py:attribute:: z_from_source


   .. py:attribute:: sample_offset


   .. py:attribute:: sample_offset_pv


   .. py:attribute:: sample


   .. py:attribute:: binary


   .. py:attribute:: ind_control


   .. py:attribute:: readbacks


   .. py:attribute:: preview_index


   .. py:attribute:: focal_size_preview


   .. py:attribute:: inter_lens_delay


   .. py:attribute:: verbose_console


   .. py:attribute:: thickness_error_flag


   .. py:attribute:: beam_mode


   .. py:attribute:: lens1


   .. py:attribute:: lens2


   .. py:attribute:: lens3


   .. py:attribute:: lens4


   .. py:attribute:: lens5


   .. py:attribute:: lens6


   .. py:attribute:: lens7


   .. py:attribute:: lens8


   .. py:method:: set(value, **kwargs)

      Set the system state.



.. py:class:: EnergySignal(*, name, value=_DefaultFloat(0.0), dtype=None, shape=None, timestamp=None, parent=None, labels=None, kind=Kind.hinted, tolerance=None, rtolerance=None, metadata=None, cl=None, attr_name='')

   Bases: :py:obj:`ophyd.Signal`


   Signal that moves the transfocator to a new energy.


   .. py:method:: put(*args, **kwargs)
      :abstractmethod:


      Raise NotImplementedError — use set() instead.



   .. py:method:: set(value, **kwargs)

      Move transfocator to the specified energy.



.. py:class:: ZMotor(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, **kwargs)

   Bases: :py:obj:`ophyd.EpicsMotor`


   EpicsMotor that optionally tracks X/Y when Z moves.


   .. py:method:: set(new_position, **kwargs)

      Move Z and optionally track X/Y.



   .. py:method:: stop(*, success=False)

      Stop Z and optionally X/Y.



.. py:function:: make_transfocator_class(motors_ioc=DEFAULT_MOTORS_IOC)

   Return a TransfocatorClass with lens motors bound to motors_ioc.

   :param motors_ioc: IOC prefix for the transfocator stage motors, e.g. ``"4idgSoft:"``.
   :type motors_ioc: str


.. py:data:: TransfocatorClass
