"""POLAR ISN 2D piezo fly-scan plan.

Drives both piezo axes through SoftGlue RAMs (matches POLAR_scan.py):

* **Fast axis** = X piezo (``huber_hp.nanox``, PV ``4idgSoftX:jena:m1``),
  driven continuously by the snake waveform in the ``mem`` / ``driveRAM``
  channel via DAC1 (see :meth:`SoftGlueZynq.snake_x`).
* **Slow axis** = Y piezo (``huber_hp.nanoy``, PV ``4idgSoftX:jena:m2``),
  driven by the step waveform in the ``mem2`` / ``driveRAMx`` channel
  via DAC2, advancing one increment per fast-axis snake cycle (see
  :meth:`SoftGlueZynq.snake_y`).

POLAR has no coarse stage motors — ``nanox`` and ``nanoy`` are the only
sample positioners. Analog input from the SoftGlue DACs into the
PiezoJena controller is gated by
:meth:`PiezoJena.modulation_input_on` / ``_off`` per axis (channel 0 =
X, channel 1 = Y).

DAC swing + modulation behaviour
--------------------------------
The PiezoJena modulation input is **summed** with the EPICS-driven
setpoint, and the SoftGlue DAC contributes a 0..+40 um offset on top:

    piezo_position = nanox.user_setpoint + dac_offset      (um)
    dac_offset      = 0 ... +40        (DAC 0 V .. 5 V)

The DAC sweep is **centred on the DAC midpoint** (20 um offset, = 2.5
V). For a scan width W = x_max - x_min, the DAC swings:

    [DAC_CENTRE - W/2,  DAC_CENTRE + W/2]  =  [20 - W/2, 20 + W/2]

To put that swing on top of the user-requested scan window
``[x0 + x_min, x0 + x_max]``, the plan shifts the EPICS motor by:

    shift_x = (x_min + x_max)/2 - DAC_CENTRE_UM
            = (x_min + x_max)/2 - 20

so that ``EPICS + DAC = x0 + (x_min+x_max)/2 + DAC_OFFSET``. For a
symmetric scan ``x_min = -a, x_max = +a`` the shift is always -20 um;
asymmetric scans shift by the scan-centre offset minus 20.

Centring on the DAC midpoint (rather than anchoring at 0 V) means
the DAC1 mid-value coincides with the scan centre, so any DC bias the
DAC picks up between manual mode and ``memDrive`` engagement still
lands the piezo at the scan centre rather than off the side.

Scan workflow
-------------
1. Read current piezo positions ``(x0, y0)`` from ``nanox`` / ``nanoy``.
2. Disable DAC modulation. Move ``nanox`` / ``nanoy`` by
   ``(shift_x, shift_y)`` (relative) so the DAC midpoint lands the
   piezo at the scan centre.
3. Load fast (X) snake into ``mem`` and slow (Y) step waveform into
   ``mem2`` (also sets ``driveRAMx_START/_INC/_END``). DAC bit values
   span ``[DAC_CENTRE - W/2, DAC_CENTRE + W/2]``.
4. Pre-set DAC1 to ``x_dac_min`` (scan-start DAC value, on the low
   side of the centred sweep) so the piezo does not jump when
   modulation re-enables.
5. Enable modulation on both axes — piezo = EPICS + DAC offset.
6. Switch DAC1 mux back to ``memDrive`` and trigger the SoftGlue.
7. Wait for ``sg.ram_y_done`` to assert; flush DMA.
8. Cleanup: disable modulation, move EPICS motors back to ``(x0, y0)``.

Position-unit note
------------------
All user-facing scan parameters (``x_min`` / ``x_max`` / etc.) are in
**micrometers**, expressed relative to the **current** ``nanox`` /
``nanoy`` position. The same micron convention is assumed for the
nano-motor EPICS records; adjust ``NANO_EGU_PER_UM`` if your IOC
reports in mm.
"""

import logging

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import numpy as np
from apsbits.core.instrument_init import oregistry
from apstools.devices import AD_prime_plugin2
from bluesky.plan_stubs import mv
from bluesky.plan_stubs import sleep

from ..callbacks.nexus_data_file_writer import nxwriter
from ..utils.run_engine import RE
from ._local_scan_utils import _setup_file_io

logger = logging.getLogger(__name__)
logger.info(__file__)

