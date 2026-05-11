id4_common.devices.piezo_jena
=============================

.. py:module:: id4_common.devices.piezo_jena

.. autoapi-nested-parse::

   PiezoJena control via the 4-ID-G MOXA serial gateway.

   The PiezoJena controller is wired to channel 2 of the MOXA box exposed
   by the asyn record at ``4idgSoftX:asyn_MOXA_G:2``. The asynRecord protocol
   uses three fields:

       .TMOD   transmit mode (1 = write, 0 = read/write)
       .AOUT   ASCII output (the command sent on the wire)
       .TINP   ASCII input  (the response read back)

   Wire commands:

       modon,<axis>,1   switch the modulation input on <axis> ON
                        (external modulation enabled)
       modon,<axis>,0   switch the modulation input on <axis> OFF
                        (external modulation disabled)
       modon,<axis>     query modulation-input state on <axis>;
                        response lands in .TINP

   where <axis> is 0 (x), 1 (y), or 2 (z).





Module Contents
---------------

.. py:class:: PiezoJena(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   PiezoJena status / input control via MOXA channel 2.


   .. py:attribute:: tmod


   .. py:attribute:: aout


   .. py:attribute:: tinp


   .. py:method:: modulation_input_on(axis)

      Switch the modulation input on `axis` ON (external modulation
      enabled). Sends ``modon,<axis>,1``.



   .. py:method:: modulation_input_off(axis)

      Switch the modulation input on `axis` OFF (external modulation
      disabled). Sends ``modon,<axis>,0``.



   .. py:method:: read_status(axis, settle_time=0.2)

      Issue a status query for `axis` and return the .TINP response.

      Switches .TMOD to 0 (read/write), writes the bare ``modon,<axis>``
      query on .AOUT, waits ``settle_time`` seconds for the asyn
      record to push the response into .TINP, then returns the
      latest .TINP value.



