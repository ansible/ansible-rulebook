==============
Limiting hosts
==============

You can limit hosts to run a playbook through configuring the meta data in an event's data.
The limiting hosts must be a subset of the hosts (inventory) selected in the rules file.

Event data example:

.. code-block:: json

    {
        "i": 0,
        "meta": {"hosts": "localhost"}
    }

The value for "hosts" can be a comma delimited string of multiple host names, but typically
it is a single host. This is useful to restrict a remedy playbook to run only on the problematical host
that emits a monitored event. Be sure that the source plugin already sends this metadata.


Inserting hosts to meta
-----------------------

The plugins may not send metadata like for example the `ansible.eda.webhook` plugin which
sends the arbitrary payload under the `payload` key.

To accommodate this, the EDA collection provides the `insert_hosts_to_meta` filter,
allowing any plugin to customize the value of `event.meta.hosts` based on the contents
of a specific key in the event.

.. note::

    The host_path argument in the filter `insert_hosts_to_meta` does not need the `event.` prefix
    like conditions or action arguments.


Example:

.. code-block:: yaml

    sources:
        - ansible.eda.webhook:
            port: 4444
          filters:
            - ansible.eda.insert_hosts_to_meta:
                host_path: "payload.alert.instances"
