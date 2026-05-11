id4_common.utils.oregistry_auxiliar
===================================

.. py:module:: id4_common.utils.oregistry_auxiliar

.. autoapi-nested-parse::

   Auxiliary utilities for querying and displaying the ophyd device registry.





Module Contents
---------------

.. py:function:: get_devices(label)

   Prints a table with the devices that have the label.

   :param label: Label to be searched. This will be something like "scaler".
   :type label: str

   :rtype: None

   .. seealso:: :func:`ophydregistry.Registry.findall`


