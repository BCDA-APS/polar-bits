id4_common.utils.load_vortex
============================

.. py:module:: id4_common.utils.load_vortex

.. autoapi-nested-parse::

   Utilities for loading and connecting Vortex detector devices.







Module Contents
---------------

.. py:data:: logger

.. py:data:: DETECTORS

.. py:function:: load_vortex(electronic: str, pv: str = None, name: str = 'vortex', labels: list = None, baseline: bool = False, **kwargs)

   Load Vortex detector. kwargs are passed to the detector class.

   If a device named ``name`` already exists in the registry it is removed
   first. A warning is issued, and the warning is more prominent when the
   existing device is a different electronics type than the one being loaded.

   The device is added to the ``__main__`` namespace under ``name`` so it is
   available in the interactive session without capturing the return value.

   :param electronic: Name of the electronic. Must be one of the keys in DETECTORS:
                      "dante1", "dante4", "xmap", "xspress4", "xspress7".
   :type electronic: string
   :param pv: PV prefix of detector. If None it will use the default.
   :type pv: string, optional
   :param name: Bluesky name of the detector. Defaults to 'vortex'.
   :type name: str, optional
   :param labels: Bluesky labels. Defaults to ["detector"].
   :type labels: list of strings, optional
   :param baseline: Flag to add the device to the baseline. Defaults to False.
   :type baseline: bool, optional

   :returns: **vortex_detector**
   :rtype: Ophyd device


