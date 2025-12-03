=============
Event Sources
=============

| Event source plugins are responsible for generating events that trigger rule evaluation
| in `ansible-rulebook`. They can either receive events or interface with external systems,
| such as message queues, to produce event data for the rule engine.

| **To help users get started the `ansible.eda` collection provides a set of event source plugins**
| that cover common integration scenarios with Ansible Event Driven. You can explore the available source plugins here:
| https://galaxy.ansible.com/ui/repo/published/ansible/eda/content/

========================
Builtin Event Sources
========================

ansible-rulebook provides the following builtin event sources for testing and development:

* eda.builtin.range
* eda.builtin.generic
* eda.builtin.webhook
* eda.builtin.pg_listener

eda.builtin.range
-----------------

Generates events with an increasing index ``i``. Useful for testing and generating sequences of events.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - limit
     - The upper limit of the range (exclusive). Events will have index from 0 to limit-1
     - Yes
   * - delay
     - Number of seconds to wait between events. Default: 0
     - No

Example:

.. code-block:: yaml

  sources:
    - name: range_source
      eda.builtin.range:
        limit: 5
        delay: 1

This will generate 5 events: ``{"i": 0}``, ``{"i": 1}``, ``{"i": 2}``, ``{"i": 3}``, ``{"i": 4}``


eda.builtin.generic
-------------------

A generic source plugin for inserting custom test data. Useful for development, testing, and demonstrations.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - payload
     - Array of events to insert into the queue
     - Yes (unless payload_file is used)
   * - payload_file
     - Path to a YAML file containing an array of events
     - Yes (unless payload is used)
   * - loop_count
     - Number of times to loop through the payload. Default: 1
     - No
   * - randomize
     - Randomize the order of events. Default: false
     - No
   * - timestamp
     - Add a timestamp to each event. Default: false
     - No
   * - time_format
     - Format of timestamp: "local", "iso8601", or "epoch". Default: "local"
     - No
   * - create_index
     - Name of index field to add to each event (starts at 0)
     - No
   * - event_delay
     - Seconds to wait between events. Default: 0
     - No

Example:

.. code-block:: yaml

  sources:
    - name: test_data
      eda.builtin.generic:
        payload:
          - name: "Event 1"
            data: "test"
          - name: "Event 2"
            data: "example"
        loop_count: 2
        create_index: "seq"


eda.builtin.webhook
-------------------

Receive events via HTTP webhook. Provides an HTTP server endpoint that
accepts POST requests with JSON payloads.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - host
     - Hostname to listen on. Default: "0.0.0.0"
     - No
   * - port
     - TCP port to listen on
     - Yes
   * - token
     - Optional Bearer authentication token
     - No
   * - hmac_secret
     - Optional HMAC secret for payload verification
     - No
   * - hmac_algo
     - HMAC algorithm (sha256, sha512, etc.). Default: "sha256"
     - No
   * - hmac_header
     - HTTP header containing HMAC signature. Default:
       "x-hub-signature-256"
     - No
   * - hmac_format
     - HMAC signature format: "hex" or "base64". Default: "hex"
     - No
   * - certfile
     - Path to certificate file for TLS support
     - No
   * - keyfile
     - Path to key file (used with certfile)
     - No
   * - cafile
     - Path to CA certificate file for mTLS
     - No

Example:

.. code-block:: yaml

  sources:
    - name: webhook_events
      eda.builtin.webhook:
        host: 0.0.0.0
        port: 5000
        token: "my-secret-token"

Example with HMAC verification:

.. code-block:: yaml

  sources:
    - name: github_webhook
      eda.builtin.webhook:
        host: 0.0.0.0
        port: 5000
        hmac_secret: "github-webhook-secret"
        hmac_algo: "sha256"
        hmac_header: "x-hub-signature-256"
        hmac_format: "hex"

.. note::
   The webhook event source places the received payload under the
   ``payload`` key in the event data. Use the
   ``eda.builtin.insert_hosts_to_meta`` filter if you need to extract
   hosts from the payload.


eda.builtin.pg_listener
-----------------------

PostgreSQL LISTEN/NOTIFY event source. Listens for notifications from a PostgreSQL database.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - dsn
     - PostgreSQL connection string (e.g., "host=localhost dbname=mydb user=myuser password=mypass")
     - Yes
   * - channels
     - List of PostgreSQL channels to listen on
     - Yes
   * - delay
     - Polling delay in seconds. Default: 0
     - No

Example:

.. code-block:: yaml

  sources:
    - name: postgres_notifications
      eda.builtin.pg_listener:
        dsn: "host=localhost dbname=events user=eda password=secret"
        channels:
          - rulebook_events
          - alerts

.. note::
   The ``pg_listener`` source requires the ``psycopg`` library to be installed.


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

    .. note::
        Ansible Automation Platform provides integrated webhooks called **Event Streams**. 
        It is recommended to use Event Streams for webhook integrations instead of custom callback plugins.
        For more information, see the documentation:
        https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/using_automation_decisions/simplified-event-routing 



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
with a period delimit, for example ``ansible.eda.alertmanager``.

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

.. note::
    Please, pay attention when handling errors in your plugin and ensure to raise an exception with a meaningful message so that ansible-rulebook
    can log it correctly. Ansible-rulebook will not log the exception itself or print stack traces; it will only log the message you provide.

Distributing plugins
^^^^^^^^^^^^^^^^^^^^

For local tests the plugin source file can be saved under a folder specified by
the ``-S`` argument in the ansible-rulebook CLI. The recommended method for
distributing and installing the plugin is through a collection. In this case
the plugin source file should be placed under ``extensions/eda/plugins/event_source`` folder
and referred to by FQCN. The following rulebook example illustrates how to
refer to the range plugin provided as a builtin:

.. code-block:: yaml

  - name: example2
    hosts: localhost
    sources:
      - name: range
        eda.builtin.range:
          limit: 5

Any dependent packages needed by the custom plugin should be installed in the
ansible-rulebook CLI env regardless the plugin is local or from a collection.

Document plugins
^^^^^^^^^^^^^^^^

It is strongly recommended that you add comments at the top of the source file.
Please describe the purpose of the event source plugin. List all required or
optional arguments. Also add an example how to configure the plugin in a
rulebook.
