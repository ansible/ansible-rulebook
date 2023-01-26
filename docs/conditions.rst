==========
Conditions
==========

In event driven automation a condition determines if a rule fires (runs its action).

Example:

    .. code-block:: yaml

        condition: event.status == "enabled"


Each of the condition(s) can use information from
 * Event received
 * Previously saved events within the rule
 * Longer term facts about the system
 * Variables provided by the user at startup saved as vars

When writing conditions
  * use the **event** prefix when accessing data from the current event
  * use the **fact** prefix when accessing data from the set_facts actions in the rulebook
  * use the **events** prefix when assigning variables and accessing data within the rule
  * use the **facts** prefix when assigning variables and accessing data within the rule
  * use the **vars** prefix when accessing variables passed in via --vars and --env-vars


.. note::
    A condition **cannot** contain Jinja style substitution when accessing variables passed in
    from the command line, we loose the data type information and the rule engine will not
    process the condition. Instead use the vars prefix to `access the data passed <#condition-with-vars-and-event>`_ in from the
    command line


A condition can contain
 * One condition
 * Multiple conditions where all of them have to match
 * Multiple conditions where any one of them has to match
 * Multiple conditions where not all one of them have to match

Supported datatypes
*******************
The data type is of great importance for the rules engine. The following types are supported

* integers
* strings
* booleans
* floats (dot notation and scientific notation)

Supported Operators
*******************

Conditions support the following operators:

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
   * - not
     - Negation operator, to negate boolean expression


Examples
********

Single condition
----------------

    .. code-block:: yaml

        name: An automatic remediation rule
        condition: event.outage == true
        action:
          run_playbook:
            name: remediate_outage.yml

When an event comes with ``outage`` attribute as true, the specified playbook is executed.

Multiple conditions where **all** of them have to match
-------------------------------------------------------

    .. code-block:: yaml

        name: All conditions must match
        condition:
          all:
            - event.target_os == "linux"
            - event.tracking_id == 345
        action:
          debug:

As we receive events from the source plugins we send them to the appropriate
rule set sessions running in the rule engine.
With multiple conditions the rule engine will keep track of the conditions that
have matched and wait for the next event to come in which might match other conditions.
Once all the conditions have been met, it will return you all the events that matched,
which can be used in action.

    .. note::
        Note that this case the engine will consider **all the different events** until meet the conditions,
        regardless of whether those events come from one or multiple sources.
        Multiple conditions with ``all`` are not equivalent to a single condition with the ``and`` operator.

        If you want to match only one event using multiple attributes
        the rule must use a single condition with the ``and`` operator:

    .. code-block:: yaml

        name: One condition combining attributes
        condition: event.target_os == "linux" and event.tracking_id == 345
        action:
          debug:


Multiple conditions where **any** one of them has to match
----------------------------------------------------------

    .. code-block:: yaml

        name: Any condition can match
        condition:
          any:
            - event.target_os == "linux"
            - event.target_os == "windows"
        action:
          debug:

    .. note::
        Note that this case the engine will consider **all the different events** until meet the conditions,
        regardless of whether those events come from one or multiple sources.
        Multiple conditions with ``any`` are not equivalent to a single condition with the ``or`` operator.

        If you want to match only one event using multiple attributes
        the rule must use a single condition with the ``or`` operator:

    .. code-block:: yaml

        name: One condition combining attributes
        condition: event.target_os == "linux" or event.target_os == "windows"
        action:
          debug:


Multiple conditions with facts and events and **all** of one of them have to match
----------------------------------------------------------------------------------

    .. code-block:: yaml

        name: Condition using both a fact and an event
        condition:
          all:
            - fact.meta.hosts == "localhost"
            - event.target_os == "windows"
        action:
          debug:

Condition with fact and event
-----------------------------

    .. code-block:: yaml

        name: Condition using a set_fact fact and an event
        condition:
          all:
            - facts.first << fact.custom.expected_index is defined
            - event.i == facts.first.custom.expected_index
        action:
          debug:

In the above example the custom.expected_index was set using the set_fact action in the running of the rulebook


Condition with vars and event
-----------------------------

    .. code-block:: yaml

        name: Condition using a passed in variable and an event
        condition:
          all:
            - event.year == vars.person.year
            - event.age == vars.person.age
        action:
          debug:

In the above example the person.year and person.age was passed in a variables file via ``--vars`` from the
command line to ansible-rulebook.

| When evaluating a single event you can compare multiple
| properties/attributes from the event using **and** or **or**

Logical and
-----------
    .. code-block:: yaml

        name: Multiple Attribute match from a single event
        condition: event.target_os == "linux" and event.version == "1.1"
        action:
          debug:

