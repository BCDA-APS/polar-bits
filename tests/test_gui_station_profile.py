"""Station-awareness of the GUI and MCP layer.

Two things are being protected here.

The first is **4IDG**, which has a working GUI that this must not disturb.  The
three code strings the kernel is bootstrapped with are pinned byte-for-byte
against fixtures captured before the station profile existed; if any of them
moves, the session those helpers serve has changed.

The second is the bug class the profile exists to fix: station values were
materialised into module constants *at import*, which is before ``app.main``
parses ``--station``.  A test that only ever runs one station cannot see that,
so the tests below switch ``ID4_STATION`` **inside a single process** and
require the answers to follow.

``gui/config.py`` imports nothing outside the standard library, so most of this
needs no stubs, no EPICS and no Qt.  The few widget tests skip themselves where
``qtpy`` is absent -- it is only in the ``gui`` extra.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from id4_common.gui import config

#: Captured from ``ID4_STATION=id4_g`` before the refactor.
DATA = Path(__file__).parent / "data"

STATIONS_WITHOUT_HKL = ["id4_b", "id4_h"]


@pytest.fixture
def at_station(monkeypatch):
    """Return a callable that points this process at a station."""

    def _set(name):
        monkeypatch.setenv("ID4_STATION", name)
        return config.profile()

    return _set


# --- the 4IDG regression guard ---------------------------------------------


def _kernel_code_strings():
    """The three code strings, keyed by the fixture that pins each.

    ``motion`` stays a constant on purpose: unlike the other two it carries no
    station content, so there is nothing for it to resolve late.

    Imported inside the function so a missing ``qtpy`` cannot stop collection:
    none of these three modules needs Qt, but ``mcp_server`` reaches into
    ``gui.config`` and the import graph is easier to reason about kept local.
    """
    from id4_common.gui.hkl_bridge import hkl_helpers_code
    from id4_common.mcp_server.bridge import mcp_helpers_code
    from id4_common.mcp_server.motion import MOTION_HELPERS_CODE

    return {
        "hkl_helpers_id4_g.py.txt": hkl_helpers_code(),
        "mcp_helpers_id4_g.py.txt": mcp_helpers_code(),
        "motion_helpers_id4_g.py.txt": MOTION_HELPERS_CODE,
    }


@pytest.mark.parametrize(
    "fixture",
    [
        "hkl_helpers_id4_g.py.txt",
        "mcp_helpers_id4_g.py.txt",
        "motion_helpers_id4_g.py.txt",
    ],
)
def test_id4_g_kernel_code_is_byte_identical(at_station, fixture):
    """4IDG's bootstrap must be exactly what it was before the refactor.

    These strings are executed in the live session, so a difference here is a
    difference in the beamline's running code -- not a cosmetic one.
    """
    at_station("id4_g")
    assert _kernel_code_strings()[fixture] == (DATA / fixture).read_text()


def test_device_literal_is_deterministic():
    """The emitted device set must not depend on the string hash seed.

    ``repr(set(...))`` does, which made the kernel source differ between two
    launches of the same station -- invisible in use, and fatal to any attempt
    to pin it.
    """
    from id4_common.mcp_server.bridge import _set_literal

    assert _set_literal({"huber_hp", "huber_euler"}) == (
        "{'huber_euler', 'huber_hp'}"
    )
    assert _set_literal(frozenset()) == "set()"


# --- the profile table ------------------------------------------------------


def test_id4_g_has_both_machines(at_station):
    """4IDG is the one station with diffractometers and flyscans."""
    profile = at_station("id4_g")
    assert profile.display == "4IDG"
    assert profile.has_diffractometer
    assert profile.diffractometers == ("huber_euler", "huber_hp")
    assert profile.mcp_allowed_devices == {"huber_euler", "huber_hp"}
    assert profile.mcp_default_device == "huber_euler"
    assert profile.has_flyscan
    assert profile.unsupported_reason is None


@pytest.mark.parametrize("station", STATIONS_WITHOUT_HKL)
def test_target_stations_declare_no_diffractometer(at_station, station):
    """4IDB and 4IDH run, but without hkl or flyscan."""
    profile = at_station(station)
    assert profile.display == station.replace("id4_", "4ID").upper()
    assert not profile.has_diffractometer
    assert profile.diffractometers == ()
    assert profile.mcp_allowed_devices == frozenset()
    assert profile.mcp_default_device is None
    assert not profile.has_flyscan
    # These two are deliverable: nothing refuses to launch them.
    assert profile.unsupported_reason is None


def test_mcp_allow_list_cannot_exceed_the_declared_machines(at_station):
    """The allow-list is derived, so a station cannot allow what it lacks."""
    for station in ("id4_b", "id4_g", "id4_h", "id4_raman"):
        profile = at_station(station)
        assert profile.mcp_allowed_devices == frozenset(profile.diffractometers)


def test_raman_is_declared_unsupported(at_station):
    """id4_raman is known, and known not to start."""
    profile = at_station("id4_raman")
    assert profile.unsupported_reason
    assert "polartools_hklpy_imports" in profile.unsupported_reason


def test_unknown_station_degrades_and_warns(at_station, caplog):
    """An unrecognised name offers nothing rather than raising.

    The MCP server reads ``ID4_STATION`` from an environment it does not
    control, so a station it cannot place must still answer.
    """
    with caplog.at_level(logging.WARNING, logger="id4_common.gui.config"):
        profile = at_station("id4_nowhere")
    assert not profile.has_diffractometer
    assert not profile.has_flyscan
    assert profile.unsupported_reason
    assert "id4_nowhere" in caplog.text


# --- the bug class: import-time freezing ------------------------------------


def test_kernel_code_follows_the_station_within_one_process(at_station):
    """The whole point: no station value may be frozen at import.

    ``app.main`` sets ``ID4_STATION`` long after ``gui.kernel`` has pulled
    these modules in, so anything materialised at import belongs to whichever
    station happened to be the default.
    """
    from id4_common.gui.hkl_bridge import hkl_helpers_code
    from id4_common.mcp_server.bridge import default_device
    from id4_common.mcp_server.bridge import mcp_helpers_code

    at_station("id4_g")
    g_hkl, g_mcp, g_default = (
        hkl_helpers_code(),
        mcp_helpers_code(),
        default_device(),
    )

    at_station("id4_b")
    b_hkl, b_mcp, b_default = (
        hkl_helpers_code(),
        mcp_helpers_code(),
        default_device(),
    )

    assert g_hkl != b_hkl
    assert g_mcp != b_mcp
    assert g_default == "huber_euler"
    assert b_default is None
    assert "_GUI_HKL_PSI = {}" in b_hkl
    assert "_GUI_MCP_DEVICES = set()" in b_mcp


def test_qsettings_scope_is_per_station_but_id4_g_keeps_its_key(at_station):
    """4IDG must not lose its saved font, log path and macro folder."""
    at_station("id4_g")
    assert config.qsettings_app() == "polar-gui"
    at_station("id4_b")
    assert config.qsettings_app() == "polar-gui-id4_b"
    at_station("id4_h")
    assert config.qsettings_app() == "polar-gui-id4_h"


# --- the MCP tool set -------------------------------------------------------


def test_instructions_drop_the_tutorial_where_there_is_no_machine(at_station):
    """Two-thirds of the text describes tools a 4IDB client will not have."""
    from id4_common.mcp_server import server

    at_station("id4_g")
    with_hkl = server.instructions()
    at_station("id4_b")
    without = server.instructions()

    assert "Orientation setup, in this order" in with_hkl
    assert "hkl_get_state" in with_hkl
    assert "Orientation setup, in this order" not in without
    assert "hkl_get_state" not in without
    assert "4IDB, which has **no diffractometer**" in without
    # The half that is true everywhere stays.
    assert "You cannot change anything by yourself" in without
    assert "move_hkl" not in without


def test_diffractometer_tools_are_declared_only_where_there_is_one(at_station):
    """A client should not be shown 18 tools that cannot work."""
    pytest.importorskip("mcp", reason="the MCP SDK is an optional extra")
    import asyncio

    from id4_common.mcp_server import server

    def tool_names(station):
        at_station(station)
        mcp, _ = server.build()
        return {tool.name for tool in asyncio.run(mcp.list_tools())}

    at_g = tool_names("id4_g")
    at_b = tool_names("id4_b")

    hkl_tools = {name for name in at_g if name.startswith("hkl_")} | {
        "move_hkl"
    }
    assert len(hkl_tools) == 18
    assert hkl_tools <= at_g
    assert not (hkl_tools & at_b)
    # Everything that is not diffractometer-specific survives.
    assert at_g - hkl_tools == at_b


def test_session_device_default_follows_the_station(at_station):
    """``HklSession(device=...)`` defaulted to a module constant."""
    from id4_common.mcp_server.session import HklSession

    at_station("id4_g")
    assert HklSession().device == "huber_euler"
    at_station("id4_b")
    assert HklSession().device is None


# The matching guard outside the GUI -- ``_configure_fixq`` with no
# diffractometer -- is tested in ``test_list_scans.py``, which already has the
# fixture that loads ``_local_scan_utils`` without its package ``__init__``.


# --- the widgets ------------------------------------------------------------


@pytest.fixture
def qt_app(monkeypatch):
    """A headless QApplication, or a skip where Qt is not installed."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("qtpy", reason="Qt is in the gui extra only")
    pytest.importorskip("qtconsole", reason="Qt is in the gui extra only")
    from qtpy.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_every_station_offers_the_same_tabs(qt_app, at_station):
    """Never omit a tab: the layout is learned once, and it holds.

    Asked of the profile rather than of built widgets, so it covers 4IDG too
    -- see the next test for why 4IDG's tabs are not constructed here.
    """
    from id4_common.gui.app import TABS

    def blocked(station):
        profile = at_station(station)
        return {cls.title for cls in TABS if cls.unavailable_reason(profile)}

    assert blocked("id4_g") == set()
    assert blocked("id4_b") == {"HKL", "Flyscan plot"}
    assert blocked("id4_h") == {"HKL", "Flyscan plot"}


