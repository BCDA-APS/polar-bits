id4_common.utils.spe_handler
============================

.. py:module:: id4_common.utils.spe_handler

.. autoapi-nested-parse::

   Handler for SPE files





Module Contents
---------------

.. py:class:: SPEHandler(fpath, template, filename, frame_per_point=1)

   Bases: :py:obj:`area_detector_handlers.HandlerBase`


   Base-class for Handlers to provide the boiler plate to
   make them usable in context managers by provding stubs of
   ``__enter__``, ``__exit__`` and ``close``


   .. py:attribute:: specs


   .. py:method:: get_file_list(datum_kwarg_gen)
