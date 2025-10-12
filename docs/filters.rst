.. _event-filter:

=============
Event Filters
=============

| Event filters provide a flexible way to preprocess event data before it is evaluated  
| by the rule engine. You can use them to remove unnecessary information and  
| to modify, enrich, or transform the event's content and structure. This ensures  
| the data is in the ideal format for your rule conditions. 

| Events are defined as Python code and distributed as collections.

| **To help users get started quickly, we already provide the `ansible.eda` collection with a set of common filters.**  
| You can explore the collection here: https://galaxy.ansible.com/ui/repo/published/ansible/eda/content/

| Event filters can be chained one after the other, and the updated data is  
| sent from one filter to the next.

| Event filters are defined in the rulebook after a source is defined.  
| When the rulebook starts the source plugin, it associates the correct filters  
| and transforms the data before putting it into the queue.

Examples:

.. code-block:: yaml

  sources:
    - name: azure_service_bus
      ansible.eda.azure_service_bus:
        conn_str: "{{connection_str}}"
        queue_name: "{{queue_name}}"
      filters:
        - json_filter:
            include_keys: ['clone_url']
            exclude_keys: ['*_url', '_links', 'base', 'sender', 'owner', 'user']
        - dashes_to_underscores:

| In the above example the data is first passed thru the json_filter and then
| thru the dashes_to_underscores filter.
| Keys in the event payload can only contain letters, numbers and underscores.
| The period (.) is used to access nested keys.

| When developing new filters you can specify the -F to specify the directory where
| your filters are located. This wont work when you have a decision environment you would
| have to distribute the filters via a collection.

=====================
Builtin Event Filters
=====================

ansible-rulebook provides the following builtin event filters:

* eda.builtin.insert_meta_info
* eda.builtin.event_splitter
* eda.builtin.dashes_to_underscores
* eda.builtin.json_filter
* eda.builtin.normalize_keys
* eda.builtin.insert_hosts_to_meta

eda.builtin.insert_meta_info
-----------------------------

| Since every event should record the origin of the event we have a filter
| eda.builtin.insert_meta_info which will be added automatically by
| ansible-rulebook to add the source name and type and received_at.
| The received_at stores a date time in UTC ISO8601 format and includes
| the microseconds.
| The uuid stores the unique id for the event.
| The event payload would be modified to include the following  data

.. code-block:: python

   event = { ..., 'meta': {'source': {'name': 'azure_service_bus',
                                      'type': 'ansible.eda.azure_service_bus'},
                           'received_at': '2023-03-23T19:11:15.802274Z',
                           'uuid': 'eb7de03f-6f8f-4943-b69e-3c90db346edf'}
           }

| The meta key is used to store metadata about the event and its needed to
| correctly report about the events in the aap-server.


eda.builtin.event_splitter
---------------------------

| If the incoming event payload has multiple events wrapped inside we can
| split the events into individual events using the eda.builtin.event_splitter
| filter. This is prevalent with Big Panda and Prometheus alerts.
| The filter takes in 4 parameters:


.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - splitter_key
     - The nested key which stores the array of events. You can use the dot delimiter to specify the path e.g incident.alerts
     - Yes
   * - attribute_key_map
     - If you need to add additional attributes from the parent nodes into the event, specified as a dictionary
     - No
   * - extras
     - If you need to add static attributes into the event, specified as a dictionary
     - No
   * - raise_error
     - true or false. If the splitter_key is missing we can stop the source by setting raise_error as true. Default is false, we would return the event as it is if the splitter_key is missing.
     - No


Examples:

.. code-block:: yaml

  sources:
    - name: my_prometheus
      ansible.eda.alertmanager:
         ...
      filters:
        - eda.builtin.event_splitter:
            splitter_key: alerts 
            attributes_key_map:
              header: header
              hosts: labels.instance 
            extras:
              region: us-east  


