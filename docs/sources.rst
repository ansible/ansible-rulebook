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


====================================
Developing Custom Event Source Plugins
====================================

You can build your own event source plugin in Python. A plugin is a single
Python file.

When deciding whether to build a dedicated plugin, first consider configuring the data source to send data to a
system where a more general plugin exists already. For example, if you have a system that can send data to a Kafka
topic then you can use the ``ansible.eda.kafka`` plugin to receive the data. There are many connectors for tying
systems to other message buses and this is a great way to leverage existing plugins.

Before getting started, let's take a look at some best practices and patterns:

Best Practices and Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are 3 patterns for developing event source plugins:

#. **Event Bus Plugins (Recommended)**
    These are plugins that listen to a stream of events from a message bus or queue where the connection
    is established by the plugin itself. Examples include the ``ansible.eda.kafka`` and
    ``ansible.eda.aws_sqs_queue`` plugins.

    **This is the recommended and most reliable pattern to follow.** Event bus plugins provide:

    - **Durability**: Messages are persisted by the message bus until consumed
    - **Reliability**: Built-in retry and error handling mechanisms
    - **Scalability**: Message buses are designed to handle high-volume event streams
    - **Ordering**: Events are typically delivered in order
    - **Acknowledgment**: Plugins can acknowledge successful processing

    The durability and reliability of the data is the responsibility of the event source, and availability
    of the data can follow the patterns of the event source and its own internal configuration.

    When possible, consider using connectors or integration tools to send your platform's events to a
    well-supported message bus (like Kafka, Azure Service Bus, or AWS SQS) rather than building a custom
    source plugin. This allows you to leverage existing, well-tested plugins.

#. **Callback Plugins (Use with Caution)**
    These plugins provide a callback endpoint (typically a webhook receiver) that external event sources
    can call when data is available. The ``eda.builtin.webhook`` plugin is an example of this pattern.

    **Important considerations for callback plugins:**

    - **Data loss risk**: If the callback endpoint is unavailable when an event occurs, the event may be lost
    - **Network requirements**: Require proper ingress policies, firewall rules, and network accessibility
    - **No built-in retry**: If the external system doesn't implement retry logic, events may not be redelivered
    - **Security concerns**: Exposing HTTP endpoints requires careful authentication and authorization

    .. note::
        **Recommendation**: Use Ansible Automation Platform's integrated **Event Streams** feature instead
        of building custom callback plugins. Event Streams provide a managed webhook infrastructure with
        better reliability and security.

        For more information, see:
        https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/using_automation_decisions/simplified-event-routing

#. **Scraper Plugins**
    These plugins connect to a source and scrape the data from it, usually after a given amount of time
    has passed. Examples include the ``ansible.eda.url_check`` and ``ansible.eda.file_watch`` plugins.

    Scraper plugins can be reliable but may require extra logic for handling duplication. It is also possible
    to miss data if the scraper is not running at the time the data is available. This pattern can be useful
    when there is no message bus or external callback/trigger available.

**Choosing the Right Pattern**

- **Use Event Bus plugins** when your platform can publish events to a message bus, you need reliable event delivery, or you need to handle high event volumes
- **Use Callback plugins** when the external system can only push events via webhooks and you accept the reliability tradeoffs
- **Use Scraper plugins** when there is no message bus available and the data source can be polled periodically



Plugin template
^^^^^^^^^^^^^^^

The following example demonstrates a complete event source plugin template to use
as a starting point for developing custom plugins. This template includes proper documentation
using the sidecar format (``DOCUMENTATION`` and ``EXAMPLES`` blocks) which is required for plugins to
render correctly in Automation Hub.

.. literalinclude:: template.py
   :language: python


Plugin entrypoint
^^^^^^^^^^^^^^^^^
The plugin python file must contain an entrypoint function exactly like the
following:

.. literalinclude:: template.py
   :language: python
   :lines: 56

It is an async function. The first argument is an asyncio queue that will be
consumed by ansible-rulebook CLI. The rest arguments are custom defined. They
must match the arguments in the source section of the rulebook. For example
the template plugin expects arguments like ``delay`` and ``message``. In the rulebook the
source section looks like:

.. code-block:: yaml

  - name: example
    hosts: all
    sources:
      - template:
          delay: 5
          message: "hello world"

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
``{"i": 2, "meta": {"hosts": "localhost"}}``. ``hosts`` can be a comma delimited
string or a list of host names.

As the plugin puts events onto a bounded queue (maxsize=1) that is consumed by ansible-rulebook,
we recommend to always use the ``await queue.put(data)`` method to put events, as it will wait
if the queue is full until space becomes available.
To give free cpu cycles to the event loop to process the events, we recommend to use ``asyncio.sleep(0)``
immediately after the ``put`` method.

