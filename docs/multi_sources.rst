========================
Including multiple Sources
========================

In a rule you can configure match one or more source, each emitting events in different format. 

Example::

    sources:
      - range:
          limit: 6
      - range2:
          limit: 5

The condition can match events from either source::

    rules:
      - name:
        condition: event.i == 2
        action:
          debug:
      - name:
        condition: event.range2.i == 1
        action:
          debug:

To avoid name conflicts the source data structure can use nested keys. The above examples assumes ``range`` 
has data like ``{"i": 1}`` and ``range2`` has data like ``{"range2": {"i": 1}}``.

Notes:

If any source terminates, it shuts down the whole engine. All events from other sources may be lost.
