id4_common.plans.flyscan_demo
=============================

.. py:module:: id4_common.plans.flyscan_demo

.. autoapi-nested-parse::

   Flyscan using area detector







Module Contents
---------------

.. py:data:: iconfig

.. py:data:: logger

.. py:data:: sgz

.. py:data:: dm_experiment

.. py:data:: HDF1_NAME_FORMAT

.. py:function:: flyscan_snake(detectors, stepping_motor, stepping_motor_start, stepping_motor_end, stepping_motor_number_of_points, flying_motor, flying_motor_start, flying_motor_end, flying_motor_speed, detector_trigger_period: float = 0.02, detector_collection_time: float = 0.01, file_name_base: str = 'scan', master_file_templates: list = [], md: dict = {}, dm_concise: bool = False, dm_wait: bool = False, dm_reporting_period: float = 10 * 60, dm_reporting_time_limit: float = 10**6, nxwriter_warn_missing: bool = False, wf_run: bool = False, wf_settings_file_path: str = None, **wf_kwargs)

   Flyscan using a "snake" trajectory.

   Note the first motor in *args will step and the second will fly (by doing a
   two point step).

   :param eiger: Currently sort of hardwired for the Eiger, but this will be removed in
                 the future to match with the POLAR standard of defaulting to our
                 `counters` class.
   :type eiger: Eiger detector instance
   :param \*args: The first motor is the outer loop that will step, with the second motor
                  flying between the ends. Thus the first motor needs a number of steps.
                  .. code-block:: python
                      motor1, start1, stop1, number of point, motor2, start2, stop
   :param speed: Velocity of the flying motor. This will be passed to `motor2.velocity`
                 through staging.
   :type speed: float, default to 10
   :param trigger_time: Time between detector triggers.
   :type trigger_time: float, default to 0.02 seconds
   :param collection_time: Time that detector spend collecting the image. It must be smaller or
                           equal to the trigger_time otherwise a ValueError is raised.
   :type collection_time: float, default to 0.01 seconds
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plan_patterns.outter_product`, :func:`flyscan_cycler`


.. py:function:: flyscan_1d(detectors, motor, start, end, speed, detector_trigger_period: float = 0.02, detector_collection_time: float = 0.01, master_file_templates: list = [], file_name_base: str = 'scan', md: dict = {}, dm_concise: bool = False, dm_wait: bool = False, dm_reporting_period: float = 10 * 60, dm_reporting_time_limit: float = 10**6, nxwriter_warn_missing: bool = False, wf_run: bool = False, wf_settings_file_path: str = None, **wf_kwargs)

   Flyscan in 1 dimension.

   :param eiger: Currently sort of hardwired for the Eiger, but this will be removed in
                 the future to match with the POLAR standard of defaulting to our
                 `counters` class.
   :type eiger: Eiger detector instance
   :param motor: Ideally it is a motor with a custom unstaging that removes "velocity"
                 from the stage_sigs, see ../devices/nanopositioners.py
   :type motor: ophyd motor object
   :param start: Initial motor position
   :type start: float
   :param end: Final motor position
   :type end: float
   :param speed: Velocity of the flying motor. This will be passed to `motor.velocity`
                 through staging.
   :type speed: float, default to 10
   :param trigger_time: Time between detector triggers.
   :type trigger_time: float, default to 0.02 seconds
   :param collection_time: Time that detector spend collecting the image. It must be smaller or
                           equal to the trigger_time otherwise a ValueError is raised.
   :type collection_time: float, default to 0.01 seconds
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plan_patterns.inner_product`, :func:`flyscan_cycler`


.. py:function:: flyscan_cycler(detectors: list, cycler, speeds: list, detector_trigger_period: float = 0.02, detector_collection_time: float = 0.01, master_file_templates: list = [], file_name_base: str = 'scan', md: dict = {}, dm_concise: bool = False, dm_wait: bool = False, dm_reporting_period: float = 10 * 60, dm_reporting_time_limit: float = 10**6, nxwriter_warn_missing: bool = False, wf_run: bool = False, wf_settings_file_path: str = None, **wf_kwargs)

   Flyscan using a generic path.

   Note that only the last motor will fly (by doing a two point step).

   :param detectors: Currently sort of hardwired for the Eiger, which must be the first item
                     in the list. But this will be removed in the future to match with the
                     POLAR standard of defaulting to our `counters` class.
   :type detectors: list of ophyd detectors
   :param cycler: cycler.Cycler object mapping movable interfaces to positions.
   :type cycler: Cycler
   :param speeds: Velocity of the motors, this is particularly useful for the flying
                  motor. If `None`, then the speed will not be changed. The speed will be
                  passed to `motor.velocity` through staging (see
                  ../devices/nanopositioners.py).
   :type speeds: list
   :param trigger_time: Time between detector triggers.
   :type trigger_time: float, default to 0.02 seconds
   :param collection_time: Time that detector spend collecting the image. It must be smaller or
                           equal to the trigger_time otherwise a ValueError is raised.
   :type collection_time: float, default to 0.01 seconds
   :param md: Metadata to be added to the run start.
   :type md: dictionary, optional

   .. seealso:: :func:`bluesky.plan_patterns.outter_product`, :func:`bluesky.plan_patterns.inner_product`


