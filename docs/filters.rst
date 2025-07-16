.. _event-filter:

=============
Event Filters
=============

| Events sometimes have extra data that is unnecessary and may overwhelm the
| rule engine.  Event filters allow us to remove that extra data so we can
| focus on what matters to our rules. Event filters may also change the format
| of the data so that the rule conditions can better match the data.

| Events are defined as python code and distributed as collections. The default
| eda collection_. has the following filters

.. list-table:: Event Filters
   :widths: 25 100
   :header-rows: 1

   * - Name
     - Description
   * - json_filter
     - Include and exclude keys from the event object
   * - dashes_to_underscores
     - This filter changes the dashes in all keys in the payload to be underscore.
   * - insert_hosts_to_meta
     - This filter inserts the hosts from the event into the meta key within the event
       based on a custom path in the event object.

| Events filters can be chained one after the other, and the updated data is
| sent from one filter to the next.

| Events filters are defined in the rulebook after a source is defined.
| When the rulebook starts the Source plugin it associates the correct filters
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

=====================
Builtin Event Filters
=====================
* eda.builtin.insert_meta_info
* eda.builtin.event_splitter

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


| If the incoming event payload has multiple events wrapped inside we can
| split the events into individual events using the eda.builtin.event_splitter
| filter. This is prevalent with Big Panda and Prometheus alerts.
| The filter takes in 4 parameters


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


.. _collection: https://github.com/ansible/event-driven-ansible/tree/main/extensions/eda/plugins/event_filter
