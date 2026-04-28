id4_common.utils.make_devices
=============================

.. py:module:: id4_common.utils.make_devices

.. autoapi-nested-parse::

   Local overrides of ``apsbits`` ``make_devices`` and
   ``guarneri_namespace_loader`` that add a ``connect`` flag.

   When ``connect=False``, devices are instantiated and registered in
   ``__main__`` / the ``oregistry`` but no EPICS connections are attempted.
   This restores the documented "deferred connection" pattern so that explicit
   ``connect_device(...)`` calls own all EPICS I/O — avoiding the
   ``DEFAULT_TIMEOUT`` wait and ``NotConnectedError`` log spam for devices
   whose IOCs are intentionally off.

   These are line-for-line copies of the upstream functions in
   ``apsbits.core.instrument_init`` with the single addition of the
   ``connect`` parameter. Drop these helpers once apsbits exposes the same
   flag upstream.







Module Contents
---------------

.. py:data:: logger

.. py:data:: MAIN_NAMESPACE
   :value: '__main__'


.. py:function:: make_devices(*, pause: float = 1, clear: bool = True, file: str, path: str | pathlib.Path | None = None, device_manager=None, connect: bool = True)

   Initialize ophyd-style devices using a device manager, optionally
   connect them, then make them part of the main namespace.

   Local override of ``apsbits.core.instrument_init.make_devices`` that
   adds the ``connect`` flag.

   PARAMETERS

   pause : float
       Wait 'pause' seconds (default: 1) for slow objects to connect.
   clear : bool
       Clear 'oregistry' first if True (the default).
   file : str | pathlib.Path | None
       Path to a YAML/TOML file containing device configurations.
   path : str | pathlib.Path | None
       Optional alternative configs directory.
   device_manager :
       The device manager to use. Currently only 'guarneri' is supported.
   connect : bool
       If True (default), eagerly try to connect every device after
       loading. If False, skip the connect step entirely — devices are
       instantiated and registered, but no EPICS I/O is performed. Use
       this when later ``connect_device(...)`` calls handle connections.


.. py:function:: guarneri_namespace_loader(yaml_device_file, instrument=None, oregistry=None, main=True, connect: bool = True)
   :async:


   Load our ophyd-style controls as described in a YAML file into the
   main namespace.

   Local override of
   ``apsbits.core.instrument_init.guarneri_namespace_loader`` that adds
   the ``connect`` flag. When ``connect=False`` the eager
   ``await instrument.connect()`` call is skipped.

   PARAMETERS

   yaml_device_file : str or pathlib.Path
       YAML file describing ophyd-style controls to be created.
   main : bool
       If ``True`` add these devices to the ``__main__`` namespace.
   connect : bool
       If True (default), eagerly try to connect every device. If False,
       only load and register them.



