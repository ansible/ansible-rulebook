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

.. _collection: https://github.com/ansible/event-driven-ansible/tree/main/extensions/eda/plugins/event_filter
