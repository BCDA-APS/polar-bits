id4_common.utils.shorts
=======================

.. py:module:: id4_common.utils.shorts

.. autoapi-nested-parse::

   Short convenience wrappers for common session operations.





Module Contents
---------------

.. py:function:: opt(method='cen')

   Move positioner of last scan to center of last scan

   usage: RE(opt())
       optional argument:      method = 'cen' (default)
                                               method = 'max'




.. py:function:: crl_setup(hutch=None)

   Switch the CRL sample-position offset to the active hutch.

   Delegates to :meth:`CRLClass.select_g` / ``select_h``, which
   write to the IOC's ``ZOffsetToggle`` PV.  The per-hutch offset values
   themselves live on the device as ``crl.offset_g`` / ``offset_h`` and
   are not changed here.

   :param hutch: Hutch to switch to.  Case-insensitive, accepts ``"G"`` / ``"H"``
                 and the longer aliases ``"diffractometer"`` (= G) /
                 ``"magnet"`` (= H) for backwards compatibility.  When ``None``
                 (default), prompt interactively.
   :type hutch: {'g', 'h'}, optional


.. py:function:: crl_size(focal_size)

   Set the CRL focal size.

   Renamed from ``crl`` so the function does not shadow the ``crl``
   device that ``load_device("crl")`` injects into the session
   namespace.

   :param focal_size: Target focal size in microns. If < 5 µm, the device's
                      ``minimize_button`` is triggered instead of writing a setpoint.
                      Otherwise the value is written to ``crl.beamsize`` (which handles
                      the microns -> meters conversion internally).
   :type focal_size: float


.. py:function:: te(temperature)

   Set the active temperature controller's setpoint.

   Thin shortcut over the ``tc`` signal installed by
   :func:`id4_common.utils.temperature_setup.temperature_setup`.  Writes
   the setpoint and returns immediately; the controller continues ramping
   toward the target on its own.

   :param temperature: Target temperature setpoint.
   :type temperature: float

   :raises RuntimeError: ``temperature_setup()`` has not been run, so there is no active
       controller to talk to.


