id4_common.callbacks.spec_data_file_writer
==========================================

.. py:module:: id4_common.callbacks.spec_data_file_writer

.. autoapi-nested-parse::

   custom callbacks
   ================

   .. autosummary::
       :nosignatures:

       ~newSpecFile
       ~spec_comment
       ~specwriter







Module Contents
---------------

.. py:data:: logger

.. py:data:: iconfig

.. py:data:: file_extension

.. py:function:: spec_comment(comment, doc=None)

   Make it easy for user to add comments to the data file.


.. py:function:: newSpecFile(title, scan_id=None, RE=None)

   User choice of the SPEC file name.

   Cleans up title, prepends month and day and appends file extension.
   If ``RE`` is passed, then resets ``RE.md["scan_id"] = scan_id``.

   If the SPEC file already exists, then ``scan_id`` is ignored and
   ``RE.md["scan_id"]`` is set to the last scan number in the file.


.. py:function:: init_specwriter_with_RE(RE)

   Initialize specwriter with the run engine.


.. py:data:: specwriter

   The SPEC file writer object.

