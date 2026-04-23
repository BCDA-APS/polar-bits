id4_common.utils.run_engine_init
================================

.. py:module:: id4_common.utils.run_engine_init

.. autoapi-nested-parse::

   Setup and initialize the Bluesky RunEngine.
   ===========================================

   This module provides the function init_RE to create and configure a
   Bluesky RunEngine with metadata storage, subscriptions, and various
   settings based on a configuration dictionary.

   .. autosummary::
       ~init_RE







Module Contents
---------------

.. py:data:: logger

.. py:function:: init_RE(iconfig: dict[str, Any], bec_instance: Optional[Any] = None, cat_instance: Optional[Any] = None, **kwargs: Any) -> tuple[bluesky.RunEngine, bluesky.SupplementalData]

   Initialize and configure a Bluesky RunEngine instance.

   This function creates a Bluesky RunEngine, sets up metadata storage,
   subscriptions, and various preprocessors based on the provided
   configuration dictionary. It configures the control layer and timeouts,
   attaches supplemental data for baselines and monitors, and optionally
   adds a progress bar and metadata updates from a catalog or BestEffortCallback.

   :param iconfig: Configuration dictionary with keys including:
                   - "RUN_ENGINE": A dict containing RunEngine-specific settings.
                   - "DEFAULT_METADATA": (Optional) Default metadata for the RunEngine.
                   - "USE_PROGRESS_BAR": (Optional) Boolean flag to enable the progress bar.
                   - "OPHYD": A dict for control layer settings
                   (e.g., "CONTROL_LAYER" and "TIMEOUTS").
   :type iconfig: Dict[str, Any]
   :param bec_instance: Instance of BestEffortCallback for subscribing
                        to the RunEngine. Defaults to None.
   :type bec_instance: Optional[Any]
   :param cat_instance: Instance of a databroker catalog for subscribing
                        to the RunEngine. Defaults to None.
   :type cat_instance: Optional[Any]
   :param \*\*kwargs: Additional keyword arguments passed to the RunEngine constructor.
                      For example, run_returns_result=True.

   :returns: A tuple containing the
             configured RunEngine instance and its associated SupplementalData.
   :rtype: Tuple[bluesky.RunEngine, bluesky.SupplementalData]

   .. rubric:: Notes

   The function attempts to set up persistent metadata storage in the RE.md attr.
   If an error occurs during the creation of the metadata storage handler,
   the error is logged and the function proceeds without persistent metadata.
   Subscriptions are added for the catalog and BestEffortCallback if provided, and
   additional configurations such as control layer, timeouts, and progress bar
   integration are applied.