# DAC offset window: the SoftGlue DAC's 0..5 V output maps to a
# 0..+40 um offset that is summed onto the EPICS-driven base position.
DAC_MIN_UM = 0.0
DAC_MAX_UM = 40.0
DAC_SWING_UM = DAC_MAX_UM - DAC_MIN_UM         # 40 um
DAC_CENTRE_UM = (DAC_MIN_UM + DAC_MAX_UM) / 2  # 20 um (= 2.5 V)
# Maximum |x_min|, |x_max| the user can request. Half the DAC swing,
# since the scan is centred on the DAC midpoint (20 um offset) and the
# DAC sweep needs to fit within the 0..40 um window.
PIEZO_HALF_RANGE_UM = DAC_SWING_UM / 2          # 20 um
# Mechanical full-range limit of the PiezoJena, used to validate that
# the EPICS-side shift doesn't push the piezo past its endstops.
PIEZO_MECHANICAL_RANGE_UM = 40.0
# Conversion factor: how many nanox/nanoy EGU per micrometer. Set to 1.0
# if the EPICS motor record reports in um; 1e-3 if it reports in mm.
NANO_EGU_PER_UM = 1.0


def _resolve(device_or_name, *, required=True, kind=""):
    """Look up a device by name from ``oregistry``, or return it as-is."""
    if device_or_name is None:
        if required:
            raise ValueError(f"{kind} device is required (got None).")
        return None
    if isinstance(device_or_name, str):
        dev = oregistry.find(device_or_name, allow_none=not required)
        if dev is None and required:
            raise ValueError(
                f"{kind} device {device_or_name!r} not in oregistry. "
                "Load it with load_device() first."
            )
        return dev
    return device_or_name


