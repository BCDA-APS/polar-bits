id4_common.devices.magnet_kepco_4idg
====================================

.. py:module:: id4_common.devices.magnet_kepco_4idg

.. autoapi-nested-parse::

   Diffractometer magnet







Module Contents
---------------

.. py:data:: logger

.. py:class:: KepcoDevice(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Base class for device objects

   This class provides attribute access to one or more Signals, which can be
   a mixture of read-only and writable. All must share the same base_name.

   :param prefix: The PV prefix for all components of the device
   :type prefix: str, optional
   :param name: The name of the device (as will be reported via read()`
   :type name: str, keyword only
   :param kind: (or equivalent integer), optional
                Default is ``Kind.normal``. See :class:`~ophydobj.Kind` for options.
   :type kind: a member of the :class:`~ophydobj.Kind` :class:`~enum.IntEnum`
   :param read_attrs: DEPRECATED: the components to include in a normal reading
                      (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: DEPRECATED: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None, optional
   :param connection_timeout: Timeout for connection of all underlying signals.

                              The default value DEFAULT_CONNECTION_TIMEOUT means, "Fall back to
                              class-wide default." See Device.set_defaults to
                              configure class defaults.

                              Explicitly passing None means, "Wait forever."
   :type connection_timeout: float or None, optional

   .. attribute:: lazy_wait_for_connection

      When instantiating a lazy signal upon first access, wait for it to
      connect before returning control to the user.  See also the context
      manager helpers: ``wait_for_lazy_connection`` and
      ``do_not_wait_for_lazy_connection``.

      :type: bool

   .. attribute:: Subscriptions



   .. attribute:: -------------



   .. attribute:: SUB_ACQ_DONE

      A one-time subscription indicating the requested trigger-based
      acquisition has completed.


   .. py:attribute:: manufacturer


   .. py:attribute:: model


   .. py:attribute:: model2


   .. py:attribute:: calibration


   .. py:attribute:: serial


   .. py:attribute:: firmware


   .. py:attribute:: status


   .. py:attribute:: status_output


   .. py:attribute:: status_list


   .. py:attribute:: status_errors


   .. py:attribute:: status_mode


   .. py:attribute:: status_protect


   .. py:attribute:: status_message


   .. py:attribute:: last_error_message


   .. py:attribute:: field


   .. py:attribute:: voltage


   .. py:attribute:: current


   .. py:attribute:: mode


   .. py:attribute:: enable


   .. py:attribute:: current_protection_positive


   .. py:attribute:: current_protection_negative


   .. py:attribute:: voltage_protection_positive


   .. py:attribute:: voltage_protection_negative


   .. py:attribute:: current_limit_positive


   .. py:attribute:: current_limit_negative


   .. py:attribute:: voltage_limit_positive


   .. py:attribute:: voltage_limit_negative


   .. py:attribute:: t1


   .. py:attribute:: t2


   .. py:attribute:: t3


   .. py:attribute:: status_temperature


   .. py:method:: default_settings()


   .. py:method:: start_auto_mode()


   .. py:method:: stop_auto_mode()
