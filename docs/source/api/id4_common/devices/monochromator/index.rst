id4_common.devices.monochromator
================================

.. py:module:: id4_common.devices.monochromator

.. autoapi-nested-parse::

   Monochromator with energy controller by bluesky



Classes
-------

.. autoapisummary::

   id4_common.devices.monochromator.MonoDevice


Module Contents
---------------

.. py:class:: MonoDevice(prefix, *, pzt_thf2_pv='4idaSoft:LJ:Ao5', pzt_chi2_pv='4idaSoft:LJ:Ao3', **kwargs)

   Bases: :py:obj:`ophyd.PseudoPositioner`


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


