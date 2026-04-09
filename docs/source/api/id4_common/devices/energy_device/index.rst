id4_common.devices.energy_device
================================

.. py:module:: id4_common.devices.energy_device

.. autoapi-nested-parse::

   Beamline energy



Attributes
----------

.. autoapisummary::

   id4_common.devices.energy_device.logger


Classes
-------

.. autoapisummary::

   id4_common.devices.energy_device.EnergySignal


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


   .. py:property:: feedback_device


   .. py:method:: get(**kwargs)

      Uses the mono as the standard beamline energy.



   .. py:method:: set(position, *, wait=False, timeout=None, settle_time=None, moved_cb=None)


   .. py:method:: stop(*, success=False)

      Stops only energy devices that are tracking.



   .. py:method:: default_settings()


