"""Flyscan live viewer, vendored from the beamline analysis folder.

These four modules were copied on 2026-09-08 from

    /gdata/dm/4ID/2026-3/Kb_comm_26-3/analysis/

    flyscan_live_gui.py   Sep  4 23:38   LiveMainWindow, the live viewer
    flyscan_gui.py        Sep  4 23:38   EigerTab, VortexTab, ProcessWorker
    live_flyscan.py       Sep  4 19:08   LiveScanReader, find_latest_scan
    process_flyscan.py    Sep  4 23:28   pure analysis, no Qt

so the Flyscan plot tab does not depend on a per-experiment directory being
present and on ``sys.path``.  That analysis copy is still edited there, so the
two will drift; a re-sync is a plain diff against the paths above.

The copies differ from their originals in three deliberate ways, all so they
sit inside a package and match the host GUI's conventions:

* the cross-module imports are relative (``from .flyscan_gui import ...``);
* Qt is imported through ``qtpy`` rather than ``PyQt5`` directly, and
  matplotlib through the binding-agnostic ``backend_qtagg``, because
  :mod:`id4_common.gui` deliberately leaves the binding unpinned;
* :meth:`~.flyscan_live_gui.LiveMainWindow.set_folder` was added, so a host can
  supply the sample folder without touching private state;
* the preview/map splitter in ``EigerTab`` and ``VortexTab`` is horizontal, so
  the two plots sit side by side rather than stacked -- the tab is wider than
  it is tall inside the station GUI;
* those plots start square and equally wide, via the ``_SquareStart`` mixin the
  two tabs gained, and give both up at the first resize or splitter drag, and
  the maps use an ``auto`` data aspect rather than ``equal`` so a lopsided
  scan range fills the square box instead of drawing a sliver across it;
* the cursor readout sits on its own full-width line under each toolbar, via
  the ``_Toolbar`` subclass, instead of being clipped inside the button row;
* the live viewer's control bar is two rows and its folder label elides
  (``_ElidingLabel``), which takes the window's minimum width from 1862 px
  down to 857 -- on one row a long data path made the viewer unshrinkable;
* Eiger frames are shown rotated one quarter turn counter-clockwise
  (``EIGER_ROT90_CCW``).  Every Eiger coordinate the user sees or picks is in
  that rotated frame, and ``raw_slice_for_roi`` / ``raw_point_to_display`` map
  it back for the two summing paths and the beam centre, so the ROI box always
  covers exactly the pixels being summed.  ``DEFAULT_EIGER_ROI`` moved with it
  and was re-centred on real data;
* every in-flight worker thread is held in a set (``_track_worker``) rather
  than one slot per kind, and ``closeEvent`` waits for them.  A scan with both
  an Eiger and a Vortex stream starts two previews at once, and the single
  slot dropped the first thread's only reference mid-run -- Qt aborted the
  process;
* both ROIs are saved to and restored from the dichro viewer's
  ``flyscan_gui_dichro.config.json`` in the experiment's analysis folder, so
  the two viewers start from the same ROI.  Writes are read-modify-write, and
  the Eiger ROI is converted to that file's raw coordinates on the way out --
  the dichro viewer does not rotate its frames.

``flyscan_live_gui`` keeps its ``main()``, so the viewer still runs standalone::

    python -m id4_common.gui.flyscan.flyscan_live_gui --folder <sample folder>
"""
