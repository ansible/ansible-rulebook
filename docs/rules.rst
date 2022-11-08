=====
Rules
=====

| Event driven automation uses rules to determine if an action should be taken when an event
| is received. A rule comprises of a name, condition(s) and action. The rule decides to run
| an action by evaluating the condition(s) that is defined by the rule book author.

Name
****

Each rule in a rule set should have a unique name. This name is displayed to the
end user in the eda-server UI to track which rules were fired.

Conditions
**********

See :doc:`conditions`


Actions
*******
See :doc:`actions`



Results
*******

When a rule's condition are satisfied we get the results back as
  * events/facts for multiple conditions
  * event/fact if a single condition

| This data is made available to your playbook as extra_vars when its invoked.
| In all the examples below you would see that facts/fact is an exact copy of events/event respectively
| and you can use either one of them in your playbook.

Single condition rule
---------------------
::

   name: "Single event"
   condition: event.i == 1
   action:
        debug:


   The extra_vars passed into the playbook will contain this data

   {'event': {'i': 1}, 'fact': {'i': 1}}


Multiple condition rule with no assignment
------------------------------------------
::


   name: "Multiple event"
   condition:
      all:
        - event.i == 1
        - event.i == 3
   action:
      debug:

   The extra vars passed into the playbook will contain this data

   {'events': {'m': {'i': 1}, 'm_1': {'i': 3}},
    'facts':  {'m': {'i': 1}, 'm_1': {'i': 3}}}

Multiple condition rule with assignment
---------------------------------------
::

     name: "Multiple event with assignment"
     condition:
        all:
          - events.first << event.i == 1
          - events.second << event.i == 3
     action:
        debug:

   The extra vars passed into the playbook will contain this data

    {'events': {'first': {'i': 1}, 'second': {'i': 3}},
     'facts':  {'first': {'i': 1}, 'second': {'i': 3}}}


Multiple condition rule with both a fact and an event without assignment
------------------------------------------------------------------------
::

      name: r2
      condition:
        all:
          - event.i == 8
          - fact.os == "windows"
      action:
        debug:

   The extra vars passed into the playbook will contain this data

     {'events': {'m_0': {'i': 8}, 'm_1': {'os': 'windows'}},
      'facts':  {'m_0': {'i': 8}, 'm_1': {'os': 'windows'}}}


Multiple condition rule with both a fact and an event with assignment
---------------------------------------------------------------------
::

    name: r2
    condition:
        all:
          - events.attr1 << event.i == 8
          - events.attr2 << fact.os == "windows"
    action:
        debug:

   The extra vars passed into the playbook will contain this data

    {'events': {'attr1': {'i': 8}, 'attr2': {'os': 'windows'}},
     'facts':  {'attr1': {'i': 8}, 'attr2': {'os': 'windows'}}}


