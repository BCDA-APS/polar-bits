id4_common.plans.workflow_plan
==============================

.. py:module:: id4_common.plans.workflow_plan

.. autoapi-nested-parse::

   Run DM workflow



Attributes
----------

.. autoapisummary::

   id4_common.plans.workflow_plan.dm_workflow
   id4_common.plans.workflow_plan.dm_experiment
   id4_common.plans.workflow_plan.logger
   id4_common.plans.workflow_plan.EXPECTED_KWARGS


Functions
---------

.. autoapisummary::

   id4_common.plans.workflow_plan.run_workflow


Module Contents
---------------

.. py:data:: dm_workflow

.. py:data:: dm_experiment

.. py:data:: logger

.. py:data:: EXPECTED_KWARGS

.. py:function:: run_workflow(bluesky_id=None, dm_concise: bool = False, dm_wait: bool = False, dm_reporting_period: float = 10 * 60, dm_reporting_time_limit: float = 10**6, settings_file_path: str = None, **_kwargs)

