id4_common.utils.local_magics
=============================

.. py:module:: id4_common.utils.local_magics




Module Contents
---------------

.. py:class:: LocalMagics(shell=None, **kwargs)

   Bases: :py:obj:`bluesky.magics.BlueskyMagics`


   IPython magics for bluesky.

   To install:

   >>> ip = get_ipython()
   >>> ip.register_magics(BlueskyMagics)

   Optionally configure default detectors and positioners by setting
   the class attributes:

   * ``BlueskyMagics.detectors``
   * ``BlueskyMagics.positioners``

   For more advanced configuration, access the magic's RunEngine instance and
   ProgressBarManager instance:

   * ``BlueskyMagics.RE``
   * ``BlueskyMagics.pbar_manager``


   .. py:method:: wm(line)


   .. py:method:: mov(line)


   .. py:method:: movr(line)


   .. py:method:: wa(line)

      List positioner info. 'wa' stands for 'where all'.
