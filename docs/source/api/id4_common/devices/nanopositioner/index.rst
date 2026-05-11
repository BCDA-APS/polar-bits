id4_common.devices.nanopositioner
=================================

.. py:module:: id4_common.devices.nanopositioner

.. autoapi-nested-parse::

   Nanopositioner motors





Module Contents
---------------

.. py:class:: MyEpicsMotor(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, **kwargs)

   Bases: :py:obj:`ophyd.EpicsMotor`


   EpicsMotor subclass that removes velocity from stage signals on unstage.


   .. py:method:: unstage()

      Remove velocity from stage_sigs before delegating to parent unstage.



.. py:class:: NanoPositioner(prefix='', *, name, kind=None, read_attrs=None, configuration_attrs=None, parent=None, child_name_separator='_', connection_timeout=DEFAULT_CONNECTION_TIMEOUT, **kwargs)

   Bases: :py:obj:`ophyd.MotorBundle`


   Three-axis nanopositioner (X, Y, Z) using Jena piezo motors.


   .. py:attribute:: nanoy


   .. py:attribute:: nanox


   .. py:attribute:: nanoz


