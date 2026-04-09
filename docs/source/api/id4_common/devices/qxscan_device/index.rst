id4_common.devices.qxscan_device
================================

.. py:module:: id4_common.devices.qxscan_device

.. autoapi-nested-parse::

   Define qxscan_setup device.

   This device will holds the parameters and energy list used in a qxscan plan.



Attributes
----------

.. autoapisummary::

   id4_common.devices.qxscan_device.logger
   id4_common.devices.qxscan_device.hbar
   id4_common.devices.qxscan_device.speed_of_light
   id4_common.devices.qxscan_device.electron_mass
   id4_common.devices.qxscan_device.constant


Classes
-------

.. autoapisummary::

   id4_common.devices.qxscan_device.EdgeDevice
   id4_common.devices.qxscan_device.PreEdgeRegion
   id4_common.devices.qxscan_device.PreEdgeDevice
   id4_common.devices.qxscan_device.PostEdgeRegion
   id4_common.devices.qxscan_device.PostEdgeDevice
   id4_common.devices.qxscan_device.QxscanParams


Module Contents
---------------

.. py:data:: logger

.. py:data:: hbar
   :value: 6.582119569e-16


.. py:data:: speed_of_light
   :value: 2.99792458e+18


.. py:data:: electron_mass

.. py:data:: constant

.. py:class:: EdgeDevice

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: Estart


   .. py:attribute:: Eend


   .. py:attribute:: Estep


   .. py:attribute:: TimeFactor


.. py:class:: PreEdgeRegion

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: Estart


   .. py:attribute:: Estep


   .. py:attribute:: TimeFactor


.. py:class:: PreEdgeDevice

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: num_regions


   .. py:attribute:: region1


   .. py:attribute:: region2


   .. py:attribute:: region3


   .. py:attribute:: region4


   .. py:attribute:: region5


.. py:class:: PostEdgeRegion

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: Kend


   .. py:attribute:: Kstep


   .. py:attribute:: TimeFactor


.. py:class:: PostEdgeDevice

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: num_regions


   .. py:attribute:: region1


   .. py:attribute:: region2


   .. py:attribute:: region3


   .. py:attribute:: region4


   .. py:attribute:: region5


.. py:class:: QxscanParams

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: pre_edge


   .. py:attribute:: edge


   .. py:attribute:: post_edge


   .. py:attribute:: energy_list


   .. py:attribute:: factor_list


   .. py:method:: save_params_json(fname)

      Save a json file that contains a dictionary with the qxscan parameters.

      :param fname:
      :type fname: string
      :param Location and name of the file to be saved.:

      :rtype: None



   .. py:method:: load_params_json(fname)

      Load a json file that contains a dictionary with the qxscan parameters.

      This dictionary must be formatted as required by
      self._read_params_dict.

      :param fname:
      :type fname: string
      :param Location and name of the file to be loaded:

      :rtype: None



   .. py:method:: load_from_scan(scan, cat=cat)


