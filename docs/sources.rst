====================
Event Source Plugins
====================

Events come from event sources.  Event driven automation supports many event
sources using a plugin system.  Event source plugins can be stored locally but
are preferably distributed via collections.  ``ansible.eda`` is a collection
that includes our initial set of event source plugins.  These include:

* alertmanager - receive events via a webhook from alertmanager
* azure_service_bus - receive events from an Azure service
* file - load facts from YAML files initially and reload when any file changes
* kafka - receive events via a kafka topic
* range - generate events with an increasing index i within a range
* tick - generate events with an increasing index i that never ends
* url_check - poll a set of URLs and send events with their statuses
* watchdog - watch file system and send events when a file status changes
* webhook - provide a webhook and receive events from it

How to Develop a Custom Plugin
------------------------------
You can build your own event source plugin in python. A plugin is a single
python file. You can start with this example:

Plugin template
^^^^^^^^^^^^^^^

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

Distributing plugins
^^^^^^^^^^^^^^^^^^^^

For local tests the plugin source file can be saved under a folder specified by
the ``-S`` argument in the ansible-rulebook CLI. The recommended method for
distributing and installing the plugin is through a collection. In this case
the plugin source file should be placed under ``plugins/event_source`` folder
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
