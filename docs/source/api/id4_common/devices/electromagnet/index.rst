id4_common.devices.electromagnet
================================

.. py:module:: id4_common.devices.electromagnet

.. autoapi-nested-parse::

   Electromagnet.





Module Contents
---------------

.. py:class:: Magnet2T(prefix, *, motor_prefix, kepco_prefix, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   2 Tesla electromagnet with sample and magnet positioning motors.


   .. py:attribute:: sx


   .. py:attribute:: sy


   .. py:attribute:: srot


   .. py:attribute:: mx


   .. py:attribute:: my


   .. py:attribute:: mrot


   .. py:attribute:: kepco


   .. py:method:: default_settings()

      Apply default settings to the Kepco controller.
