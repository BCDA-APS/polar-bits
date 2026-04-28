id4_common.devices.kb_generic
=============================

.. py:module:: id4_common.devices.kb_generic

.. autoapi-nested-parse::

   Generic KB mirror device factory with configurable motor PV suffixes.







Module Contents
---------------

.. py:function:: make_kb_class(v_motors: dict, h_motors: dict) -> type

   Return a KBDevice class with specified motor PV suffixes.

   :param v_motors: Mapping of vertical motor attribute names to PV suffixes, e.g.
                    ``{"ds_piezo": "m4", "us_piezo": "m5", ...}``.
   :type v_motors: dict
   :param h_motors: Mapping of horizontal motor attribute names to PV suffixes.
   :type h_motors: dict

   :returns: A KBDevice class composed of Vertical and Horizontal sub-devices.
   :rtype: type


.. py:data:: GKBDevice

.. py:data:: HKBDevice
