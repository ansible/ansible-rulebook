.. _event-source-plugins:

====================
Event Source Plugins
====================

Events come from event sources. Event driven automation supports many event
sources using a plugin system. Event source plugins can be stored locally but
are preferably distributed via collections.

`Ansible.eda <https://github.com/ansible/event-driven-ansible>`_
is the collection that includes our initial set of event source plugins.
These include:

..
    TODO: Add extended documentation for plugins in the collection and link to it here.

* alertmanager
    Receive events via a webhook from alertmanager

* azure_service_bus
    Receive events from an Azure service

* kafka
    Receive events via a kafka topic

* url_check
    Poll a set of URLs and send events with their statuses

* watchdog
    Watch file system and send events when a file status changes

* webhook
    Provide a webhook and receive events from it

* tick
    Generate events with an increasing index i that never ends
    Mainly used for development and testing

* file
    Load facts from YAML files initially and reload when any file changes
    Mainly used for development and testing

* range
    Generate events with an increasing index i within a range
    Mainly used for development and testing



How to Develop a Custom Plugin
------------------------------
You can build your own event source plugin in python. A plugin is a single
python file but before we get to that lets take a look at some best practices and patterns:

Best Practices and Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are 3 basic patterns that you'll be developing against when considering a new source plugin:

#. Event Bus Plugins
    These are plugins that listen to a stream of events from a source where the connection
    is established by the plugin itself. Examples of this are the ``kafka`` and ``aws_sqs_queue`` plugins.

    This is the most ideal and reliable pattern to follow. Durability and Reliability of the data
    is the responsibility of the event source and availability of the data can follow the patterns
    of the event source and its own internal configuration.

#. Scraper Plugins
    These plugins connect to a source and scrape the data from the source usually after a given amount of time
    has passed. Examples of this are the ``url_check`` and ``watchdog`` plugins.

    These plugins can be reliable but may require extract logic for handling duplication. It's also possible
    to miss data if the scraper is not running at the time the data is available.

#. Callback Plugins
    These plugins provide a callback endpoint that the event source can call when data is available.
    Examples of this are the ``webhook`` and ``alertmanager`` plugins.

    These plugins are the least reliable as they are dependent on the event source to call the callback
    endpoint and are highly sensitive to data loss. If the event source is not available or the callback
    endpoint is not available then there may not be another opportunity to receive the data.

    These can also require other ingress policies and firewall rules to be available and configured properly
    to operate.

It's strongly recommended to adopt one of the first two patterns and only consider callback plugins in the absence
of any other solution.

When deciding whether to build a dedicated plugin you may consider configuring the data source to send data to a
system where a more general plugin exists already. For example, if you have a system that can send data to a kafka
topic then you can use the ``kafka`` plugin to receive the data. There are many connectors for tying systems to other
message buses and this is a great way to leverage existing plugins.

Plugin template
^^^^^^^^^^^^^^^

Lets take a look at a very basic example that you could use in the form of a template for producing other plugins:

.. code-block:: python

  """
  template.py

  An ansible-rulebook event source plugin template.

  Arguments:
    - delay: seconds to wait between events

  Examples:
    sources:
      - template:
          delay: 1

  """
  import asyncio
  from typing import Any, Dict


  async def main(queue: asyncio.Queue, args: Dict[str, Any]):
      delay = args.get("delay", 0)

      while True:
          await queue.put(dict(template=dict(msg="hello world")))
          await asyncio.sleep(delay)


  if __name__ == "__main__":

      class MockQueue:
          async def put(self, event):
              print(event)

      mock_arguments = dict()
      asyncio.run(main(MockQueue(), mock_arguments))


Plugin entrypoint
^^^^^^^^^^^^^^^^^
The plugin python file must contain an entrypoint function exactly like the
following:

.. code-block:: python

  async def main(queue: asyncio.Queue, args: Dict[str, Any]):

It is an async function. The first argument is an asyncio queue that will be
consumed by ansible-rulebook CLI. The rest arguments are custom defined. They
must match the arguments in the source section of the rulebook. For example
the template plugin expects a single argument ``delay``. In the rulebook the
source section looks like:

.. code-block:: yaml

  - name: example
    hosts: all
    sources:
      - template:
          delay: 5

Each source must contain a key which is the name of the plugin. Its nested keys
must match argument names expected by the main function. The name of the plugin
is the python filename. If the plugin is from a collection then the plugin name
is a FQCN which is the collection name concatenating with the python filename
with a period delimit, for example ``ansible.eda.range``.

In the main function you can implement code that connects to an external source
of events, retrieves events and puts them onto the provided asyncio queue. The
event data put on the queue must be a dictionary. You can insert the ``meta``
key that points to another dictionary that holds a list of hosts. These hosts
will limit where the ansible playbook can run. A simple example looks like
``{"i": 2, "meta": {hosts: "localhost"}}``. ``hosts`` can be a comma delimited
string or a list of host names.

As the plugin have full access to an unbounded queue that is consumed by ansible-rulebbok
we carefully recommend to use always the method ``asyncio.Queue.put`` to put events as it's a non-blocking call.
To give free cpu cycles to the event loop to process the events, we recommend to use ``asyncio.sleep(0)``
immediately after the ``put`` method.

.. note::
    ansible-rulebook is intended to be a long running process and react to events over the time.
    If the ``main`` function of **any of the sources** exits then the ansible-rulebook process will be terminated.
    Usually you may want to implement a loop that keeps running and waits for events endlessly.

.. note::
    The rulebook can contain it's own logic to finish the process through the ``shutdown`` action.
    If your plugin needs to perform some cleanup before the process is terminated, you must catch the ``asyncio.CancelledError`` exception.


Distributing plugins
^^^^^^^^^^^^^^^^^^^^

For local tests the plugin source file can be saved under a folder specified by
the ``-S`` argument in the ansible-rulebook CLI. The recommended method for
distributing and installing the plugin is through a collection. In this case
the plugin source file should be placed under ``extensions/eda/plugins/event_source`` folder
and referred to by FQCN. The following rulebook example illustrates how to
refer to the range plugin provided by ``ansible.eda`` collection:

.. code-block:: yaml

  - name: example2
    hosts: localhost
    sources:
      - name: range
        ansible.eda.range:
          limit: 5

Any dependent packages needed by the custom plugin should be installed in the
ansible-rulebook CLI env regardless the plugin is local or from a collection.

Document plugins
^^^^^^^^^^^^^^^^

It is strongly recommended that you add comments at the top of the source file.
Please describe the purpose of the event source plugin. List all required or
optional arguments. Also add an example how to configure the plugin in a
rulebook.
