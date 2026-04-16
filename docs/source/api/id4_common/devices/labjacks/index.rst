id4_common.devices.labjacks
===========================

.. py:module:: id4_common.devices.labjacks

.. autoapi-nested-parse::

   Labjacks







Module Contents
---------------

.. py:class:: AnalogOutput(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`apstools.devices.labjack.Output`


   A generic output record.

   Intended to be sub-classed into different output types.



   .. py:attribute:: description


   .. py:attribute:: value


   .. py:attribute:: low_limit


   .. py:attribute:: high_limit


   .. py:attribute:: readback_value
      :value: None



   .. py:attribute:: desired_value
      :value: None



.. py:function:: make_analog_outputs(num_aos: int)

   Create a dictionary with analog output device definitions.

   For use with an ophyd DynamicDeviceComponent.

   :param num_aos: How many analog outputs to create.


.. py:function:: make_digital_ios(channels_list: list)

   Create a dictionary with digital I/O device definitions.

   For use with an ophyd DynamicDeviceComponent.

   :param num_dios: How many digital I/Os to create.


.. py:class:: CustomLabJackT7(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`apstools.devices.LabJackT7`


   A labjack T-series data acquisition unit (DAQ).

   To use the individual components separately, consider using the
   corresponding devices in the list below.

   This device contains signals for the following:

   - device information (e.g. firmware version ,etc)
   - analog outputs (:py:class:`~apstools.devices.labjack.AnalogInput`)
   - analog inputs* (:py:class:`~apstools.devices.labjack.AnalogOutput`)
   - digital input/output* (:py:class:`~apstools.devices.labjack.DigitalIO`)
   - waveform digitizer* (:py:class:`~apstools.devices.labjack.WaveformDigitizer`)
   - waveform generator (:py:class:`~apstools.devices.labjack.WaveformGenerator`)

   The number of inputs and digital outputs depends on the specific
   LabJack T-series device being used. Therefore, the base device
   ``LabJackBase`` does not implement these I/O signals. Instead,
   consider using one of the subclasses, like ``LabJackT4``.

   The ``.trigger()`` method does not do much. To retrieve fresh
   values for analog inputs where .SCAN is passive, you will need to
   trigger the individual inputs themselves.

   The waveform generator and waveform digitizer are included for
   convenience. Reading all the analog/digital inputs and outputs can
   be done by calling the ``.read()`` method. However, it is unlikely
   that the goal is also to trigger the digitizer and generator
   during this read. For this reason, **the digitizer and generator
   have kind="omitted"**. To trigger the digitizer or generator, they
   can be used as separate devices:

   .. code:: python

       lj = LabJackT4(...)

       # Read a waveform from the digitizer
       lj.waveform_digitizer.trigger().wait()
       lj.waveform_digitizer.read()

       # Same thing for the waveform generator
       lj.waveform_generator.trigger().wait()



   .. py:attribute:: analog_outputs


   .. py:attribute:: digital_ios


   .. py:method:: default_settings()


