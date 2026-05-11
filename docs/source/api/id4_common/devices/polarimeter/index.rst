id4_common.devices.polarimeter
==============================

.. py:module:: id4_common.devices.polarimeter

.. autoapi-nested-parse::

   Polarization analyzer





Module Contents
---------------

.. py:class:: PolAnalyzer(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.Device`


   Polarization analyzer assembly with theta/y motors and two pre-amplifiers.


   .. py:attribute:: y


   .. py:attribute:: th


   .. py:attribute:: vertical_preamp


   .. py:attribute:: horizontal_preamp


   .. py:method:: default_settings()

      Configure pre-amplifier signals for put_complete and disable string mode
      on offset_fine.