.. code-block:: yaml


  sources:
    - name: my_bigpanda
      ...big_panda...:
         ...
      filters:
        - eda.builtin.event_splitter:
            splitter_key: incident.alerts
            attributes_key_map:
               id: incident.id
               active: incident.active
               severity: incident.severity
               status: incident.status
               environments: incident.environments


eda.builtin.dashes_to_underscores
----------------------------------

Changes dashes in event keys to underscores. For instance, the key ``server-name`` becomes ``server_name``.
This filter processes all dictionary keys recursively, including those nested in lists. It takes one parameter:

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - overwrite
     - Overwrite values if there is a key collision when converting dashes to underscores. Default: true
     - No

Examples:

.. code-block:: yaml

  sources:
    - name: my_webhook
      ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
      filters:
        - eda.builtin.dashes_to_underscores:
            overwrite: false

.. code-block:: yaml

  # Input event
  {
    "server-name": "web01",
    "app-version": "1.0"
  }

  # Output event
  {
    "server_name": "web01",
    "app_version": "1.0"
  }


eda.builtin.json_filter
------------------------

Filters keys from events based on include/exclude patterns. The ``include_keys`` parameter protects keys
from being excluded (it doesn't act as a whitelist). Include patterns override exclude patterns.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - exclude_keys
     - List of key patterns to remove (supports wildcards like ``*`` and ``?``)
     - No
   * - include_keys
     - List of key patterns to keep even if they match exclude patterns
     - No

Examples:

.. code-block:: yaml

  sources:
    - name: my_source
      ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
      filters:
        - eda.builtin.json_filter:
            exclude_keys:
              - 'metadata'
              - 'internal_*'
            include_keys:
              - 'internal_id'

.. code-block:: yaml

  # Input event
  {
    "data": "important",
    "metadata": "remove",
    "internal_debug": "remove",
    "internal_id": "keep"
  }

  # Output event (internal_id kept despite matching internal_*)
  {
    "data": "important",
    "internal_id": "keep"
  }


eda.builtin.normalize_keys
---------------------------

Normalizes keys by replacing non-alphanumeric characters with underscores. Consecutive special characters
are coalesced into a single underscore. For example, ``server.name`` becomes ``server_name`` and
``server--name`` becomes ``server_name``.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - overwrite
     - Overwrite values if there is a key collision after normalization. Default: true
     - No

Examples:

.. code-block:: yaml

  sources:
    - name: my_source
      ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
      filters:
        - eda.builtin.normalize_keys:

.. code-block:: yaml

  # Input event
  {
    "server.name": "web01",
    "app@version": "1.0",
    "data--key": "value"
  }

  # Output event
  {
    "server_name": "web01",
    "app_version": "1.0",
    "data_key": "value"
  }


eda.builtin.insert_hosts_to_meta
---------------------------------

Extracts hosts from event data and inserts them into the meta dictionary. In ansible-rulebook,
this limits actions to run only on the specified hosts in the meta dict.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - host_path
     - The JSON path inside the event data to find hosts (uses dot notation)
     - Yes
   * - path_separator
     - The separator to interpret host_path. Default: "."
     - No
   * - host_separator
     - Separator to split host string if it contains multiple hosts
     - No
   * - raise_error
     - Raise error if host_path doesn't exist. Recommended for development. Default: false
     - No
   * - log_error
     - Log error if host_path doesn't exist. Default: true
     - No

Examples:

.. code-block:: yaml

  sources:
    - name: my_alertmanager
      ansible.eda.alertmanager:
        host: 0.0.0.0
        port: 5050
      filters:
        - eda.builtin.insert_hosts_to_meta:
            host_path: "alert.target"
            path_separator: "."
            raise_error: true

.. code-block:: yaml

  # Input event
  {
    "alert": {
      "target": "server1.example.com",
      "severity": "critical"
    }
  }

  # Output event
  {
    "alert": {
      "target": "server1.example.com",
      "severity": "critical"
    },
    "meta": {
      "hosts": ["server1.example.com"]
    }
  }




.. _collection: https://github.com/ansible/event-driven-ansible/tree/main/extensions/eda/plugins/event_filter
