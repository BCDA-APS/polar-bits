id4_common.devices.polar_status
===============================

.. py:module:: id4_common.devices.polar_status

.. autoapi-nested-parse::

   Polar status



Classes
-------

.. autoapisummary::

   id4_common.devices.polar_status.HutchStatus
   id4_common.devices.polar_status.AStatus
   id4_common.devices.polar_status.Status4ID


Module Contents
---------------

.. py:class:: HutchStatus(prefix, hutch=None, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: user_enable


   .. py:attribute:: aps_enable


   .. py:attribute:: searched


   .. py:attribute:: beam_present


   .. py:attribute:: shutter


.. py:class:: AStatus(prefix, hutch=None, **kwargs)

   Bases: :py:obj:`HutchStatus`


   .. py:attribute:: shutter


.. py:class:: Status4ID

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: online


   .. py:attribute:: acis


   .. py:attribute:: fe_eps


   .. py:attribute:: a_hutch


   .. py:attribute:: b_hutch


   .. py:attribute:: g_hutch


   .. py:attribute:: h_hutch


