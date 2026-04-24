id4_common.devices.nanopositioner
=================================

.. py:module:: id4_common.devices.nanopositioner

.. autoapi-nested-parse::

   Nanopositioner motors





Module Contents
---------------

.. py:class:: MyEpicsMotor(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, **kwargs)

   Bases: :py:obj:`ophyd.EpicsMotor`


   An EPICS motor record, wrapped in a :class:`Positioner`

   Keyword arguments are passed through to the base class, Positioner

   :param prefix: The record to use
   :type prefix: str
   :param read_attrs: The signals to be read during data acquisition (i.e., in read() and
                      describe() calls)
   :type read_attrs: sequence of attribute names
   :param name: The name of the device
   :type name: str, optional
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None
   :param settle_time: The amount of time to wait after moves to report status completion
   :type settle_time: float, optional
   :param timeout: The default timeout to use for motion requests, in seconds.
   :type timeout: float, optional


   .. py:method:: unstage()

      Unstage the device.

      This method returns the device to the state it was prior to the
      last `stage` call.

      This method should be as fast as feasible as it does not
      return a status object.

      This method must be idempotent, multiple calls (without a new
      call to 'stage') have no effect.

      :returns: **devices** -- list including self and all child devices unstaged
      :rtype: list



.. py:class:: NanoPositioner(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.MotorBundle`


   Sub-class this to device a bundle of motors

   This provides better default behavior for :ref:``hints``.


   .. py:attribute:: nanoy


   .. py:attribute:: nanox


   .. py:attribute:: nanoz
