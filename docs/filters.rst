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

| Events filters can be chained one after the other, and the updated data is
| sent from one filter to the next.

| Events filters are defined in the rulebook after a source is defined.
| When the rulebook starts the Source plugin it associates the correct filters
| and transforms the data before putting it into the queue.

e.g.

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

.. _collection: https://github.com/ansible/event-driven-ansible/tree/main/plugins/event_filter
