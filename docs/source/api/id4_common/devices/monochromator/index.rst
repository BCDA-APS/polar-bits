id4_common.devices.monochromator
================================

.. py:module:: id4_common.devices.monochromator

.. autoapi-nested-parse::

   Monochromator with energy controller by bluesky





Module Contents
---------------

.. py:class:: MonoDevice(prefix, *, pzt_thf2_pv='4idaSoft:LJ:Ao5', pzt_chi2_pv='4idaSoft:LJ:Ao3', **kwargs)

   Bases: :py:obj:`ophyd.PseudoPositioner`


   A pseudo positioner which can be comprised of multiple positioners

   :param prefix: The PV prefix for all components of the device
   :type prefix: str
   :param concurrent: If set, all real motors will be moved concurrently. If not, they will
                      be moved in order of how they were defined initially
   :type concurrent: bool, optional
   :param read_attrs: the components to include in a normal reading (i.e., in ``read()``)
   :type read_attrs: sequence of attribute names
   :param configuration_attrs: the components to be read less often (i.e., in
                               ``read_configuration()``) and to adjust via ``configure()``
   :type configuration_attrs: sequence of attribute names
   :param name: The name of the device
   :type name: str, optional
   :param egu: The user-defined engineering units for the whole PseudoPositioner
   :type egu: str, optional
   :param auto_target: Automatically set the target position of PseudoSingle devices when
                       moving to a single PseudoPosition
   :type auto_target: bool, optional
   :param parent: The instance of the parent device, if applicable
   :type parent: instance or None
   :param settle_time: The amount of time to wait after moves to report status completion
   :type settle_time: float, optional
   :param timeout: The default timeout to use for motion requests, in seconds.
   :type timeout: float, optional


   .. py:attribute:: energy


   .. py:attribute:: th


   .. py:attribute:: y2


   .. py:attribute:: crystal_select


   .. py:attribute:: thf2


   .. py:attribute:: chi2


   .. py:attribute:: pzt_thf2


   .. py:attribute:: pzt_chi2


   .. py:attribute:: y_offset


   .. py:attribute:: crystal_h


   .. py:attribute:: crystal_k


   .. py:attribute:: crystal_l


   .. py:attribute:: crystal_a


   .. py:attribute:: crystal_2d


   .. py:attribute:: crystal_type


   .. py:method:: convert_energy_to_theta(energy)


   .. py:method:: convert_energy_to_y(energy)


   .. py:method:: convert_theta_to_energy(theta)


   .. py:method:: forward(pseudo_pos)

      Run a forward (pseudo -> real) calculation



   .. py:method:: inverse(real_pos)

      Run an inverse (real -> pseudo) calculation



   .. py:method:: set_energy(energy)


   .. py:method:: default_settings()


