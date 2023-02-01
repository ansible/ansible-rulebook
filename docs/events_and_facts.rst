================
Events and Facts
================


Differences between Events and Facts
************************************

Internally, there are no differences on how Events and Facts are processed. Both represent the same data, but there are some differences in the way they are used.
Events are used to represent the occurrence of something, while Facts are used to represent the state of the world. So, a fact is long live event.

An event is automatically discarded as soon it meets the condition within a rule.
A fact is not discarded, it is kept in the working memory until it is explicitly removed.

Facts can come as a result of an action, for example, cached facts from the playbook, or can be defined explicitly through the ``set_fact`` action.

You can not combine facts and events in the same condition, because there are different events for the rule engine.
This will never match:

.. code-block:: yaml

    name: An automatic remediation rule
    condition: event.outage == true and facts.beta_enabled != true
    action:
      run_playbook:
      name: remediate_outage.yml

Instead, the ``all`` operator must be used:

.. code-block:: yaml

    name: An automatic remediation rule
    condition:
      all:
        - event.outage == true
        - facts.beta_enabled != true
    action:
      run_playbook:
      name: remediate_outage.yml


.. note::
    To use facts you may use either ``events`` or ``facts`` keys interchangeably.


You can combine `set_fact <actions.html#set-fact>`_ and `retract_fact <actions.html#retract-fact>`_ actions to manage the global state during the lifecycle of your rulebook.

The text above describes how to use ``events`` or ``facts`` in a rulebook. A single matched ``event`` or multiple matched ``events`` are also
sent to a playbook through extra_vars under namespace ``ansible_eda`` when a run_playbook or run_job_template action is executed. So in a playbook
you should reference them as ``ansible_eda.event`` or ``ansible_eda.events``. Facts are not sent to playbooks.
