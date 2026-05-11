id4_common.devices.counters_mixin
=================================

.. py:module:: id4_common.devices.counters_mixin

.. autoapi-nested-parse::

   Mixin classes for the detector channel-selection API used by CountersClass.





Module Contents
---------------

.. py:class:: CountersMixin

   Bases: :py:obj:`abc.ABC`


   API contract for detectors used with CountersClass.plotselect().

   Concrete implementations must provide plot_options, label_option_map,
   select_plot, and field_for_label. select_read defaults to a no-op, which
   is correct for detectors where all channels are always read (eiger, vimba).

   For preset_monitor, set the class attribute _preset_monitor_attr to a
   dotted attribute path string (e.g. "cam.acquire_time"). Devices that
   cannot use this pattern (e.g. LocalScalerCH which has preset_monitor as
   an ophyd Component) may override preset_monitor directly in the class body.


   .. py:property:: preset_monitor

      Return the ophyd signal used to control scan count time.

      Resolved by walking the dotted path in _preset_monitor_attr. Set
      that class attribute in subclasses instead of overriding this property.


   .. py:property:: plot_options
      :type: list

      :abstractmethod:


      Return human-readable channel labels available for plot selection.


   .. py:property:: label_option_map
      :type: dict

      :abstractmethod:


      Return mapping from human-readable label to internal index.


   .. py:method:: select_plot(channels: list) -> None
      :abstractmethod:


      Configure Kind.hinted for the given channel labels.



   .. py:method:: field_for_label(label: str) -> str
      :abstractmethod:


      Return the ophyd field name for a plot-option label.



   .. py:method:: predict_save_path(base_path, name_template, file_number)

      Return (full_path, relative_path) without any EPICS I/O.

      Mirrors setup_images + make_write_read_paths for detectors that store
      their format string as hdf1_name_format or hdf1_file_format. Returns
      (None, None) when neither attribute is found.



   .. py:method:: select_read(channels: list) -> None

      Mark channels as Kind.normal without plotting.

      No-op by default. Override in devices where channels can be omitted
      (i.e. where Kind.omitted is a valid resting state).



.. py:class:: ROICountersMixin

   Bases: :py:obj:`CountersMixin`


   Shared plot-selection implementation for ROI-based MCA detectors.

   Provides concrete implementations of plot_options, select_plot,
   field_for_label, select_read, and the read_rois getter. Subclasses
   must still provide:

   - ``label_option_map`` — maps label strings to ROI index integers
   - ``select_roi(rois)`` — device-specific Kind manipulation across all ROIs
   - ``read_rois`` setter if per-pixel stats kinds must also be updated

   The ``_read_rois`` class attribute sets the default readable ROI index.


   .. py:property:: read_rois
      :type: list


      ROI indices currently included in reads (Kind.normal or hinted).


   .. py:property:: label_option_map
      :type: dict

      :abstractmethod:


      Map label strings to ROI index integers.


   .. py:method:: select_roi(rois: list) -> None
      :abstractmethod:


      Set Kind.hinted/normal/omitted for ROIs; implementation is per-device.



   .. py:property:: plot_options
      :type: list


      Return all available ROI label strings for plot channel selection.


   .. py:method:: select_plot(channels: list) -> None

      Select which ROI channels are plotted by label name.



   .. py:method:: field_for_label(label: str) -> str

      Return the ophyd field name for a plot-option label.



   .. py:method:: select_read(channels: list) -> None

      Mark channels as Kind.normal without plotting.

      Must be called after select_plot because select_roi resets ROI kinds.



