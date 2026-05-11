id4_common.devices.interferometers_4IDG
=======================================

.. py:module:: id4_common.devices.interferometers_4IDG

.. autoapi-nested-parse::

   Interferometer setup





Module Contents
---------------

.. py:class:: InterferometerDevice(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Six-channel interferometer readout for mirror horizontal and vertical
   positions.


   .. py:attribute:: mhor_up


   .. py:attribute:: mhor_down


   .. py:attribute:: shor


   .. py:attribute:: mvert_up


   .. py:attribute:: mvert_down


   .. py:attribute:: svert


   .. py:method:: plot_first_pos1()

      Set only the mhor_up channel as hinted and all others to normal.



   .. py:method:: plot_all()

      Set all six interferometer channels to hinted kind for plotting.
