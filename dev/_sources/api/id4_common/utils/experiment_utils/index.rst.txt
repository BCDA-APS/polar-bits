id4_common.utils.experiment_utils
=================================

.. py:module:: id4_common.utils.experiment_utils

.. autoapi-nested-parse::

   Utility functions
   =================

   .. autosummary::

       ~set_experiment









Module Contents
---------------

.. py:data:: logger

.. py:data:: iconfig

.. py:data:: SERVERS

.. py:data:: path_startup

.. py:class:: ExperimentClass

   .. py:attribute:: esaf
      :value: None



   .. py:attribute:: proposal
      :value: None



   .. py:attribute:: server
      :value: None



   .. py:attribute:: base_experiment_path
      :value: None



   .. py:attribute:: windows_base_experiment_path
      :value: None



   .. py:attribute:: experiment_name
      :value: None



   .. py:attribute:: data_management
      :value: None



   .. py:attribute:: sample
      :value: None



   .. py:attribute:: file_base_name
      :value: None



   .. py:attribute:: spec_file
      :value: None



   .. py:property:: experiment_path


   .. py:method:: esaf_input(esaf_id: int = None)


   .. py:method:: proposal_input(proposal_id: int = None)


   .. py:method:: sample_input(sample: str = None)


   .. py:method:: base_name_input(base_name: str = None)


   .. py:method:: server_input(server: str = None)


   .. py:method:: experiment_name_input(experiment_name: str = None)


   .. py:method:: dm_experiment_setup(experiment_name)


   .. py:method:: setup_dm_daq()

      Configure bluesky session for this user.

      PARAMETERS

      dm_experiment_name *str*:



   .. py:method:: setup_path()


   .. py:method:: scan_number_input(reset_scan_id: int = None)


   .. py:method:: start_specwriter()


   .. py:method:: load_from_bluesky(scan_id: int = -1, reset_scan_id: int = -1, skip_DM: bool = False, useRE=False)


   .. py:method:: save_params_to_yaml()


   .. py:method:: load_params_from_yaml()


   .. py:method:: setup(esaf_id: int = None, proposal_id: int = None, base_name: str = None, sample: str = None, server: str = None, experiment_name: str = None, reset_scan_id: int = None, skip_DM: bool = False)


   .. py:method:: change_sample(sample_name: str = None, base_name: str = None, reset_scan_id: int = None)


.. py:data:: experiment

.. py:function:: experiment_setup(esaf_id: int = None, proposal_id: int = None, base_name: str = None, sample: str = None, server: str = None, experiment_name: str = None, reset_scan_id: int = None, skip_DM: bool = False)

.. py:function:: experiment_change_sample(sample_name: str = None, base_name: str = None, reset_scan_id: int = None)

.. py:function:: experiment_load_from_bluesky(reset_scan_id: int = -1, skip_DM: bool = False)

