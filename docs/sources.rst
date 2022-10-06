====================
Event Source Plugins
====================

Events come from event sources.  Event driven automtion supports many event sources using a plugin
system.  Event source plugins are distributed via collections.  `benthomasson.eda` is a collection
that our initial set of event source plugins.  These include:

* webhook - a basic webhook plugin
* alertmanager - a web
* azure_service_bus
* file - a way to load events from a file
* range - a way to generate events from i = 0 to i = limit
* url_check - generate events based on polling a url
* watchdog - file change events


If you want to build a custom event source plugin start with this template:

.. literalinclude :: ../tests/sources/template.py
   :language: python


