id4_common.devices.softgluezynq_parts
=====================================

.. py:module:: id4_common.devices.softgluezynq_parts

.. autoapi-nested-parse::

   SoftGlueZynq



Attributes
----------

.. autoapisummary::

   id4_common.devices.softgluezynq_parts.logger


Classes
-------

.. autoapisummary::

   id4_common.devices.softgluezynq_parts.SoftGlueSignal
   id4_common.devices.softgluezynq_parts.SGZDevideByN
   id4_common.devices.softgluezynq_parts.SGZUpCounter
   id4_common.devices.softgluezynq_parts.SGZDownCounter
   id4_common.devices.softgluezynq_parts.SGZGateDly
   id4_common.devices.softgluezynq_parts.SGZClocks
   id4_common.devices.softgluezynq_parts.SGZGates
   id4_common.devices.softgluezynq_parts.SGZDFF
   id4_common.devices.softgluezynq_parts.SGZHistScal
   id4_common.devices.softgluezynq_parts.SGZhistScalerDma
   id4_common.devices.softgluezynq_parts.SoftGlueScalToStream
   id4_common.devices.softgluezynq_parts.SampleXY


Module Contents
---------------

.. py:data:: logger

.. py:class:: SoftGlueSignal

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: signal


   .. py:attribute:: bi


.. py:class:: SGZDevideByN

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: enable


   .. py:attribute:: clock


   .. py:attribute:: reset


   .. py:attribute:: out


   .. py:attribute:: n


.. py:class:: SGZUpCounter

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: enable


   .. py:attribute:: clock


   .. py:attribute:: reset


   .. py:attribute:: counts


.. py:class:: SGZDownCounter

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: enable


   .. py:attribute:: clock


   .. py:attribute:: load


   .. py:attribute:: preset


   .. py:attribute:: out


.. py:class:: SGZGateDly

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: input


   .. py:attribute:: clock


   .. py:attribute:: delay


   .. py:attribute:: width


   .. py:attribute:: out


.. py:class:: SGZClocks

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: clock_10MHz


   .. py:attribute:: clock_20MHz


   .. py:attribute:: clock_50MHz


   .. py:attribute:: clock_variable


.. py:class:: SGZGates

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: in1


   .. py:attribute:: in2


   .. py:attribute:: out


.. py:class:: SGZDFF

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: set_


   .. py:attribute:: d


   .. py:attribute:: clock


   .. py:attribute:: clear


   .. py:attribute:: out


.. py:class:: SGZHistScal

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: en


   .. py:attribute:: sync


   .. py:attribute:: det


   .. py:attribute:: det2


   .. py:attribute:: mode


   .. py:attribute:: clock


   .. py:attribute:: read_


   .. py:attribute:: clear


.. py:class:: SGZhistScalerDma

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: enable


   .. py:attribute:: scan


   .. py:attribute:: read_button


   .. py:attribute:: clear_button


   .. py:attribute:: debug


   .. py:attribute:: hist


.. py:class:: SoftGlueScalToStream

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: reset


   .. py:attribute:: chadv


   .. py:attribute:: imtrig


   .. py:attribute:: flush


   .. py:attribute:: full


   .. py:attribute:: advdone


   .. py:attribute:: imdone


   .. py:attribute:: fifo


   .. py:attribute:: dmawords


.. py:class:: SampleXY

   Bases: :py:obj:`ophyd.Device`


   .. py:attribute:: x_offset


   .. py:attribute:: y_offset


   .. py:attribute:: pitch_offset


   .. py:attribute:: x


   .. py:attribute:: y


   .. py:attribute:: dx


   .. py:attribute:: pitch


