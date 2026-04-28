id4_common.utils.load_vortex
============================

.. py:module:: id4_common.utils.load_vortex






Module Contents
---------------

.. py:data:: logger

.. py:data:: DETECTORS

.. py:function:: load_vortex(electronic: str, pv: str = None, name: str = 'vortex', labels: list = ['detector'], baseline: bool = False, **kwargs)

   Load Vortex detector. kwargs are passed to the detector class.

   :param electronic: Name of the electronic. Currently must be one of: dante, xmap,
                      xspress4, xspress7
   :type electronic: string
   :param pv: PV prefix of detector. If None it will use the default.
   :type pv: string, optional
   :param name: Bluesky name of the detector. Defaults to 'vortex'.
   :type name: str, optional
   :param labels: Bluesky labels. Defaults to ["detectexior",]
   :type labels: list of strings, optional
   :param baseline: Flag to add the device to the baseline. Defaults to False.
   :type baseline: bool, optional

   :returns: **vortex_detector**
   :rtype: Ophyd device
