id4_common.utils.run_engine_init
================================

.. py:module:: id4_common.utils.run_engine_init

.. autoapi-nested-parse::

   Setup and initialize the Bluesky RunEngine.
   ===========================================

   Local copy of ``apsbits.core.run_engine_init.init_RE`` that fixes the
   broken ``handler_name`` selector. Upstream apsbits 2.0.1 hard-codes
   ``handler_name = StoredDict`` (the class object) and then compares it to
   the string ``"PersistentDict"`` / ``"StoredDict"`` — both branches are
   always False, so ``RE.md`` is never wired up to the on-disk
   PersistentDict and `scan_id` (etc.) never restore on startup.

   Drop this shim once apsbits ships a release that picks the handler from
   the path layout instead of pinning it to a class.

   .. autosummary::
       ~init_RE







Module Contents
---------------

.. py:data:: logger

.. py:function:: init_RE(iconfig: collections.abc.Mapping[str, Any], subscribers: Optional[list[Any]] = None, **kwargs: Any) -> tuple[bluesky.RunEngine, bluesky.SupplementalData]

   Initialize and configure a Bluesky RunEngine instance.

   Mirrors :func:`apsbits.core.run_engine_init.init_RE`. The only
   behavioural difference is :data:`handler_name`, which here selects
   ``"StoredDict"`` for a file ``MD_PATH`` and ``"PersistentDict"``
   otherwise — the upstream version hard-codes the class and never
   actually restores from disk.
