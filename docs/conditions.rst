==========
Conditions
==========

In event driven automation a condition determines if a rule fires (runs its action).  Conditions
are written in format that is similar to the conditionals format in `Ansible playbooks`_::

    event.status == "enabled"


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


Conditions support the following operators:

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


**Examples**
************

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




.. _Ansible playbooks: https://docs.ansible.com/ansible/latest/user_guide/playbooks_conditionals.html


..


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
