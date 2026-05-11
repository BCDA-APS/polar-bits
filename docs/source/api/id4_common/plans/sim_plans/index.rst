id4_common.plans.sim_plans
==========================

.. py:module:: id4_common.plans.sim_plans

.. autoapi-nested-parse::

   Simulators from ophyd
   =====================

   For development and testing only, provides plans.

   .. autosummary::
       ~sim_count_plan
       ~sim_print_plan
       ~sim_rel_scan_plan







Module Contents
---------------

.. py:data:: logger

.. py:data:: DEFAULT_MD

.. py:function:: sim_count_plan(num: int = 1, imax: float = 10000, md: dict = DEFAULT_MD)

   Demonstrate the ``count()`` plan.


.. py:function:: sim_print_plan()

   Demonstrate a ``print()`` plan stub (no data streams).


.. py:function:: sim_rel_scan_plan(span: float = 5, num: int = 11, imax: float = 10000, center: float = 0, sigma: float = 1, noise: str = 'uniform', md: dict = DEFAULT_MD)

   Demonstrate the ``rel_scan()`` plan.
