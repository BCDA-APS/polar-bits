id4_common.devices.magnet_nanopositioner
========================================

.. py:module:: id4_common.devices.magnet_nanopositioner

.. autoapi-nested-parse::

   Magnet Nanopositioner motors





Module Contents
---------------

.. py:class:: NanoPositioner(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.MotorBundle`


   Sub-class this to device a bundle of motors

   This provides better default behavior for :ref:``hints``.


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: z
