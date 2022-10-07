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

| The condition(s) is written using a subset of Jinja syntax. Each of the 
| condition(s) can use information from

 * Event received 
 * Previously saved events
 * Longer term facts about the system
 * Variables provided by the user at startup saved as facts

When writing conditions 
  * use the event/events prefix when accessing data from the current event.
  * use the fact/facts prefix when accessing data from the facts stored in the rule engine.


The following is an example rule::

    name:  An automatic remediation rule
    condition:  event.outage == True
    action:
        run_playbook:
            name: remediate_outage.yml

| This rule searches for a recent event with the data `outage` being `True`. If an event
| with this condition is found then the `remediate_outage.yml` playbook is run.

A condition can contain
 * One condition
 * Multiple conditions where all of them have to match
 * Multiple conditions where any one of them has to match

**Examples**

Single condition
----------------
::

    name:  An automatic remediation rule
    condition:  event.outage == True
    action:
        run_playbook:
            name: remediate_outage.yml



Multiple conditions where **all** of them have to match
-------------------------------------------------------
::

      name: All conditions must match
      condition:
        all:
          - event.target_os == "linux"
          - event.tracking_id == 345 
      action:
        debug:

Multiple conditions where **any** one of them has to match
----------------------------------------------------------
::

      name: Any condition can match
      condition:
        any:
          - event.target_os == "linux"
          - event.target_os == "windows"
      action:
        debug:

Multiple conditions with facts and events and **all** of one of them have to match
----------------------------------------------------------------------------------
::

      name: Condition using both a fact and an event
      condition:
        all:
          - fact.meta.hosts == "localhost"
          - event.target_os == "windows"
      action:
        debug:

| When evaluating a single event you can compare multiple 
| properties/attributes from the event using **and** or **or**

Logical and
-----------
::

      name: Multiple Attribute match from a single event
      condition: event.target_os == "linux" and event.version == "1.1"
      action:
        debug:

Logical or
----------
::

      name: Match any one attribute from a single event
      condition: event.version == "2.0" or event.version == "1.1"
      action:
        debug:

| The "and" and "or" keywords are case sensitive. You can't use 
| "AND" or "OR" for the logical operators.


| When a condition is evaluated if the condition passes the matching event 
| is stored in a well known attribute called **m**, **m_1**, **m_2**.....
| You can optionally alias this attribute using the **<<** operator e.g

Multiples condition with assignment
-----------------------------------
::

      name: multiple conditions
      condition:
        all:
          - events.first << event.i == 0
          - events.second << event.i == 1
          - events.third << event.i == events.first.i + 2 
      action:
        debug:
          first: "{{events.first}}"
          second: "{{events.second}}"
          third: "{{events.third}}"

| When using the assignment operator the attribute names should have the 
| **events.** or **facts.** prefix. In the above example we are saving the
| matching events per condition as events.first, events.second and events.third.
| In the third condition we are using the saved event in events.first to do 
| a comparison.

Multiple condition with default assignments
-------------------------------------------
::

     name: multiple conditions
     condition:
        all:
          - event.i == 1
          - event.i == 2
          - event.i == events.m.i + 3 
     action:
        debug:
          first: "{{events.m}}"
          second: "{{events.m_1}}"
          third: "{{events.m_2}}"

The first match is stored as **m**, and the subsequent ones are stored as **m_1**, **m_2** ...

Single condition assignment (Not supported)
-------------------------------------------
::

     name: assignment ignored
     condition: event.first << event.i == 0
     action:
       debug:
         event: "{{event}}"

| Assignment **cannot** be used for rules that have a single condition, the 
| matching event will always be called **event**. In the above example **event.first** 
| is ignored and the matching event is stored as **event**




Actions
*******

When a rule matches the conditions, it fires the corresponding action for the rule.
The following actions are supported

.. list-table:: Actions
   :widths: 25 150
   :header-rows: 1

   * - Name
     - Description
   * - run_playbook
     - Run an Ansible playbook from a collection
   * - run_module
     - Run an Ansible module from a collection or from the Ansible built in modules
   * - assert_fact
     - Assert a fact to the rule set, will fire all matching rules 
   * - post_event
     - Assert an event to the rule set, will fire the first matching rule. An event is retracted after it matches.
   * - retract_fact
     - Retract a fact from the rule set, will fire all matching rules that checks for the missing fact.
   * - print_event
     - Print the matching event to stdout
   * - debug
     - Log the matching event
   * - none
     - No operation

run_playbook
************
.. list-table:: Run a playbook
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name of the playbook, using the FQCN (fully qualified collection name)
     - Yes
   * - assert_facts
     - The artifacts from the playbook execution are inserted back into the rule set as facts
     - No
   * - post_events
     - The artifacts from the playbook execution are inserted back into the rule set as events
     - No
   * - ruleset
     - The name of the ruleset to post the event or assert the fact to, default is current rule set.
     - No
   * - retry
     - If the playbook fails execution, retry it, boolean value true|false
     - No
   * - retries
     - If the playbook fails execution, the number of times to retry it. An integer value
     - No
   * - delay
     - The retry interval, an integer value
     - No
   * - verbosity
     - Verbosity level when running the playbook, a value between 1-4
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No
   * - * (any other args)
     - These will be passed to the playbook
     - No

run_module
**********
.. list-table:: Run an Ansible module
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name of the module, using the FQCN (fully qualified collection name)
     - Yes
   * - module_args
     - The arguments to pass into the Ansible Module
     - No
   * - verbosity
     - Verbosity level when running the module, a value between 1-4
     - No

post_event
**********
.. list-table::  Post an event to a running rule set in the rules engine
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - event
     - The event dictionary to post
     - Yes
   * - ruleset
     - The name of the rule set to post the event, default is the current rule set name
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No

Example::

      action:
        post_event:
          ruleset: Test rules4
          event:
            j: 4

assert_fact
***********
.. list-table:: Post a fact to the running rule set in the rules engine
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - fact
     - The fact dictionary to post
     - Yes
   * - ruleset
     - The name of the rule set to post the fact, default is the current rule set name
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No

Example::

    action:
        assert_fact:
          ruleset: Test rules4
          fact:
            j: 1

retract_fact
************
.. list-table:: Remove a fact from the running rule set in the rules engine
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - fact
     - The fact dictionary to remove
     - Yes
   * - ruleset
     - The name of the rule set to retract the fact, default is the current rule set name
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No

Example::

      action:
        retract_fact:
          ruleset: Test rules4
          fact:
            j: 3

print_event
***********
.. list-table:: Write the event to stdout
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - pretty
     - A boolean value to pretty print
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No

Example::
    
    action:
      print_event:
        pretty: true
        var_root: i

Example with multiple event match::

    name: Multiple events with var_root
      condition:
        all:
          - events.webhook << event.webhook.payload.url == "http://www.example.com"
          - events.kafka << event.kafka.message.channel == "red"
      action:
        print_event:
          var_root:
            webhook.payload: webhook
            kafka.message: kafka

debug
*****
  Write the event to stdout
  No arguments needed

none
****
  No action, useful when writing tests
  No arguments needed


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