.. note::
    ansible-rulebook is intended to be a long running process and react to events over time.
    If the ``main`` function of **any of the sources** exits then the ansible-rulebook process will be terminated.
    Usually you may want to implement a loop that keeps running and waits for events endlessly.

.. note::
    The rulebook can contain it's own logic to finish the process through the ``shutdown`` action.
    If your plugin needs to perform some cleanup before the process is terminated, you must catch the ``asyncio.CancelledError`` exception.

.. note::
    Please, pay attention when handling errors in your plugin and ensure to raise an exception with a meaningful message so that ansible-rulebook
    can log it correctly.

Testing plugins
^^^^^^^^^^^^^^^

Here are some approaches to test a plugin:

**Standalone Testing**

The recommended approach is to include a ``if __name__ == "__main__":`` block in the plugin
file that allows it to run independently for testing. This was shown in the plugin template above.

.. literalinclude:: template.py
   :language: python
   :lines: 72-79

The plugin can be then tested directly:

.. code-block:: console

  $ python3 extensions/eda/plugins/event_source/my_plugin.py

**Testing with a Rulebook**

Create a test rulebook that uses the plugin with various configurations:

.. code-block:: yaml

  - name: Test my custom plugin
    hosts: localhost
    sources:
      - name: test_source
        my_namespace.my_collection.my_plugin:
          param1: value1
          param2: value2
    rules:
      - name: Debug events
        condition: event.my_plugin is defined
        action:
          debug:
            msg: "Received event: {{ event }}"

Then run the rulebook with the plugin:

.. code-block:: console

  $ ansible-rulebook -i inventory.yml --rulebook test_rulebook.yml -S /path/to/plugin/directory

**Unit Testing**

For more comprehensive testing, a recommended approach is to use `pytest <https://pytest.org>`_. Here's an example test structure:

.. code-block:: python

  import asyncio
  import contextlib
  import pytest
  from extensions.eda.plugins.event_source import my_plugin


  @pytest.mark.asyncio
  async def test_plugin_generates_events():
      queue = asyncio.Queue()
      args = {"delay": 0, "message": "test"}

      # Run plugin for limited time
      task = asyncio.create_task(my_plugin.main(queue, args))
      await asyncio.sleep(0.1)
      task.cancel()

      # Verify events were generated
      assert not queue.empty()
      event = await queue.get()
      assert "my_plugin" in event


  @pytest.mark.asyncio
  async def test_plugin_handles_invalid_args():
      queue = asyncio.Queue()
      args = {"invalid_param": "value"}

      # Plugin should handle missing required args gracefully
      # Start plugin as background task to avoid blocking
      task = asyncio.create_task(my_plugin.main(queue, args))

      try:
          # Use a short timeout to force prompt failure
          with pytest.raises(Exception):
              await asyncio.wait_for(task, timeout=1.0)
      finally:
          # Ensure task is cancelled if still running
          if not task.done():
              task.cancel()
              with contextlib.suppress(asyncio.CancelledError):
                  await task


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

Event source plugins must use the **sidecar documentation format** with ``DOCUMENTATION`` and
``EXAMPLES`` blocks. This format enables the plugin documentation to be rendered correctly
in Automation Hub and Galaxy.

**Required Documentation Blocks**

The plugin must include the following documentation blocks at the top of the file:

1. ``DOCUMENTATION`` **block** - A YAML-formatted string describing the plugin, its options, and metadata
2. ``EXAMPLES`` **block** - Practical examples showing how to use the plugin in a rulebook

**DOCUMENTATION Block Format**

The ``DOCUMENTATION`` block must be a module-level variable containing a YAML string:

.. literalinclude:: template.py
   :language: python
   :lines: 10-33

**Key Fields Explained:**

- ``short_description``: One-line summary (required)
- ``description``: Detailed explanation as a list of strings (required)
- ``options``: Dictionary of all plugin parameters (required if plugin accepts parameters)

  - ``description`` (`str`): What the parameter does (required)
  - ``type`` (`str`): Data type (``str``, ``int``, ``bool``, ``list``, ``dict``, ``float``, ``path``) (required)
  - ``required`` (`bool`): Whether the parameter is mandatory (optional)
  - ``default``: Default value if not provided (optional)
  - ``choices`` (`list`): List of valid values (optional)
  - ``elements`` (`str`): Type of list elements when type is ``list`` (optional)

**EXAMPLES Block Format**

The ``EXAMPLES`` block shows how to use the plugin in a rulebook:

.. literalinclude:: template.py
   :language: python
   :lines: 35-53

**Validation**

The ``DOCUMENTATION`` and ``EXAMPLES`` blocks follow the same YAML format used by Ansible modules.
When your plugin is distributed within a collection, these blocks are automatically parsed and
rendered in Automation Hub and Galaxy, making your plugin documentation available to users
browsing the collection.
