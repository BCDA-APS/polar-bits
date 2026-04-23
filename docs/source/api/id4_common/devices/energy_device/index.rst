id4_common.devices.energy_device
================================

.. py:module:: id4_common.devices.energy_device

.. autoapi-nested-parse::

   Beamline energy







Module Contents
---------------

.. py:data:: logger

.. py:class:: EnergySignal(*args, mono_name='mono', feedback_name='mono_feedback', feedback_tolerance=0.1, **kwargs)

   Bases: :py:obj:`ophyd.Signal`


   Beamline energy.
   The monochromator defines the beamline energy.


   .. py:property:: mono


   .. py:property:: trackable_devices


   .. py:property:: extra_devices


   .. py:property:: tracking


   .. py:method:: tracking_setup(devices_names: collections.abc.Iterable = [])


   .. py:property:: position


   .. py:property:: limits

      The control limits (low, high), such that low <= value <= high


   .. py:property:: feedback_device


   .. py:method:: get(**kwargs)

      Uses the mono as the standard beamline energy.



   .. py:method:: set(position, *, wait=False, timeout=None, settle_time=None, moved_cb=None)

      Set the value of the Signal and return a Status object.

      :returns: **st** -- This status object will be finished upon return in the
                case of basic soft Signals
      :rtype: Status



   .. py:method:: stop(*, success=False)

      Stops only energy devices that are tracking.



   .. py:method:: default_settings()


