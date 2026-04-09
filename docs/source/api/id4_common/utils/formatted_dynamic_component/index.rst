id4_common.utils.formatted_dynamic_component
============================================

.. py:module:: id4_common.utils.formatted_dynamic_component


Classes
-------

.. autoapisummary::

   id4_common.utils.formatted_dynamic_component.FormattedDynamicSubDevice
   id4_common.utils.formatted_dynamic_component.InstanceFormattedComponent


Module Contents
---------------

.. py:class:: FormattedDynamicSubDevice(factory_func)

   Creates a subdevice with dynamically formatted components.


   .. py:attribute:: factory_func


.. py:class:: InstanceFormattedComponent(factory_func)

   Acts like a Component that can interpolate format strings using the
   instance's __dict__. Used to dynamically build a subdevice based on
   instance parameters (like self.prefix1).


   .. py:attribute:: factory_func


