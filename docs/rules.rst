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
 * Previously saved events within the rule
 * Longer term facts about the system
 * Variables provided by the user at startup saved as facts

When writing conditions 
  * use the **event** prefix when accessing data from the current event
  * use the **fact** prefix when accessing data from the saved facts or passed in variables
  * use the **events** prefix when assigning variables and accessing data within the rule
  * use the **facts** prefix when assigning variables and accessing data within the rule


| A condition **cannot** contain Jinja style substitution when accessing variables passed in
| from the command line, we loose the data type information and the rule engine will not
| process the condition. Instead use the fact prefix to access the data passed in from the
| command line

The following is an example rule::

    name:  An automatic remediation rule
    condition:  event.outage == true
    action:
        run_playbook:
            name: remediate_outage.yml

| This rule searches for a recent event with the data `outage` being `true`. If an event
| with this condition is found then the `remediate_outage.yml` playbook is run.
| After an event is matched it is immediately removed and will not be used in subsequent
| rules.

A condition can contain
 * One condition
 * Multiple conditions where all of them have to match
 * Multiple conditions where any one of them has to match

**Examples**

Single condition
----------------
::

    name:  An automatic remediation rule
    condition:  event.outage == true
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

| As we receive events from the source plugins we send them to the appropriate 
| rule set sessions running in the rule engine.
| With multiple conditions the rule engine will keep track of the conditions that
| have matched and wait for the next event to come in which might match other conditions.
| Once all the conditions have been met, it will return you all the events that matched,
| which can be used in action.

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

Condition with fact and event, fact being passed in via --variables on command line
-----------------------------------------------------------------------------------
::

      name: Condition using a passed in variable and an event
      condition: event.i == fact.custom.expected_index
      action:
        debug:

In the above example the custom.expected_index was passed in via --variables from the
command line to ansible-rulebook.

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
| it is stored in well known attribute(s) called **m**, **m_1**, **m_2**.....
| You can optionally alias these attribute(s) using the **<<** operator e.g

Multiple conditions with assignment
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
| In the third condition we are accessing the saved event in events.first to do 
| a comparison. **events** and **facts** have rule scope and are not available
| outside of the rule. They can be used in assignments and accessing the saved
| values in a condition or in action.

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
| is ignored and the matching event is stored as **event**. Compare this to multiple
| condition rules where the matching events are stored as **events**




Actions
*******

When a rule matches the condition(s), it fires the corresponding action for the rule.
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
   * - set_fact
     - Set a fact for the rule set, will fire all matching rules different from post_event 
   * - post_event
     - Assert an event to the rule set, will fire the first matching rule. An event is retracted after it matches.
   * - retract_fact
     - Retract a fact from the rule set, will fire all matching rules that checks for the missing fact.
   * - print_event
     - Print the matching event to stdout
   * - shutdown
     - Generate a shutdown event
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
   * - set_facts
     - The artifacts from the playbook execution are inserted back into the rule set as facts
     - No
   * - post_events
     - The artifacts from the playbook execution are inserted back into the rule set as events
     - No
   * - ruleset
     - The name of the ruleset to post the event or assert the fact to, default is current rule set.
     - No
   * - retry
     - If the playbook fails execution, retry it once, boolean value true|false
     - No
   * - retries
     - If the playbook fails execution, the number of times to retry it. An integer value
     - No
   * - delay
     - The retry interval, an integer value specified in seconds
     - No
   * - verbosity
     - Verbosity level when running the playbook, a value between 1-4
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No
   * - `*` (any other args)
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
   * - retry
     - If the module fails execution, retry it once, boolean value true|false. Default false
     - No
   * - retries
     - If the module fails execution, the number of times to retry it. Integer value, default 0
     - No
   * - delay
     - The retry interval, an integer value
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

Example::

      action:
        post_event:
          ruleset: Test rules4
          event:
            j: 4

Example, using data saved with assignment
::

      name: multiple conditions
      condition:
        all:
          - events.first << event.i == 0
          - events.second << event.i == 1
          - events.third << event.i == events.first.i + 2 
      action:
        post_event:
          ruleset: Test rules4
          event:
            data: "{{events.third}}"


