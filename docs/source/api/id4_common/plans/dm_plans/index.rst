id4_common.plans.dm_plans
=========================

.. py:module:: id4_common.plans.dm_plans

.. autoapi-nested-parse::

   Plans in support of APS Data Management
   =======================================

   .. autosummary::

       ~dm_kickoff_workflow
       ~dm_list_processing_jobs
       ~dm_submit_workflow_job







Module Contents
---------------

.. py:data:: logger

.. py:function:: dm_kickoff_workflow(run, argsDict, timeout=None, wait=False)

   Start a DM workflow for this bluesky run and share run's metadata with DM.

   PARAMETERS:

   run (*obj*): Bluesky run object (such as 'run = cat[uid]').

   argsDict (*dict*): Dictionary of parameters needed by 'workflowName'.
       At minimum, most workflows expect these keys: 'filePath' and
       'experimentName'.  Consult the workflow for the expected
       content of 'argsDict'.

   timeout (*number*): When should bluesky stop reporting on this
       DM workflow job (if it has not ended). Units are seconds.
       Default is forever.

   wait (*bool*): Should this plan stub wait for the job to end?
       Default is 'False'.


.. py:function:: dm_list_processing_jobs(exclude=None)

   Show all the DM jobs with status not excluded.

   Excluded status (default): 'done', 'failed'


.. py:function:: dm_submit_workflow_job(workflowName, argsDict)

   Low-level plan stub to submit a job to a DM workflow.

   It is recommended to use dm_kickoff_workflow() instead.
   This plan does not share run metadata with DM.

   PARAMETERS:

   workflowName (*str*): Name of the DM workflow to be run.

   argsDict (*dict*): Dictionary of parameters needed by 'workflowName'.
       At minimum, most workflows expect these keys: 'filePath' and
       'experimentName'.  Consult the workflow for the expected
       content of 'argsDict'.
