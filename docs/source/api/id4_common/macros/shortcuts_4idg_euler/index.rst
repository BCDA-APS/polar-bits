id4_common.macros.shortcuts_4idg_euler
======================================

.. py:module:: id4_common.macros.shortcuts_4idg_euler

.. autoapi-nested-parse::

   Bind 4-ID-G Euler diffractometer motor shortcuts into the interactive session.

   Resolves the diffractometer from ``oregistry`` at import time and
   assigns each named sub-device to ``__main__`` under the same short
   name. Importing this module is the side-effect: ``import
   id4_common.macros.shortcuts_4idg_euler`` makes ``h``, ``k``, ``l``,
   ``gamma``, ``delta``, ... directly usable in the IPython session.





Module Contents
---------------

.. py:data:: logger

.. py:data:: MAIN_NAMESPACE
   :value: '__main__'


.. py:data:: namespace

.. py:data:: dev