def test_a_4idb_window_gets_ten_tabs_two_of_them_placeholders(
    qt_app, at_station
):
    """The same gate, exercised through the real construction path.

    Only at 4IDB: 4IDG's HKL tab embeds the 3D diffractometer view, which
    wants a real display and aborts the interpreter under ``offscreen``.  The
    4IDG build is a manual check.
    """
    from id4_common.gui.app import TABS
    from id4_common.gui.app import MainWindow
    from id4_common.gui.tabs.base import UnavailableTab

    profile = at_station("id4_b")
    built = [MainWindow._build_tab(cls, profile) for cls in TABS]

    assert len(built) == len(TABS)
    assert {tab.title for tab in built if isinstance(tab, UnavailableTab)} == {
        "HKL",
        "Flyscan plot",
    }


def test_a_placeholder_names_the_station_and_the_reason(qt_app, at_station):
    """An unexplained grey tab is the bug being fixed, not the fix."""
    from id4_common.gui.tabs.flyscanplot import FlyscanPlotTab
    from id4_common.gui.tabs.hkl import HklTab

    profile = at_station("id4_h")
    for tab_class in (HklTab, FlyscanPlotTab):
        reason = tab_class.unavailable_reason(profile)
        assert reason
        assert "4IDH" in reason

    assert HklTab.unavailable_reason(at_station("id4_g")) is None
    assert FlyscanPlotTab.unavailable_reason(at_station("id4_g")) is None


