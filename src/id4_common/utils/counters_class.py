"""
Detector and monitor selection class for dual-scaler beamline configurations.
"""

from collections.abc import Iterable
from logging import getLogger

from apsbits.core.instrument_init import oregistry
from ophydregistry import ComponentNotFound
from pandas import DataFrame

logger = getLogger(__name__)
logger.bsdev(__file__)

__all__ = ["counters"]

IDEAL_ORDER = [
    "scaler1",
    "scaler2",
    "eiger",
    "vortex",
    "flagcam_hhl",
    "flagcam_mono",
    "flagcam_toro",
]


class CountersClass:
    """
    Holds monitor and detectors for scans. Our scans read these by default.

    Attributes
    ----------
    detectors : list of devices
        Detectors that will be triggered and read.
    extra_devices : list of devices
        Extra devices that will be read but not plotted during scan.
    monitor : str
        Human-readable label of the channel used as monitor.
    monitor_field : str
        Ophyd field name of the monitor channel (use for dichro/BEC hints).
    is_scaler_monitor : bool
        True when the monitor is Time or a scaler channel.
    """

    def __init__(self, order=IDEAL_ORDER):
        super().__init__()
        self._dets = []
        # Selections stored as (device_name, channel_label) tuples so they
        # remain valid even when the device list changes and DataFrame row
        # indices shift (Issue #10).
        self._selected_dets: list = []  # list[tuple[str, str]]
        self._selected_mon: tuple = ("scalers", "Time")  # (device_name, label)
        self._selected_extra_read: list = []  # list[tuple[str, str]] (#17)
        self._mon = "Time"
        self._extra_devices = []
        self._order = order
        self.use_scalers: bool = True

    def __repr__(self):
        read_names = [
            item.name for item in (self.detectors + self.extra_devices)
        ]
        extra_read_labels = [c for _, c in self._selected_extra_read]
        return (
            "Counters settings\n"
            " Monitor:\n"
            f"  Channel = '{self._mon}'\n"
            " Scalers:\n"
            f"  use_scalers = {self.use_scalers}\n"
            " Detectors:\n"
            f"  Read devices = {read_names}\n"
            f"  Plot components = {self.plot_names}\n"
            " Extra read:\n"
            f"  Channels = {extra_read_labels}"
        )

    def __str__(self):
        return self.__repr__()

    def __call__(self):
        """Launch interactive plotselect."""
        self.plotselect()

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------

    @property
    def plot_names(self):
        """Ophyd field names of currently hinted (plotted) channels."""
        names = []
        for item in self.detectors:
            names.extend(item.hints["fields"])
        return names

    @property
    def _available_scalers(self):
        return oregistry.findall("scaler", allow_none=True)

    @property
    def detectors(self):
        return self._dets

    @property
    def selected_plot_detectors(self):
        """Device names that currently have at least one hinted channel."""
        return [
            det.name for det in self.detectors if len(det.hints["fields"]) > 0
        ]

    @property
    def monitor(self):
        """Human-readable label of the monitor channel."""
        return self._mon

    @property
    def is_scaler_monitor(self):
        """True when the monitor is Time or a scaler channel."""
        dev_name = self._selected_mon[0]
        scaler_names = [s.name for s in self._available_scalers]
        return dev_name in (["scalers"] + scaler_names)

    @property
    def monitor_field(self):
        """Ophyd field name of the monitor channel.

        For scalers the label equals the field name (after match_names).
        For non-scaler devices the field name is looked up via
        device.field_for_label().
        """
        dev_name, label = self._selected_mon
        if self.is_scaler_monitor:
            return label
        dev = oregistry.find(dev_name, allow_none=True)
        if dev is not None and hasattr(dev, "field_for_label"):
            return dev.field_for_label(label)
        return label  # fallback

    @property
    def monitor_detector(self):
        """Return the scaler device(s) for the monitor channel.

        Returns the list of available scalers when monitor is Time, the
        specific scaler device when monitor is a scaler channel, or None
        when the monitor is a non-scaler device (use monitor_field for
        the event-document key in that case).
        """
        if self._mon == "Time":
            return self._available_scalers
        if self.is_scaler_monitor:
            name = self._selected_mon[0]
            return oregistry.find(name)
        return None

    @property
    def extra_devices(self):
        return self._extra_devices

    @extra_devices.setter
    def extra_devices(self, value):
        try:
            value = list(value)
        except TypeError:
            value = [value]

        self._extra_devices = []
        for item in value:
            if isinstance(item, str):
                raise ValueError(
                    "Input has to be a device instance, not a "
                    f"device name, but {item} was entered."
                )
            if item not in self.detectors:
                self._extra_devices.append(item)

    @property
    def _available_detectors(self):
        try:
            _dets = oregistry.findall("detector")
        except ComponentNotFound:
            logger.warning("WARNING: no detectors were found by oregistry.")
            _dets = []

        dets = []
        for name in self._order:
            dev = oregistry.find(name, allow_none=True)
            if dev in _dets:
                _dets.remove(dev)
            if dev is not None:
                dets.append(dev)

        return dets + _dets

    # ------------------------------------------------------------------
    # Selection table helpers
    # ------------------------------------------------------------------

    def _sel_marker(self, dev_name, chan):
        """Return the selection marker string for a (device_name, label) pair."""
        key = (dev_name, chan)
        if key in self._selected_dets:
            return "Plot"
        if key == self._selected_mon:
            return "Monitor"
        if key in self._selected_extra_read:
            return "Read"
        return ""

    @property
    def detectors_plot_options(self):
        """DataFrame with columns detectors / channels / selection."""
        table = dict(detectors=[], channels=[], selection=[])

        # Row 0: virtual "Time" entry representing all scalers' time channel.
        if len(self._available_scalers) > 0:
            table["detectors"].append("scalers")
            table["channels"].append("Time")
            table["selection"].append(self._sel_marker("scalers", "Time"))

        for det in self._available_detectors:
            _options = getattr(det, "plot_options", [])
            # Skip the first entry ("Time") for scalers — handled above.
            if det in self._available_scalers:
                _options = _options[1:]
            for opt in _options:
                table["detectors"].append(det.name)
                table["channels"].append(opt)
                table["selection"].append(self._sel_marker(det.name, opt))

        return DataFrame(table)

    def _tuples_to_indices(self, tuples, options):
        """Convert stored (device, label) tuples to current DataFrame indices."""
        indices = []
        for dev_name, chan in tuples:
            match = options[
                (options["detectors"] == dev_name)
                & (options["channels"] == chan)
            ].index.tolist()
            indices.extend(match)
        return indices

    def _tuple_to_index(self, tup, options):
        """Convert a single stored (device, label) tuple to its current index."""
        dev_name, chan = tup
        match = options[
            (options["detectors"] == dev_name) & (options["channels"] == chan)
        ].index.tolist()
        return match[0] if match else 0

    # ------------------------------------------------------------------
    # Channel selection
    # ------------------------------------------------------------------

    def select_plot_channels(self, selection):
        """Configure device hints based on selected row indices."""
        plot_options = self.detectors_plot_options
        selection = list(selection)

        # Index 0 is the virtual "Time" row: expand it to each scaler's
        # chan01 so groupby can work normally.
        if 0 in selection:
            selection.remove(0)
            for sc in self._available_scalers:
                selection.append(len(plot_options))
                plot_options.loc[len(plot_options)] = [
                    sc.name,
                    sc.channels.chan01.chname.get(),
                    "",  # selection column (3rd) required for 3-column DF
                ]

        groups = plot_options.iloc[list(selection)].groupby("detectors")

        dets = []
        for name, group in groups:
            det = oregistry.find(name)
            det.select_plot(list(group["channels"].values))
            dets.append(det)

        # Include all scalers in _dets so timing / gating works,
        # unless use_scalers is False (scalers only added if explicitly selected).
        if self.use_scalers:
            for sc in self._available_scalers:
                if sc not in dets:
                    dets.append(sc)
                    sc.select_plot_channels([""])

        self._dets = dets

    def _apply_extra_read(self, extra_read_indices, options):
        """Apply extra-read channel selections to devices (Issue #17)."""
        if not extra_read_indices:
            return
        extra = options.iloc[list(extra_read_indices)]
        for name, group in extra.groupby("detectors"):
            if name == "scalers":
                continue
            det = oregistry.find(name, allow_none=True)
            if det is not None and hasattr(det, "select_read"):
                det.select_read(list(group["channels"].values))
                if det not in self._dets:
                    self._dets.append(det)

    # ------------------------------------------------------------------
    # Interactive selection
    # ------------------------------------------------------------------

    def plotselect(self, dets=None, mon=None, extra_read=None):
        """
        Select plotting detectors, monitor, and optional extra-read channels.

        Parameters
        ----------
        dets : int or list of int, optional
            Row index/indices into detectors_plot_options for plot channels.
        mon : int, optional
            Row index of the monitor channel.
        extra_read : list of int, optional
            Row indices of channels to read but not plot (Issue #17).
        """
        _valid_dets = False
        _valid_mon = False
        _valid_extra = False

        options = self.detectors_plot_options
        n = options.shape[0]

        # Validate dets
        if dets is not None:
            if not isinstance(dets, Iterable):
                dets = [dets]
            dets = list(dets)
            if all([isinstance(i, int) and 0 <= i < n for i in dets]):
                _valid_dets = True
            else:
                logger.warning(f"The detectors option {dets} is invalid!")

        # Validate mon
        if mon is not None:
            if isinstance(mon, int) and 0 <= mon < n:
                _valid_mon = True
            else:
                logger.warning(f"The monitor option {mon} is invalid!")

        # Validate extra_read
        if extra_read is not None:
            if not isinstance(extra_read, Iterable):
                extra_read = [extra_read]
            extra_read = list(extra_read)
            if all([isinstance(i, int) and 0 <= i < n for i in extra_read]):
                _valid_extra = True
            else:
                logger.warning(
                    f"The extra_read option {extra_read} is invalid!"
                )

        interactive = not (_valid_dets and _valid_mon)

        if interactive:
            print("Options:")
            print(options)
            print("")

        # --- Detector selection ---
        if not _valid_dets:
            current_defaults = self._tuples_to_indices(
                self._selected_dets, options
            )
            while True:
                dets = (
                    input(
                        "Enter the indexes of plotting channels "
                        f"{current_defaults}: "
                    )
                    or current_defaults
                )

                if len(dets) == 0:
                    print("A value must be entered.")
                    continue

                try:
                    if isinstance(dets, str):
                        dets = [int(i) for i in dets.split()]
                    else:
                        dets = [int(i) for i in dets]
                except ValueError:
                    print("Please enter the index numbers only.")
                    continue

                if not all([i in options.index.values for i in dets]):
                    print("The index values must be in the table.")
                    continue

                break

        self.select_plot_channels(dets)
        self._selected_dets = [
            (options.loc[i]["detectors"], options.loc[i]["channels"])
            for i in dets
        ]

        # --- Monitor selection ---
        if not _valid_mon:
            current_mon = self._tuple_to_index(self._selected_mon, options)
            while True:
                mon = (
                    input(
                        f"Enter index number of monitor channel [{current_mon}]: "
                    )
                    or current_mon
                )

                try:
                    mon = int(mon)
                except ValueError:
                    print("Please enter the index number only.")
                    continue

                if mon in dets:
                    print(
                        f"Monitor {mon} is invalid because it is also "
                        "selected as a detector."
                    )
                    continue

                break

        self._selected_mon = (
            options.loc[mon]["detectors"],
            options.loc[mon]["channels"],
        )
        self._mon = options.loc[mon]["channels"]

        # --- Extra read channels (Issue #17) ---
        if interactive and not _valid_extra:
            current_read = self._tuples_to_indices(
                self._selected_extra_read, options
            )
            extra_str = input(
                "Enter indexes of extra read channels "
                f"(optional, Enter to keep {current_read}): "
            )
            if extra_str.strip():
                try:
                    extra_read = [int(i) for i in extra_str.split()]
                    # Remove overlap with plot channels and monitor.
                    extra_read = [
                        i for i in extra_read if i not in dets and i != mon
                    ]
                    if all([i in options.index.values for i in extra_read]):
                        _valid_extra = True
                    else:
                        print("Invalid extra read indices, skipping.")
                        extra_read = self._tuples_to_indices(
                            self._selected_extra_read, options
                        )
                        _valid_extra = True
                except ValueError:
                    print("Invalid extra read input, skipping.")
                    extra_read = self._tuples_to_indices(
                        self._selected_extra_read, options
                    )
                    _valid_extra = True
            else:
                # Keep current stored extra read.
                extra_read = self._tuples_to_indices(
                    self._selected_extra_read, options
                )
                _valid_extra = True

        if _valid_extra and extra_read:
            self._selected_extra_read = [
                (options.loc[i]["detectors"], options.loc[i]["channels"])
                for i in extra_read
                if i in options.index.values
            ]

        # Always apply stored extra read (re-apply after select_plot_channels).
        stored_extra = self._tuples_to_indices(
            self._selected_extra_read, options
        )
        self._apply_extra_read(stored_extra, options)

        print()
        print(self)


counters = CountersClass()
