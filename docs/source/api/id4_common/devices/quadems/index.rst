id4_common.devices.quadems
==========================

.. py:module:: id4_common.devices.quadems

.. autoapi-nested-parse::

   QuadEMs for POLAR





Module Contents
---------------

.. py:class:: StatsPluginQuadEM(*args, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.StatsPlugin`


   Remove property attribute found in AD IOCs now.


   .. py:attribute:: kind
      :value: 'config'



.. py:class:: QuadEMPOLAR(*args, **kwargs)

   Bases: :py:obj:`ophyd.QuadEM`


   This trigger mixin class takes one acquisition per trigger.

   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


   .. py:attribute:: image


   .. py:attribute:: current1


   .. py:attribute:: current2


   .. py:attribute:: current3


   .. py:attribute:: current4


   .. py:attribute:: sum_all


   .. py:attribute:: sumall_mean


   .. py:attribute:: sumall_fast


   .. py:attribute:: sumall_sigma


   .. py:attribute:: sumx_mean


   .. py:attribute:: sumx_fast


   .. py:attribute:: sumx_sigma


   .. py:attribute:: sumy_mean


   .. py:attribute:: sumy_fast


   .. py:attribute:: sumy_sigma


   .. py:attribute:: diffx_mean


   .. py:attribute:: diffx_fast


   .. py:attribute:: diffx_sigma


   .. py:attribute:: diffy_mean


   .. py:attribute:: diffy_fast


   .. py:attribute:: diffy_sigma


   .. py:attribute:: posx_mean


   .. py:attribute:: posx_fast


   .. py:attribute:: posx_sigma


   .. py:attribute:: posy_mean


   .. py:attribute:: posy_fast


   .. py:attribute:: posy_sigma


   .. py:property:: preset_monitor


.. py:class:: TetrAMM(*args, **kwargs)

   Bases: :py:obj:`QuadEMPOLAR`


   This trigger mixin class takes one acquisition per trigger.

   .. rubric:: Examples

   >>> class SimDetector(SingleTrigger):
   ...     pass
   >>> det = SimDetector('..pv..')
   # optionally, customize name of image
   >>> det = SimDetector('..pv..', image_name='fast_detector_image')


   .. py:attribute:: conf


.. py:class:: QuadEMRO_mixins(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

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


   .. py:attribute:: dummy


   .. py:property:: preset_monitor


   .. py:method:: trigger()

      Start acquisition



   .. py:method:: stage()

      Stage the device for data collection.

      This method is expected to put the device into a state where
      repeated calls to :meth:`~BlueskyInterface.trigger` and
      :meth:`~BlueskyInterface.read` will 'do the right thing'.

      Staging not idempotent and should raise
      :obj:`RedundantStaging` if staged twice without an
      intermediate :meth:`~BlueskyInterface.unstage`.

      This method should be as fast as is feasible as it does not return
      a status object.

      The return value of this is a list of all of the (sub) devices
      stage, including it's self.  This is used to ensure devices
      are not staged twice by the :obj:`~bluesky.run_engine.RunEngine`.

      This is an optional method, if the device does not need
      staging behavior it should not implement `stage` (or
      `unstage`).

      :returns: **devices** -- list including self and all child devices staged
      :rtype: list



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



.. py:class:: SydorEMRO(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`QuadEMRO_mixins`, :py:obj:`QuadEMPOLAR`


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


   .. py:attribute:: conf


   .. py:attribute:: num_channels
      :value: None



   .. py:attribute:: read_format
      :value: None



   .. py:attribute:: trigger_mode
      :value: None



   .. py:attribute:: bias_interlock
      :value: None



   .. py:attribute:: bias_state
      :value: None



   .. py:attribute:: bias_voltage
      :value: None



   .. py:attribute:: hvi_readback
      :value: None



   .. py:attribute:: hvs_readback
      :value: None



   .. py:attribute:: hvv_readback
      :value: None



   .. py:attribute:: image
      :value: None



   .. py:method:: default_settings()


.. py:class:: TetrAMMRO(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`QuadEMRO_mixins`, :py:obj:`TetrAMM`


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


   .. py:method:: default_settings()