Logical or
----------

    .. code-block:: yaml

        name: Match any one attribute from a single event
        condition: event.version == "2.0" or event.version == "1.1"
        action:
          debug:

| The "and" and "or" keywords are case sensitive. You can't use
| "AND" or "OR" for the logical operators.



Combining logical operators
---------------------------

You can combine multiple ``and`` operators:

    .. code-block:: yaml

        name: Combining and operators
        condition: event.version == "2.0" and event.name == "example" and event.alert_count > 10
        action:
          debug:


If you combine ``and`` and ``or`` operators they must be enclosed in parenthesis:


    .. code-block:: yaml

        name: Combining and -and- or operators
        condition: ((event.i > 100 and event.i < 200) or (event.i > 500 and event.i < 600))
        action:
          debug:


    .. code-block:: yaml

        name: Combining and -and- or operators
        condition: (event.i > 100 and event.i < 200) or event.i > 1000
        action:
          debug:


Multiple conditions with assignment
-----------------------------------

When a condition is evaluated if the condition passes the matching event
it is stored in well known attribute(s) called **m_0**, **m_1**, **m_2**.....
You can optionally alias these attribute(s) using the **<<** operator. For example:

    .. code-block:: yaml

        name: multiple conditions
        condition:
          all:
            - events.first << event.i == 0
            - events.second << event.i == 1
            - events.third << event.i == events.first.i + 2
        action:
          debug:
            first: "{{ events.first }}"
            second: "{{ events.second }}"
            third: "{{ events.third }}"

| When using the assignment operator the attribute names should have the
| **events.** or **facts.** prefix. In the above example we are saving the
| matching events per condition as events.first, events.second and events.third.
| In the third condition we are accessing the saved event in events.first to do
| a comparison. **events** and **facts** have rule scope and are not available
| outside of the rule. They can be used in assignments and accessing the saved
| values in a condition or in action.
| The above example using default assignments

    .. code-block:: yaml

        name: multiple conditions using default assignments
        condition:
          all:
            - event.i == 0
            - event.i == 1
            - event.i == events.m_0.i + 2
        action:
          debug:
            first: "{{ events.m_0 }}"
            second: "{{ events.m_1 }}"
            third: "{{ events.m_2 }}"

Multiple condition with default assignments
-------------------------------------------

    .. code-block:: yaml

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

    .. code-block:: yaml

        name: assignment ignored
        condition: event.first << event.i == 0
        action:
          debug:
            event: "{{event}}"

| Assignment **cannot** be used for rules that have a single condition, the
| matching event will always be called **event**. In the above example **event.first**
| is ignored and the matching event is stored as **event**. Compare this to multiple
| condition rules where the matching events are stored as **events**.


Negation Example
----------------

    .. code-block:: yaml

        name: negation
        condition: not (event.i > 50 or event.i < 10)
        action:
          print_event:

| In this example the boolean expression is evaluated first and then negated.

.. note::
    ``not`` operator can work without parenthesis when the value is a boolean, E.g ``condition: not event.disabled``

    In the rest of the cases the expression must be enclosed in parenthesis. E.g ``condition: not (event.i == 4)``


Adding time constraints for rules with multiple conditions
----------------------------------------------------------

    .. code-block:: yaml

        name: Condition with timeout
        condition:
          all:
            - event.x == 5
            - event.y == 99
          timeout: 10 seconds
        action:
          debug:

| In the above example the event.x and event.y are 2 separate events that would be
| processed at different times. The order of which event comes first is not guaranteed.
| When both conditions are met the action in the rule is triggered. The **timeout** attribute
| in a condition allows you to put time constraints on how long to wait for these multiple
| conditions to be satisfied.
| The timeout units are **milliseconds**, **seconds**, **minutes**, **hours**, **days**.
| If the conditions are not met within 10 seconds in the above example the rule will be skipped.
| The timer for the rule starts when any one of the conditions match.


Adding time constraints for rules when "not all" conditions matched
-------------------------------------------------------------------

    .. code-block:: yaml

        name: Not all conditions met with timeout
        condition:
          not_all:
            - event.msg == "Applying Maintenance"
            - event.msg == "Server Rebooted"
            - event.msg == "Application Restarted"
          timeout: 5 minutes
        action:
          run_playbook:
            name: notify_delays.yml

| In certain scenarios you might want to trigger an action only if **some** of
| the conditions (not_all) from a group of conditions are met. In the above example
| we are tracking 3 separate events, if they are all met everything is
| normal, but if we only have some of the conditions match within the time window then
| we have something abnormal in the environment and would like to trigger an action.
| In the above example it triggers a notify_delays playbook when not all conditions
| are met within the time window. The timer starts when one of the conditions match.
| The timeout units are **milliseconds**, **seconds**, **minutes**, **hours**, **days**.

