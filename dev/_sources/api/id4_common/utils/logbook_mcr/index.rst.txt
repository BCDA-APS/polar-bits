id4_common.utils.logbook_mcr
============================

.. py:module:: id4_common.utils.logbook_mcr

.. autoapi-nested-parse::

   Fetch shift events from the APS Main Control Room logbook.







Module Contents
---------------

.. py:class:: ShiftEventParser

   Bases: :py:obj:`html.parser.HTMLParser`


   Parser to extract shift events from HTML.


   .. py:attribute:: events
      :value: []



   .. py:attribute:: in_shift_events
      :value: False



   .. py:attribute:: in_paragraph
      :value: False



   .. py:attribute:: current_text
      :value: ''



   .. py:attribute:: found_shift_events_header
      :value: False



   .. py:method:: handle_starttag(tag, attrs)

      Track entry into <p> and <br> tags inside the shift events section.



   .. py:method:: handle_endtag(tag)

      On </p>, split the buffered paragraph into (time, description) events.



   .. py:method:: handle_data(data)

      Buffer text inside <p> tags and detect end-of-section markers.



   .. py:method:: handle_entityref(name)

      Handle HTML entities like &nbsp; &amp; etc.



   .. py:method:: handle_charref(name)

      Handle numeric character references like &#160;



.. py:function:: fetch_shift_events(n=3)

   Fetch and display the last n shift events from the APS logbook.

   :param n: Number of shift events to display (default: 3)
   :type n: int

   :returns: List of tuples containing (time, description) for each event
   :rtype: list


