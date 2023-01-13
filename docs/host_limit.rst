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