Throttle actions to counter event storms: Reactive
--------------------------------------------------

    .. code-block:: yaml

        name: Throttle example reactive
        condition: event.code == "error"
        throttle:
           once_within: 5 minutes
           group_by_attributes:
              - event.meta.hosts
              - event.code
        action:
          run_playbook:
            name: notify_outage.yml

| When we have too many events within a short time span (event storm) and the condition
| matches, we would trigger the action multiple times within that time period.
| This will lead to the playbook running several times within that short time frame.
| You can throttle this behavior by specifying a time window using the **once_within**
| attribute under the **throttle** node for a rule. When the condition matches for the
| **first time** we trigger the action and then suppress further action till the
| time window expires.
| In the above example we would trigger the action as soon (reactive) as we see an
| event with the code attribute set to error. Then for the next 5 minutes we would
| suppress further actions. After the 5 minute window has expired we will run the
| action again if the condition matches.
| The **group_by_attributes** in the throttle node allows you to specify an array of
| attributes in the event payload which create unique events. In the above example
| we are using event.meta.hosts and event.code. If we got 2 separate events one that had
| event.code=warning and another one with event.code=error they would be treated as distinct
| events and each one would be handled separately triggering an action. Its mandatory
| to have **group_by_attributes**  specified when using the once_within option.
| The timeout units are **milliseconds**, **seconds**, **minutes**, **hours**, **days**.
| The once_within will only work with a single condition and doesn't support multiple conditions.
| The timer for the rule starts when any one of unique event matches the condition.
| The **once_within** provides event level granularity as opposed to **once_after** described below
| which provides a time window level granularity with multiple matching events.

Throttle actions to counter event storms: Passive
-------------------------------------------------

    .. code-block:: yaml

        name: Throttle example passive
        condition: event.code == "warning"
        throttle:
           once_after: 5 minutes
           group_by_attributes:
              - event.meta.hosts
              - event.code
        action:
          run_playbook:
            name: notify_outage.yml

| This is similar to the **once_within** described earlier. This is more of a passive
| approach, for situations where you don't want to react immediately like
| in the **once_within** case. With **once_after** you would wait,
| then collect all the unique events until the time window expires.
| Then at the end of 5 minutes in the above example trigger the action to run the
| playbook.
| The **group_by_attributes** in the throttle node allows you to specify an array of
| attributes in the event payload which create unique event pairs. In the above example
| we are using event.meta.hosts and event.code. If we get 2 separate events, one that had
| event.code=warning and another one with event.code=error, they would be treated as distinct
| events and would result in matching multiple events when the action is triggered.
| Its mandatory to have group_by_attributes specified when using the once_after option.
| One of the advantages of the **once_after** is that you can collect all the
| unique events that match the condition and trigger a single action based on multiple
| matching events, allowing you to combine host information.
| The timeout units are **milliseconds**, **seconds**, **minutes**, **hours**, **days**.
| The once_after will only work with a single condition and doesn't support multiple conditions.

| When evaluating a single event you can compare multiple
| properties/attributes from the event using **and** or **or**


FAQ
***

| **Q:** In a multiple condition scenario when 1 event matches and the rest of the events don't match
| how long does the Rule engine keep the previous event around?

| **Ans:** Currently there is no time limit on how long the rule engine keeps the matched event.
| Once they match they are retracted.

| **Q:** When does the Ansible rulebook stop processing?

| **Ans:** When a Shutdown event is generated from the source plugin, shutdown action is invoked or the process is killed.

| **Q:** Will a condition be evaluated if a variable is missing?

| **Ans:** If a condition refers to an object.attribute which doesn't exist then that condition
| is skipped and not processed.

Example:
    .. code-block:: yaml

        name: send to debug
        condition: event.payload.eventType != 'GET'
        action:
            debug:


In the above case if any of the event.payload.eventType is undefined the condition is
ignored and doesn't match anything.

| **Q:** When a rulebook has multiple rule sets and one of them shuts down are all rule sets terminated?

| **Ans:** Yes, so care should be taken if there are any playbooks running in the other rule sets

| **Q:** How do I check if an attribute in an object referred in a condition exists?

| **Ans:** Use the is defined

Example:
    .. code-block:: yaml

        name: rule1
        condition: event.msg is defined
        action:
          retract_fact:
            fact:
            msg: "{{event.msg}}"

| **Q:** How do I check if an attribute in an object referred in a condition does not exist?

| **Ans:** Use the is not defined

Example:
    .. code-block:: yaml

      name: rule2
      condition: fact.msg is not defined
      action:
        set_fact:
          fact:
            msg: Hello World