def flyscan(
    detectors: list = None,
    x_min: float = -10,
    x_max: float = 10,
    x_npts: int = 21,
    y_min: float = -10,
    y_max: float = 10,
    y_npts: int = 21,
    acquire_time: float = 50,
    det_dead: float = 10,
    interferometer_per_pixel: int = 5,
    F: float = 0.9,
    *,
    softglue="gsgz_isn",
    piezo="piezo_jena",
    diffractometer="huber_hp",
    socketserver="socketserver",
    savedata="savedata",
):
    """Run a POLAR ISN 2D piezo fly-scan.

    Parameters
    ----------
    detectors : list
        Area detectors that expose ``setup_flyscan_mode``, ``stage``,
        ``unstage`` and an ``hdf1`` plugin.
    x_min, x_max, x_npts : float / int, optional
        **Fast axis** (X piezo) bounds in microns **relative to the
        current** ``nanox`` position ``x0``. Scan physically covers
        ``[x0 + x_min, x0 + x_max]``. Each side is capped at +/- 20
        um (so the scan width never exceeds the 40-um DAC swing).
        ``x_npts`` defaults to 21; the per-point pitch ``dx`` is
        derived as ``(x_max - x_min) / (x_npts - 1)``.
    y_min, y_max, y_npts : float / int, optional
        **Slow axis** (Y piezo) bounds relative to the current
        ``nanoy`` position ``y0`` (same range / cap rules as above).
        ``y_npts`` defaults to 21; pitch ``dy`` derived analogously.
        The slow-axis range is internally extended by one ``dy`` step
        so the last requested line at ``y_max`` is reached —
        ``snake_y``'s firmware end-comparison is strict-less-than.
        ``plan_args`` records the user-supplied values; the extension
        is invisible to downstream metadata.
    acquire_time : float, optional
        Per-image acquire time in milliseconds.
    det_dead : float, optional
        Detector dead time in milliseconds.
    F : float, optional
        Fraction of the fast-axis snake spent in the linear ramp
        (0 < F <= 1).
    interferometer_per_pixel : int, optional
        Interferometry samples streamed per image.
    softglue, piezo, diffractometer : str or Device
        Device name in ``oregistry`` (or a Device instance). ``softglue``
        is the SoftGlueZynq device, ``piezo`` is the PiezoJena
        controller, and ``diffractometer`` is the hklpy2 diffractometer
        that owns ``.nanox`` and ``.nanoy``.
    socketserver, savedata : str or Device, optional
        ISN-style helpers. Skipped silently when missing from
        ``oregistry``.
    """
    logger.debug("Starting flyscan")

    # Accept a single detector or a list/tuple — bluesky stage_decorator
    # and the per-detector loops below all want an iterable.
    if detectors is None:
        detectors = [oregistry.find("eiger")]

    if not isinstance(detectors, (list, tuple)):
        detectors = [detectors]

    # --- Deferred device lookups (no oregistry access at import time) ---

    sg = _resolve(softglue, kind="softglue")
    pz = _resolve(piezo, kind="piezo_jena")
    diff = _resolve(diffractometer, kind="diffractometer")
    # socket_srv = _resolve(socketserver, required=False, kind="socketserver")
    save = _resolve(savedata, required=False, kind="savedata")
    pos_stream = oregistry.find("pos_stream", allow_none=True)

    nanox = diff.nanox  # 4idgSoftX:jena:m1 — fast X piezo
    nanoy = diff.nanoy  # 4idgSoftX:jena:m2 — slow Y piezo

    # --- Resolving number of points and step sizes ---

    if F <= 0 or F > 1:
        raise ValueError("F must be between 0 and 1.")

    if (
        np.abs(x_min) > PIEZO_HALF_RANGE_UM
        or np.abs(x_max) > PIEZO_HALF_RANGE_UM
    ):
        raise ValueError(
            f"Fast-axis range exceeds +/- {PIEZO_HALF_RANGE_UM} um."
        )
    if (
        np.abs(y_min) > PIEZO_HALF_RANGE_UM
        or np.abs(y_max) > PIEZO_HALF_RANGE_UM
    ):
        raise ValueError(
            f"Slow-axis range exceeds +/- {PIEZO_HALF_RANGE_UM} um."
        )

    x_npts_ = abs(int(x_npts))
    dx_ = (x_max - x_min) / (max(x_npts_, 2) - 1)

    y_npts_ = abs(int(y_npts))
    dy_ = (y_max - y_min) / (max(y_npts_, 2) - 1)

    # snake_y's firmware RAM advances the slow axis by 2 lines per cycle
    # (one stored RAM period covers two dy-spaced transitions), so the
    # smallest unit of slow-axis advance is 2 lines. Odd y_npts forces a
    # half-cycle that ends up producing an off-by-one extra line. Reject
    # it cleanly here rather than silently over-triggering by ~x_npts
    # images per scan.
    if y_npts_ % 2 != 0:
        raise ValueError(
            f"y_npts must be even (got {y_npts_}); snake_y's firmware "
            "advances the slow axis by 2 lines per RAM cycle, so odd "
            "y_npts produces an off-by-one extra line. Pass "
            f"y_npts={y_npts_ + 1} to scan that many lines."
        )

    # --- Capturing plan arguments for metadata ---

    plan_args = {
        "detectors": [d.name for d in detectors],
        "x_min": x_min, "x_max": x_max, "dx": dx_, "x_npts": x_npts_,
        "y_min": y_min, "y_max": y_max, "dy": dy_, "y_npts": y_npts_,
        "acquire_time": acquire_time,
        "det_dead": det_dead,
        "F": F,
        "interferometer_per_pixel": interferometer_per_pixel,
    }

    # Predict + validate master and per-detector HDF5 paths, configure each
    # detector's HDF1 plugin, and populate nxwriter with the master /
    # external file paths. Raises FileExistsError BEFORE any PV writes if a
    # target file already exists (Issue #16).
    _master_fullpath, _dets_file_paths, _rel_dets_paths = _setup_file_io(
        detectors + [pos_stream]
    )

    # Top-level start-doc metadata. Mirrors the shape that bluesky's
    # built-in plans (bp_count / bp_scan) produce — in particular, the
    # SPEC writer's ``_rebuild_scan_command`` looks up ``doc["detectors"]``
    # (top level) when it sees ``"detectors"`` as a key in
    # ``doc["plan_args"]``, so the top-level key must be present.
    scan_md = {
        "plan_name": "flyscan",
        "detectors": [d.name for d in detectors],
        "motors": [nanox.name, nanoy.name],
        "hints": {
            "detectors": [],
            "motors": [nanox.name, nanoy.name],
        },
        "plan_args": plan_args,
        "master_file_path": str(_master_fullpath),
        "detectors_file_full_path": _dets_file_paths,
        "detectors_file_relative_path": _rel_dets_paths,
    }

    # --- Cache initial piezo positions in micrometers ---

    x0_um = nanox.user_readback.get() / NANO_EGU_PER_UM
    y0_um = nanoy.user_readback.get() / NANO_EGU_PER_UM

    # --- Pre-compute scan geometry / per-detector args ---

    # Number of points in one fast-axis snake cycle.
    snake_npts = 1000

    # EPICS-side relative shifts. The DAC sweep is centred on its
    # midpoint (DAC_CENTRE_UM = 20 um offset, = 2.5 V), so to put the
    # scan centre at x0 + (x_min+x_max)/2 we shift the EPICS motor by
    # whatever makes ``shift + DAC_CENTRE = scan_centre``.
    shift_x = (x_min + x_max) / 2.0 - DAC_CENTRE_UM
    shift_y = (y_min + y_max) / 2.0 - DAC_CENTRE_UM

    # Final EPICS targets — verify they stay within the piezo's
    # mechanical range to avoid driving past the endstops.
    target_x_um = x0_um + shift_x
    target_y_um = y0_um + shift_y
    if abs(target_x_um) > PIEZO_MECHANICAL_RANGE_UM:
        raise ValueError(
            f"Required nanox shift ({shift_x:+.2f} um) from "
            f"x0={x0_um:.2f} um would land at {target_x_um:+.2f} um, "
            f"outside the +/-{PIEZO_MECHANICAL_RANGE_UM} um piezo range."
        )
    if abs(target_y_um) > PIEZO_MECHANICAL_RANGE_UM:
        raise ValueError(
            f"Required nanoy shift ({shift_y:+.2f} um) from "
            f"y0={y0_um:.2f} um would land at {target_y_um:+.2f} um, "
            f"outside the +/-{PIEZO_MECHANICAL_RANGE_UM} um piezo range."
        )

    # DAC-side scan window, in the DAC's [0, +40] um offset frame.
    # Centred on the DAC midpoint with extent matching the scan width.
    half_x_width = (x_max - x_min) / 2.0
    half_y_width = (y_max - y_min) / 2.0
    x_dac_min = DAC_CENTRE_UM - half_x_width
    x_dac_max = DAC_CENTRE_UM + half_x_width
    y_dac_min = DAC_CENTRE_UM - half_y_width
    y_dac_max = DAC_CENTRE_UM + half_y_width

    x_min_bits = sg.um_to_bits(x_dac_min)
    x_max_bits = sg.um_to_bits(x_dac_max)
    y_min_bits = sg.um_to_bits(y_dac_min)
    y_max_bits = sg.um_to_bits(y_dac_max)

    acquire_period = acquire_time + det_dead
    interferometry_period = acquire_period / interferometer_per_pixel
    # ms -> 10 MHz clock ticks
    interferometer_clock_N = interferometry_period * 1e4
    eiger_clock_N = acquire_period * 1e4
    waveform_period = int(
        2 * acquire_period * 1e-3 * x_npts_ / (F * snake_npts * 1e-7)
    )
    total_scan_points = max(y_npts_, 1) * snake_npts

    # If the total images is smaller than the number of triggers, the detector
    # is crashing!
    total_images = int((max(y_npts_, 1) * x_npts_ * 1.1) / F - 1)
    # total_images = 20000
    # print(total_images, y_npts_, x_npts_)
    images_per_line = int(x_npts_ / F)
    # interferometry_per_line = (
    #     images_per_line * interferometer_per_pixel
    # )

    # Per-bit DAC step (~1.22 nm), unchanged by where the swing sits.
    dy_bits = abs(int(round(dy_ / DAC_SWING_UM * 32767)))

    _threshold_range = (x_dac_max - x_dac_min) * (1 - F)
    _positive_threshold = sg.um_to_bits(x_dac_max - _threshold_range / 2)
    _negative_threshold = sg.um_to_bits(x_dac_min + _threshold_range / 2)

    # --- Per-detector configuration (before staging, so stage_sigs ---
    # --- updated by setup_flyscan_mode take effect when stage runs).
    # The SoftGlue FO -> detector wiring is fixed in hardware on POLAR
    # (e.g. eiger triggered from FO4), so we do not call
    # enable_detector_trigger() here — no software routing is needed.
    # AD_prime_plugin2 is a no-op if the HDF1 plugin has already been
    # primed; it prevents the UnprimedPlugin error from stage() after
    # an IOC restart.

    for detector in detectors:
        # if hasattr(detector, "hdf1"):
        #     AD_prime_plugin2(detector.hdf1)
        detector.setup_flyscan_mode(
            num_images=total_images,
            acq_time=acquire_time * 1e-3,
            hdf_images=images_per_line,
        )
        # detector._flyscan = True

    # --- Inner plan (wrapped with stage + run decorators) ---

    @bpp.stage_decorator(list(detectors))
    @bpp.run_decorator(md=scan_md)
    def _inner():
        eta_min = (
            x_npts_ * y_npts_ * acquire_period / 1000
        ) / 60
        print(
            f"\nStarting flyscan. ETA {np.around(eta_min, 2)} minutes"
        )
        logger.info(
            "Starting a (%s, %s) flyscan. Ctrl+C twice to stop. "
            "Preparing piezos and detectors...",
            x_npts_,
            y_npts_,
        )

        # --- Disable analog modulation so EPICS motor moves take effect

        yield from bps.checkpoint()
        logger.debug("Disabling piezo modulation input.")
        pz.modulation_input_off("x")
        pz.modulation_input_off("y")

        # --- Shift piezos so the DAC swing lands the scan on the    ---
        # --- user-requested range. shift_x / shift_y are computed   ---
        # --- above; this is a relative move from (x0, y0).          ---

        yield from bps.checkpoint()
        print(
            f"[motors] nanox: {x0_um:+.3f} -> {target_x_um:+.3f} um "
            f"(shift {shift_x:+.3f}); "
            f"nanoy: {y0_um:+.3f} -> {target_y_um:+.3f} um "
            f"(shift {shift_y:+.3f})"
        )
        yield from mv(
            nanox, target_x_um * NANO_EGU_PER_UM,
            nanoy, target_y_um * NANO_EGU_PER_UM,
        )

        # --- Stopping softglue and cleaning ---

        yield from bps.checkpoint()
        print("[sg] stop_softglue() / reset() / clear_output_fields()")
        sg.stop_softglue()
        sg.reset()
        # sg.clear_output_fields()

        # --- Defining user clock (ckUser) ---

        yield from bps.checkpoint()
        print(
            f"[sg] div_by_n_3.n <- {eiger_clock_N}  "
            f"(ckeig @ {1 / (acquire_period * 1e-3):0.3e} Hz)"
        )
        sg.div_by_n_3.n.put(eiger_clock_N)

        # --- Defining image clock (ckIM) ---

        yield from bps.checkpoint()
        print(f"[sg] div_by_n_2.n <- {interferometer_clock_N}  (ckIM)")
        sg.div_by_n_2.n.put(interferometer_clock_N)

        # --- Setting up gated trigger ---

        # On POLAR the gate-delay output is hard-wired to the detector
        # trigger via the FO output; no software routing is performed
        # here.
        yield from bps.checkpoint()
        print(
            f"[sg] gate_delay_1: input.signal <- 'ckeig', "
            f"width <- {acquire_time * 1e4}"
        )
        yield from mv(
            sg.gate_delay_1.input.signal, "ckeig",
            sg.gate_delay_1.width, acquire_time * 1e4,
        )

        # --- Defining waveform clock ---

        # One snake cycle of snake_npts points drives the fast (X)
        # axis over one line, while the slow (Y) axis advances by
        # one dy.
        yield from bps.checkpoint()
        # print(
        #     f"[sg] pulse_train: n <- {total_scan_points}, "
        #     f"period <- {waveform_period}, "
        #     f"width <- {int(waveform_period / 2)}"
        # )
        # sg.pulse_train.n.put(total_scan_points)
        # sg.pulse_train.period.put(waveform_period)
        # sg.pulse_train.width.put(int(waveform_period / 2))
        sg.div_by_n_1.n.put(waveform_period)

        # --- Configure fast-axis thresholds (X piezo) ---

        yield from bps.checkpoint()
        print(
            f"[sg] threshold_pos <- {_positive_threshold}, "
            f"threshold_neg <- {_negative_threshold}"
        )
        yield from mv(
            sg.threshold_pos, _positive_threshold,
            sg.threshold_neg, _negative_threshold,
        )

        # --- Load fast-axis (X) snake waveform ---

        yield from bps.checkpoint()
        print(
            f"[sg] snake_x: x_min={x_min_bits}, x_max={x_max_bits}, "
            f"F={F}, npts={snake_npts}"
        )
        yield from sg.snake_x(
            x_min=x_min_bits,
            x_max=x_max_bits,
            F=F,
            npts=snake_npts,
        )

        # --- Load slow-axis (Y) step waveform ---

        yield from bps.checkpoint()
        print(
            f"[sg] snake_y: F={F}, dy={dy_bits}, npts={snake_npts}, "
            f"y_start={y_min_bits}, y_end={y_max_bits}"
        )
        yield from sg.snake_y(
            F=F,
            dy=dy_bits,
            npts=snake_npts,
            y_start=y_min_bits,
            y_end=y_max_bits,
        )

        # --- Pre-set DAC1 to the scan-start DAC value so the piezo ---
        # --- does not jump when modulation enables. move_x_analog   ---
        # --- also switches the DAC1 mux to manual mode; we restore  ---
        # --- memDrive below.                                        ---

        yield from bps.checkpoint()
        print(f"[sg] move_x_analog({x_dac_min} um  [DAC frame])")
        yield from sg.move_x_analog(x_dac_min)

        # --- Enable analog modulation: piezos now follow DAC1/DAC2 ---

        yield from bps.checkpoint()
        logger.debug("Enabling piezo modulation input.")
        yield from sleep(.1)
        pz.modulation_input_on("x")
        yield from sleep(.1)
        pz.modulation_input_on("y")
        yield from sleep(.1)

        # --- Switch DAC1 mux back to memDrive (waveform playback) ---

        print("[sg] enable_waveform() / dac1_write <- 'memDrive'")
        yield from sg.enable_waveform()
        # POLAR signal name (was "funcGenPulse" on 19-ID).
        sg.dac1_write.put("memDrive")

        # --- Update savedata's scan number ---

        yield from bps.checkpoint()
        if save is not None:
            save.next_scan_number.put(RE.md["scan_id"] + 1)

        # --- Preparing socket server ---

        yield from bps.checkpoint()
        if pos_stream is not None:
            # socket_srv.setup_flyscan_mode(
            #     hdf_images=interferometry_per_line
            # )
            # socket_srv.stage()
            # yield from bps.sleep(1)
            # socket_srv.trigger()
            # yield from bps.sleep(1)
            print("[pos_stream] Starting position stream.")
            yield from mv(
                pos_stream.cam.array_counter, 0, pos_stream.hdf1.capture, 1
            )
            yield from mv(pos_stream.cam.acquire, 1)

        #yield from sleep(1)
        # --- Start softglue ---

        print("[sg] prepare()")
        sg.prepare()
        yield from sleep(1)
        logger.info("Takeoff!")
        print("[sg] trigger() — waiting for completion")
        yield from bps.trigger(sg, wait=True)

        # --- Flush DMA so the trailing buffer drains BEFORE the    ---
        # --- detector unstage (triggered by stage_decorator on exit)
        # --- finalises its HDF file.                                 ---

        print("[sg] scal_to_stream_1.flush.signal <- '1!'  (x11, draining DMA)")
        for _ in range(11):
            sg.scal_to_stream_1.flush.signal.put("1!")
            yield from sleep(0.1)

        sg.stop_softglue()
        sg.reset()

        yield from sleep(1)

    def _restore():
        """Non-detector cleanup (runs after stage_decorator unstages)."""
        logger.info(
            "Flyscan done. Restoring softglue and piezo state."
        )

        if pos_stream is not None:
            # Stop position stream
            yield from mv(pos_stream.hdf1.capture, 0)
            yield from mv(pos_stream.cam.acquire, 0)

        # --- Stop softglue and switch DAC1 mux back to manual ---

        print(
            "[sg] stop_softglue() / reset() / clear_output_fields() / "
            "disable_waveform()"
        )
        sg.stop_softglue()
        sg.reset()
        # sg.clear_output_fields()
        yield from sg.disable_waveform()

        # --- Disable modulation: piezos follow EPICS motor records ---

        logger.debug("Disabling piezo modulation input.")
        yield from sleep(.1)
        pz.modulation_input_off("x")
        yield from sleep(.1)
        pz.modulation_input_off("y")
        yield from sleep(.1)

        # --- Restore piezo positions ---

        logger.debug("Returning piezos to original positions.")
        yield from mv(
            nanox, x0_um * NANO_EGU_PER_UM,
            nanoy, y0_um * NANO_EGU_PER_UM,
        )

        # --- Redundant softglue cleanup for reliability ---

        print("[sg] stop_softglue() / reset() / clear_output_fields()  (redundant)")
        sg.stop_softglue()
        sg.reset()
        # sg.clear_output_fields()

    @bpp.subs_decorator(nxwriter.receiver)
    def _flyscan_with_nx():
        yield from bpp.finalize_wrapper(_inner(), _restore())
        yield from nxwriter.wait_writer_plan_stub()

    yield from _flyscan_with_nx()
