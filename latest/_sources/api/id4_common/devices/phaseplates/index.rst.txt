id4_common.devices.phaseplates
==============================

.. py:module:: id4_common.devices.phaseplates

.. autoapi-nested-parse::

   Phase retarders.





Module Contents
---------------

.. py:class:: MicronsSignal(parent_attr, *, parent=None, **kwargs)

   Bases: :py:obj:`ophyd.DerivedSignal`


   A signal that converts the offset from degrees to microns


   .. py:method:: describe()

      Override describe to report units as microns.



   .. py:method:: inverse(value)

      Compute original signal value -> derived signal value



   .. py:method:: forward(value)

      Compute derived signal value -> original signal value



.. py:class:: PRPzt(PV, *args, drio_prefix='4idaSoft:232DRIO:1:', **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Phase retarder PZT


   .. py:attribute:: remote_setpoint


   .. py:attribute:: remote_readback


   .. py:attribute:: localdc


   .. py:attribute:: center


   .. py:attribute:: offset_degrees


   .. py:attribute:: offset_microns


   .. py:attribute:: servoon


   .. py:attribute:: servooff


   .. py:attribute:: servostatus


   .. py:attribute:: selectDC


   .. py:attribute:: selectAC


   .. py:attribute:: ACstatus


   .. py:attribute:: conversion_factor


.. py:class:: PRDeviceBase(prefix, name, motorsDict, **kwargs)

   Bases: :py:obj:`ophyd.PseudoPositioner`


   Base class for phase retarder devices mapping energy to Bragg angle.


   .. py:attribute:: energy


   .. py:attribute:: th


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: d_spacing


   .. py:attribute:: offset_degrees


   .. py:attribute:: motor_switch


   .. py:attribute:: tracking


   .. py:method:: convert_energy_to_theta(energy)

      Convert photon energy (keV) to Bragg angle (degrees) using the crystal
      d-spacing.



   .. py:method:: convert_theta_to_energy(theta)

      Convert Bragg angle (degrees) to photon energy (keV) using the crystal
      d-spacing.



   .. py:method:: forward(pseudo_pos)

      Run a forward (pseudo -> real) calculation



   .. py:method:: inverse(real_pos)

      Run an inverse (real -> pseudo) calculation



   .. py:method:: set_energy(energy)

      Calibrate the Bragg-angle motor to match the given photon energy (keV).



   .. py:method:: default_settings()

      Apply default d-spacing and motor-switch settings for this phase
      retarder.



.. py:class:: PRDevice(prefix, name, prnum, motorsDict, **kwargs)

   Bases: :py:obj:`PRDeviceBase`


   Phase retarder with PZT piezo control and crystal-plane auto-selection.


   .. py:attribute:: pzt


   .. py:attribute:: select_pr


   .. py:method:: default_settings()

      Set PZT conversion factor and d-spacing based on the selected crystal
      plane.