def test_a_tab_that_raises_does_not_take_the_window_down(qt_app, at_station):
    """One broken tab was enough to stop the GUI starting."""
    from id4_common.gui.app import MainWindow
    from id4_common.gui.tabs.base import BaseTab
    from id4_common.gui.tabs.base import UnavailableTab

    class ExplodingTab(BaseTab):
        """A tab whose constructor raises."""

        title = "Boom"

        def __init__(self, parent=None):
            """Fail, as a tab with a broken dependency would."""
            raise RuntimeError("no such device")

    tab = MainWindow._build_tab(ExplodingTab, at_station("id4_b"))
    assert isinstance(tab, UnavailableTab)
    assert tab.failed
    assert "no such device" in tab.reason


def test_hkl_plans_are_listed_but_disabled(qt_app, at_station):
    """Listed, so someone who has used them at 4IDG gets an answer."""
    from id4_common.gui.scancode import HKL_PLANS
    from id4_common.gui.scancode import PLANS
    from id4_common.gui.tabs.scan import ScanTab

    def plan_rows(station):
        at_station(station)
        tab = ScanTab()
        model = tab._plan_combo.model()
        rows = {
            model.item(i).text(): model.item(i).isEnabled()
            for i in range(model.rowCount())
        }
        return tab, rows

    tab, rows = plan_rows("id4_b")
    assert set(rows) == set(PLANS)
    assert {name for name, on in rows.items() if not on} == set(HKL_PLANS)

    tab._plan_combo.setCurrentText("ascan")
    tab._on_plan_changed()
    assert not tab._fixq.isVisibleTo(tab)

    tab, rows = plan_rows("id4_g")
    assert all(rows.values())
    tab._plan_combo.setCurrentText("ascan")
    tab._on_plan_changed()
    assert tab._fixq.isVisibleTo(tab)
