"""Mixin classes for the detector channel-selection API used by CountersClass."""

from abc import ABC
from abc import abstractmethod

__all__ = ["CountersMixin", "ROICountersMixin"]


class CountersMixin(ABC):
    """API contract for detectors used with CountersClass.plotselect().

    Concrete implementations must provide plot_options, label_option_map,
    select_plot, and field_for_label. select_read defaults to a no-op, which
    is correct for detectors where all channels are always read (eiger, vimba).

    For preset_monitor, set the class attribute _preset_monitor_attr to a
    dotted attribute path string (e.g. "cam.acquire_time"). Devices that
    cannot use this pattern (e.g. LocalScalerCH which has preset_monitor as
    an ophyd Component) may override preset_monitor directly in the class body.
    """

    _preset_monitor_attr: str | None = None

    @property
    def preset_monitor(self):
        """Return the ophyd signal used to control scan count time.

        Resolved by walking the dotted path in _preset_monitor_attr. Set
        that class attribute in subclasses instead of overriding this property.
        """
        if self._preset_monitor_attr is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define _preset_monitor_attr "
                "or override preset_monitor."
            )
        obj = self
        for part in self._preset_monitor_attr.split("."):
            obj = getattr(obj, part)
        return obj

    @property
    @abstractmethod
    def plot_options(self) -> list:
        """Return human-readable channel labels available for plot selection."""

    @property
    @abstractmethod
    def label_option_map(self) -> dict:
        """Return mapping from human-readable label to internal index."""

    @abstractmethod
    def select_plot(self, channels: list) -> None:
        """Configure Kind.hinted for the given channel labels."""

    @abstractmethod
    def field_for_label(self, label: str) -> str:
        """Return the ophyd field name for a plot-option label."""

    def select_read(self, channels: list) -> None:  # noqa: B027
        """Mark channels as Kind.normal without plotting.

        No-op by default. Override in devices where channels can be omitted
        (i.e. where Kind.omitted is a valid resting state).
        """


class ROICountersMixin(CountersMixin):
    """Shared plot-selection implementation for ROI-based MCA detectors.

    Provides concrete implementations of plot_options, select_plot,
    field_for_label, select_read, and the read_rois getter. Subclasses
    must still provide:

    - ``label_option_map`` — maps label strings to ROI index integers
    - ``select_roi(rois)`` — device-specific Kind manipulation across all ROIs
    - ``read_rois`` setter if per-pixel stats kinds must also be updated

    The ``_read_rois`` class attribute sets the default readable ROI index.
    """

    _read_rois: list = [1]

    @property
    def read_rois(self) -> list:
        """ROI indices currently included in reads (Kind.normal or hinted)."""
        return self._read_rois

    @property
    @abstractmethod
    def label_option_map(self) -> dict:
        """Map label strings to ROI index integers."""

    @abstractmethod
    def select_roi(self, rois: list) -> None:
        """Set Kind.hinted/normal/omitted for ROIs; implementation is per-device."""

    @property
    def plot_options(self) -> list:
        """Return all available ROI label strings for plot channel selection."""
        return list(self.label_option_map.keys())

    def select_plot(self, channels: list) -> None:
        """Select which ROI channels are plotted by label name."""
        chans = [self.label_option_map[c] for c in channels]
        self.select_roi(chans)

    def field_for_label(self, label: str) -> str:
        """Return the ophyd field name for a plot-option label."""
        roi_index = self.label_option_map[label]
        return getattr(self.total, f"roi{roi_index}").name

    def select_read(self, channels: list) -> None:
        """Mark channels as Kind.normal without plotting.

        Must be called after select_plot because select_roi resets ROI kinds.
        """
        for channel in channels:
            roi_index = self.label_option_map[channel]
            getattr(self.total, f"roi{roi_index}").kind = "normal"
            if roi_index not in self._read_rois:
                self._read_rois.append(roi_index)
