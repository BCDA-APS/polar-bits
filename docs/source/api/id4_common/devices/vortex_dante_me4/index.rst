id4_common.devices.vortex_dante_me4
===================================

.. py:module:: id4_common.devices.vortex_dante_me4

.. autoapi-nested-parse::

   Vortex 4 element with Dante electronics







Module Contents
---------------

.. py:data:: MAX_TIME
   :value: 3600


.. py:data:: MAX_ROIS
   :value: 32


.. py:class:: Trigger(*args, image_name=None, **kwargs)

   Bases: :py:obj:`id4_common.devices.ad_mixins.TriggerBase`


   This trigger mixin class takes one acquisition per trigger.


   .. py:attribute:: stage_sigs


   .. py:method:: setup_manual_trigger()

      Configure stage_sigs for software-triggered (manual) single-shot
      acquisition.



   .. py:method:: setup_external_trigger()
      :abstractmethod:


      Raise NotImplementedError; the Dante cannot be used in flyscans.



   .. py:method:: stage()

      Subscribe the busy-signal callback and arm the detector before staging.



   .. py:method:: unstage()

      Stop the Dante, unsubscribe the busy callback, and restore manual-
      trigger mode.



   .. py:method:: trigger()

      Start one Dante acquisition and return a status object that completes
      when done.



.. py:class:: TotalCorrectedSignal(prefix, roi_index=0, **kwargs)

   Bases: :py:obj:`ophyd.SignalRO`


   Signal that returns the deadtime corrected total counts


   .. py:attribute:: roi_index
      :value: 0



   .. py:method:: get(**kwargs)

      Return the sum of deadtime-corrected ROI counts across all Dante
      channels.



.. py:class:: VortexDante4(*args, default_folder=Path('/net/s4data/export/sector4/4idd/bluesky_images/vortex'), hdf1_file_format='%s/%s_%6.6d.h5', **kwargs)

   Bases: :py:obj:`Trigger`, :py:obj:`id4_common.devices.counters_mixin.ROICountersMixin`, :py:obj:`ophyd.areadetector.DetectorBase`


   Four-element Vortex detector driven by a Dante MCA with HDF5 file saving.


   .. py:attribute:: cam


   .. py:attribute:: mcas


   .. py:attribute:: scas


   .. py:attribute:: total


   .. py:attribute:: hdf1


   .. py:attribute:: default_folder


   .. py:attribute:: hdf1_file_format
      :value: '%s/%s_%6.6d.h5'



   .. py:property:: num_channels

      Return the number of MCA channels for this detector.


   .. py:method:: align_on()

      Start detector in alignment mode



   .. py:method:: align_off()

      Stop detector



   .. py:method:: save_images_on()

      Enable the HDF5 plugin so acquisitions are written to disk.



   .. py:method:: save_images_off()

      Disable the HDF5 plugin so acquisitions are not written to disk.



   .. py:method:: auto_save_on()

      Enable HDF5 autosave so files are written automatically.



   .. py:method:: auto_save_off()

      Disable HDF5 autosave.



   .. py:method:: default_settings()

      Configure HDF5 path, stage signals, ROIs, and manual-trigger mode.



   .. py:property:: read_rois

      Return the list of ROI indices that are currently included in reads.


   .. py:method:: select_roi(rois)

      Set the hinted ROI totals to those in rois, keeping other read_rois as
      normal.



   .. py:method:: plot_roi0()

      Set ROI 0 as the hinted plot channel.



   .. py:method:: plot_roi1()

      Set ROI 1 as the hinted plot channel.



   .. py:method:: plot_roi2()

      Set ROI 2 as the hinted plot channel.



   .. py:method:: plot_roi3()

      Set ROI 3 as the hinted plot channel.



   .. py:method:: plot_roi4()

      Set ROI 4 as the hinted plot channel.



   .. py:property:: label_option_map

      Return a mapping from human-readable ROI label strings to ROI index
      integers.


   .. py:method:: setup_images(base_folder, file_name_base, file_number, flyscan=False)

      Configure HDF5 file name, number, path, and flysetup flag for an
      upcoming scan.



   .. py:property:: save_image_flag

      Return True if the HDF5 plugin is enabled or autosave is on.