| The events and facts prefixes have rule scope and cannot be accessed outside of
| rules. Please note the use of Jinja substitution when accessing the event results.

set_fact
********
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

Example
::

    action:
        set_fact:
          ruleset: Test rules4
          fact:
            j: 1

Example, using data saved with assignment in multiple condition
::

      name: multiple conditions
      condition:
        all:
          - events.first << event.i == 0
          - events.second << event.i == 1
          - events.third << event.i == events.first.i + 2 
      action:
        set_fact:
          ruleset: Test rules4
          fact:
            data: "{{events.first}}"

Example, using data saved with single condition
::

      name: single condition
      condition: event.i == 23
      action:
        set_fact:
          fact:
            myfact: "{{event.i}}"

| A rulebook can have multiple rule sets, the set_fact/retract_fact/post_event allow you
| to target different rule sets within the rulebook. You currently cannot assert an event to
| multiple rule sets, it can be asserted to a single rule set. The default being the current
| rule set. Please note the use of Jinja substitution in the above examples  when accessing 
| the event results in an action.

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


shutdown
********

| Generate a shutdown event which will terminate the rulebook engine. If there are multiple
| If there are multiple rule-sets running in your rule book, issuing a shutdown will cause
| all other rule-sets to end, care needs to be taken to account for running playbooks which
| can be impacted when one of the rule set decides to shutdown.

Example::

   name: shutdown after 5 events
   condition: event.i >= 5
   action:
      shutdown:

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

Supported Operators
*******************

The conditions use a subset of Jinja syntax, the following operators are
currently supported

.. list-table:: Operators
   :widths: 25 150
   :header-rows: 1

   * - Name
     - Description
   * - ==
     - The equality operator for strings and numbers
   * - !=
     - The non equality operator for strings and numbers
   * - >
     - The greater than operator for numbers
   * - <
     - The less than operator for numbers
   * - >=
     - The greater than equal to operator for numbers
   * - <=
     - The less than equal to operator for numbers
   * - `+`
     - The addition operator for numbers
   * - `-`
     - The subtraction operator for numbers
   * - `*`
     - The multiplication operator for numbers
   * - and
     - The conjunctive add, for making compound expressions
   * - or
     - The disjunctive or
   * - is defined
     - To check if a variable is defined
   * - is not defined
     - To check if a variable is not defined
   * - `<<`
     - Assignment operator, to save the matching events or facts with events or facts prefix

FAQ
***

| **Q:** In a multiple condition scenario when 1 event matches and the rest of the events don't match
| how long does the Rule engine keep the previous event around?

| **Ans:** Currently there is no time limit on how long the rule engine keeps the matched event.
| Once they match they are retracted.

| **Q:** When does the Ansible rulebook stop processing?

| **Ans:** When a Shutdown event is generated from the source plugin, or shutdown action is invoked.

| **Q:** Will a condition be evaluated if a variable is missing?

| **Ans:** If a condition refers to an object.attribute which doesn't exist then that condition
| is skipped and not processed.

Example::

   name: send to debug
   condition: event.payload.eventType != 'GET'
   action:
        debug:


   In the above case if any of the event.payload.eventType is undefined the condition is
   ignored and doesn't match anything.

| **Q:** When a rule book has multiple rule sets and one of them shuts down are all rule sets terminated?

| **Ans:** Yes, so care should be taken if there are any playbooks running in the other rule sets

| **Q:** How do I check if an attribute in an object referred in a condition exists?

| **Ans:** Use the is defined

Example::

      name: rule1
      condition: event.msg is defined
      action:
        retract_fact:
          fact:
            msg: "{{event.msg}}"

| **Q:** How do I check if an attribute in an object referred in a condition does not exist?

| **Ans:** Use the is not defined

Example::

      name: rule2
      condition: fact.msg is not defined
      action:
        set_fact:
          fact:
            msg: Hello World
