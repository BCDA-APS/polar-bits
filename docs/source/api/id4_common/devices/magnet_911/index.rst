id4_common.devices.magnet_911
=============================

.. py:module:: id4_common.devices.magnet_911

.. autoapi-nested-parse::

   9T magnet



Classes
-------

.. autoapisummary::

   id4_common.devices.magnet_911.TableMotors
   id4_common.devices.magnet_911.RamanMotors
   id4_common.devices.magnet_911.MagnetMotors
   id4_common.devices.magnet_911.FieldPositioner
   id4_common.devices.magnet_911.PowerSupply
   id4_common.devices.magnet_911.MonChannel
   id4_common.devices.magnet_911.VTIDevice
   id4_common.devices.magnet_911.NVDevice
   id4_common.devices.magnet_911.Magnet911


Module Contents
---------------

.. py:class:: TableMotors

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z


   .. py:attribute:: sx


   .. py:attribute:: sz


   .. py:attribute:: srot


.. py:class:: RamanMotors

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z


   .. py:attribute:: tilt


   .. py:attribute:: rot


.. py:class:: MagnetMotors

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: y


   .. py:attribute:: th


.. py:class:: FieldPositioner(*args, **kwargs)

   Bases: :py:obj:`ophyd.PVPositioner`


   .. py:attribute:: setpoint


   .. py:attribute:: readback


   .. py:attribute:: actuate


   .. py:attribute:: actuate_value
      :value: 1



   .. py:attribute:: done


   .. py:attribute:: done_value
      :value: 1



   .. py:attribute:: current


   .. py:attribute:: voltage


   .. py:attribute:: egu_readback


   .. py:attribute:: egu_setpoint


   .. py:method:: move(position, wait=True, timeout=None, moved_cb=None)


.. py:class:: PowerSupply

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: field


   .. py:attribute:: active_coil


   .. py:attribute:: safety_message


   .. py:attribute:: status


   .. py:attribute:: ready


   .. py:attribute:: heater


   .. py:attribute:: quench


   .. py:attribute:: helium


   .. py:attribute:: persistent_field


   .. py:attribute:: ramp_rate


   .. py:attribute:: ramp_rate_unit


   .. py:attribute:: set_ignore_table


   .. py:attribute:: set_persistent


   .. py:attribute:: set_pm_zero


   .. py:attribute:: ramp_pause


   .. py:attribute:: ramp_start


   .. py:attribute:: ramp_abort


   .. py:attribute:: read_button


   .. py:attribute:: read_scan


.. py:class:: MonChannel(*args, ch_num=1, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: temperature_name


   .. py:attribute:: temperature


   .. py:attribute:: hall_resistance


   .. py:attribute:: hall_field


   .. py:attribute:: read_button


   .. py:attribute:: read_scan


   .. py:attribute:: ch
      :value: 1



.. py:class:: VTIDevice

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: sensor_a


   .. py:attribute:: sensor_b


   .. py:attribute:: sensor_c


   .. py:attribute:: sensor_d


   .. py:attribute:: setpoint_1


   .. py:attribute:: setpoint_2


   .. py:attribute:: setpoint_3


   .. py:attribute:: setpoint_4


   .. py:attribute:: read_button


   .. py:attribute:: read_scan


.. py:class:: NVDevice

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: control_mode


   .. py:attribute:: pressure_control_switch


   .. py:attribute:: temp


   .. py:attribute:: pressure


   .. py:attribute:: read_button


   .. py:attribute:: read_scan


.. py:class:: Magnet911

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: connection


   .. py:attribute:: tab


   .. py:attribute:: raman


   .. py:attribute:: samp


   .. py:attribute:: ps


   .. py:attribute:: monitors


   .. py:attribute:: temps


   .. py:attribute:: needle_valve


