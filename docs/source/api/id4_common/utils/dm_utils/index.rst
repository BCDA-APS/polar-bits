id4_common.utils.dm_utils
=========================

.. py:module:: id4_common.utils.dm_utils

.. autoapi-nested-parse::

   Setup new user in Bluesky.



Attributes
----------

.. autoapisummary::

   id4_common.utils.dm_utils.esaf_api
   id4_common.utils.dm_utils.bss_api
   id4_common.utils.dm_utils.exp_api
   id4_common.utils.dm_utils.user_api
   id4_common.utils.dm_utils.DEFAULT_USERS
   id4_common.utils.dm_utils.BEAMLINE_NAME
   id4_common.utils.dm_utils.STATION


Functions
---------

.. autoapisummary::

   id4_common.utils.dm_utils.dm_workflow
   id4_common.utils.dm_utils.dm_get_experiment_data_path
   id4_common.utils.dm_utils.get_processing_job_status
   id4_common.utils.dm_utils.dm_upload
   id4_common.utils.dm_utils.dm_upload_info
   id4_common.utils.dm_utils.dm_upload_wait
   id4_common.utils.dm_utils.list_esafs
   id4_common.utils.dm_utils.get_esaf_info
   id4_common.utils.dm_utils.get_esaf_users_badge
   id4_common.utils.dm_utils.get_current_run
   id4_common.utils.dm_utils.get_current_run_name
   id4_common.utils.dm_utils.dm_experiment_setup
   id4_common.utils.dm_utils.create_dm_experiment
   id4_common.utils.dm_utils.add_dm_users
   id4_common.utils.dm_utils.get_experiment_
   id4_common.utils.dm_utils.get_experiment
   id4_common.utils.dm_utils.get_experiments_names
   id4_common.utils.dm_utils.current_run_experiments_names
   id4_common.utils.dm_utils.get_proposal_info
   id4_common.utils.dm_utils.list_proposals


Module Contents
---------------

.. py:data:: esaf_api

.. py:data:: bss_api

.. py:data:: exp_api

.. py:data:: user_api

.. py:data:: DEFAULT_USERS
   :value: ['d206409', 'd85892', 'd87100', 'd86103']


.. py:data:: BEAMLINE_NAME
   :value: '4-ID-B,G,H'


.. py:data:: STATION
   :value: '4ID'


.. py:function:: dm_workflow()

.. py:function:: dm_get_experiment_data_path(dm_experiment_name: str)

.. py:function:: get_processing_job_status(id=None, owner='user4idd')

.. py:function:: dm_upload(experiment_name, folder_path, **daqInfo)

.. py:function:: dm_upload_info(id)

.. py:function:: dm_upload_wait(id, timeout: float = DEFAULT_UPLOAD_TIMEOUT, poll_period: float = DEFAULT_UPLOAD_POLL_PERIOD)

   (bluesky plan) Wait for APS DM data acquisition to upload a file.

   PARAMETERS

   - Experiment id
   - timeout *float*: Number of seconds to wait before raising a
   'TimeoutError'.
   - poll_period *float*: Number of seconds to wait before check DM again.

   RAISES

   - TimeoutError: if DM does not identify file within 'timeout' (seconds).



.. py:function:: list_esafs(year=datetime.now().year, sector=STATION)

.. py:function:: get_esaf_info(id)

.. py:function:: get_esaf_users_badge(id)

.. py:function:: get_current_run()

.. py:function:: get_current_run_name()

.. py:function:: dm_experiment_setup(experiment_name, esaf_id=None, users_name_list: list = [], title: str = None, **kwargs)

.. py:function:: create_dm_experiment(experiment_name, description='', rootPath=None, startDate=None, endDate=None)

.. py:function:: add_dm_users(experiment_name, users_name_list)

.. py:function:: get_experiment_(experiment_name)

.. py:function:: get_experiment(experiment_name)

.. py:function:: get_experiments_names(since='2018-01-01', until='2100-01-01')

.. py:function:: current_run_experiments_names()

.. py:function:: get_proposal_info(proposal_id: int, run: str = None)

.. py:function:: list_proposals(run: str = None)

