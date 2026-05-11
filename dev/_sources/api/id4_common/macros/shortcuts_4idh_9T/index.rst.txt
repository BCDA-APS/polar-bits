id4_common.macros.shortcuts_4idh_9T
===================================

.. py:module:: id4_common.macros.shortcuts_4idh_9T

.. autoapi-nested-parse::

   Bind 4-ID-H 9-Tesla magnet motor shortcuts into the interactive session.

   Resolves ``magnet911`` from ``oregistry`` at import time, walks each
   ``device.subattr`` dotted path, and assigns the resulting object to
   ``__main__`` under the requested short name. Importing this module is
   the side-effect: ``import id4_common.macros.shortcuts_4idh_9T`` makes
   ``field``, ``tabx``, ``sy``, ... directly usable in the IPython
   session.





Module Contents
---------------

.. py:data:: logger

.. py:data:: MAIN_NAMESPACE
   :value: '__main__'


.. py:data:: namespace

.. py:data:: dev

