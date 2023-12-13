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

Supported data types
********************
The data type is of great importance for the rules engine. The following types are supported

* integers
* strings
* booleans
* floats (dot notation and scientific notation)
* null

Navigate structured data
************************

You can navigate strutured event, fact, var data objects using either dot notation or bracket notation:

    .. code-block:: yaml

      rules:
        - name: Using dot notation
          condition: event.something.nested == true
          action:
            debug:
        - name: Analogous, but using bracket notation
          condition: event.something["nested"] == true
          action:
            debug:

Both of the above examples checks for the same value (attribute "nested" inside of "something") to be equal to `true`.

Bracket notation might be preferable to dot notation when the structured data contains a key using symbols
or other special characters:

    .. code-block:: yaml

      name: Looking for specific metadata
      condition: event.resource.metadata.labels["app.kubernetes.io/name"] == "hello-pvdf"
      action:
        debug:

You can find more information about dot notation and bracket notation also in the Ansible playbook `manual <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html#referencing-key-value-dictionary-variables>`_.

You can access list in strutured event, fact, var data objects using bracket notation too.
The first item in a list is item 0, the second item is item 1.
Like Python, you can access the `n`-to-last item in the list by supplying a negative index.
For example:

    .. code-block:: yaml

      rules:
        - name: Looking for the first item in the list
          condition: event.letters[0] == "a"
          action:
            debug:
        - name: Looking for the last item in the list
          condition: event.letters[-1] == "z"
          action:
            debug:

You can find more information the bracket notation for list also in the Ansible playbook `manual <https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html#referencing-list-variables>`_.

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
   * - in
     - To check if a value in the left hand side exists in the list on the right hand side
   * - not in
     - To check if a value in the left hand side does not exist in the list on the right hand side
   * - contains
     - To check if the list on the left hand side contains the value on the right hand side
   * - not contains
     - To check if the list on the left hand side does not contain the value on the right hand side
   * - is defined
     - To check if a variable is defined
   * - is not defined
     - To check if a variable is not defined, please see caveats listed below
   * - is match(pattern,ignorecase=true)
     - To check if the pattern exists in the beginning of the string. Regex supported
   * - is not match(pattern,ignorecase=true)
     - To check if the pattern does not exist in the beginning of the string. Regex supported
   * - is search(pattern,ignorecase=true)
     - To check if the pattern exists anywhere in the string. Regex supported
   * - is not search(pattern,ignorecase=true)
     - To check if the pattern does not exist anywhere in the string. Regex supported
   * - is regex(pattern,ignorecase=true)
     - To check if the regular expression pattern exists in the string
   * - is not regex(pattern,ignorecase=true)
     - To check if the regular expression pattern does not exist in the string
   * - is select(operator, value)
     - To check if an item exists in the list, that satisfies the test defined by operator and value
   * - is not select(operator, value)
     - To check if an item does not exist in the list, that does not satisfy the test defined by operator and value
   * - is selectattr(key, operator, value)
     - To check if an object exists in the list, that satisfies the test defined by key, operator and value
   * - is not selectattr(key, operator, value)
     - To check if an object does not exist in the list, that does not satisfy the test defined by key, operator and value
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

Single boolean
--------------

    .. code-block:: yaml

        name: An automatic remediation rule
        condition: event.outage
        action:
          run_playbook:
            name: remediate_outage.yml

If the ``outage`` attribute is a boolean, you can use it
by itself in the condition. This is a shorter version of
the previous example. If the value is true the condition
passes and the action is triggered.

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

    .. warning::
        Note that in this case the engine will consider **all the different events** until the conditions are met,
        regardless of whether those events come from one or multiple sources.
        Multiple conditions with ``all`` are not equivalent to a single condition with the ``and`` operator.

        If you want to match only one event using multiple attributes
        the rule must use a single condition with the ``and`` operator:

        .. code-block:: yaml

            name: One condition combining attributes
            condition: event.target_os == "linux" and event.tracking_id == 345
            action:
              debug:


Multiple conditions where **all** of them have to match with internal references
--------------------------------------------------------------------------------

| If a rule has multiple conditions with **all** all of the conditions have to match.
| You can safely make references to matching event payloads from the other conditions
| in the same rule. If the other events have not arrived, the rule engine will cache the
| events and re-evaluate them as a whole set when the new event arrives.


   .. code-block:: yaml

      ---
      - name: Delayed comparison
        hosts: all
        sources:
        - ansible.eda.generic:
            payload:
              - friend_list:
                  names:
                     - fred
                     - barney
              - request:
                  type: Delete
                  friend_name: fred
        rules:
          - name: r1
            condition:
              all:
                - event.request.type == "Delete"
                - event.friend_list.names is select("search",  events.m_0.request.friend_name)
            action:
              print_event:
                pretty: true



| The above example uses the generic source plugin which allows for the event
| payloads to be defined in the rule book for easy testing.
| In this example the event.request.type Delete is the second event that is injected
| into the system. The first event that comes in is the event.friends_list and when it is
| evaluated the events.m_0.request.friend_name which comes from the second event is not
| defined. The rule engine will hold this event in cache and when the second event comes
| in, the event.request.type == "Delete" matches and then the first event which is cached
| is re-evaluated.


| Another key point is that if multiple events match, the partial matches are stored
| till the whole set matches and the actions will be executed with the proper set
| of matching events.

   .. code-block:: yaml

      ---
      - name: multiple conditions caching
        hosts: all
        sources:
          - ansible.eda.generic:
              payload:
                - request:
                    type: Delete
                    friend_name: fred
                - request:
                    type: Delete
                    friend_name: wilma
                - friend_list:
                    names:
                       - fred
                       - barney
                - friend_list:
                    names:
                       - betty
                       - wilma
        rules:
          - name: r1
            condition:
              all:
                - event.request.type == "Delete"
                - event.friend_list.names contains events.m_0.request.friend_name
            action:
              print_event:

| The above example uses the generic source plugin which allows for the event
| payloads to be defined in the rule book for easy testing.
| In this example the first condition matches for the first 2 events
| this leads to 2 partial matching rules, then the 3rd and 4th events arrive
| with the friend_list payload and they match the 2nd condition. This will lead
| to the rule being satisfied twice and the print_event will run twice with the
| correct events.


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
        Note that in this case the engine will consider **all the different events** until one of them meets one of the conditions,
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

| In the above example the custom.expected_index was set using the set_fact action in
| the running of the rulebook. You cannot compare a fact and event directly in the same
| condition. First the fact has to be assigned to a local variable, **facts.first** in the
| above example and then that local variable can be compared with event.i. When you use a
| fact and event it would always have to be in the context of multiple conditions using **all**.
| `Differences between facts and events <events_and_facts.html>`_


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

| In the above example the person.year and person.age was passed in a variables file via
| ``--vars`` from the command line to ansible-rulebook. The usage of vars allows us to
| preserve the data type.  Environment variable values are always treated as strings and
| you would have to do the type conversion in the playbook or job template.

    .. code-block:: yaml

        name: Single condition comparing vars and event
        condition: event.name == vars.name
        action:
          debug:

| Vars can be used in single condition rules, like above because vars are resolved when
| the ruleset is loaded before being passed into the rule engine. If the vars is missing
| ansible-rulebook reports an error.

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
            msg:
              - "first: {{ events.first }}"
              - "second: {{ events.second }}"
              - "third: {{ events.third }}"

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
            msg:
              - "first: {{ events.m_0 }}"
              - "second: {{ events.m_1 }}"
              - "third: {{ events.m_2 }}"

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
            msg:
              - "first: {{ events.m_0 }}"
              - "second: {{ events.m_1 }}"
              - "third: {{ events.m_2 }}"

The first match is stored as **m**, and the subsequent ones are stored as **m_1**, **m_2** ...

Single condition assignment (Not supported)
-------------------------------------------

    .. code-block:: yaml

        name: assignment ignored
        condition: event.first << event.i == 0
        action:
          debug:
            msg:
              - "event: {{event}}"

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
    ``not`` operator can work without parenthesis when the value is a single logical statement

    If there are multiple logical statements with **or** or **and** please use round brackets like shown above.


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
| The timer for the rule starts when any one of the conditions match. This timeout field overrides
| any default_events_ttl that you have set at the ruleset level.


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

String search
-------------

    .. code-block:: yaml

        name: string search example
        condition: event.url is search("example.com", ignorecase=true)
        action:
          print_event:

| To search for a pattern anywhere in the string. In the above example we check if
| the event.url has "example.com" anywhere in its value. The option controls that this
| is a case insensitive search

    .. code-block:: yaml

        name: string not search example
        condition: event.url is not search("example.com", ignorecase=true)
        action:
          print_event:

| In the above example we check if the event.url does not have "example.com" anywhere in its value
| And the option controls that this is a case insensitive search.

String match
------------

    .. code-block:: yaml

        name: string match example
        condition: event.url is match("http://www.example.com", ignorecase=true)
        action:
          print_event:

| To search for a pattern in the beginning of string. In the above example we check if
| the event.url has "http://www.example.com" in the beginning. The option controls that this
| is a case insensitive search

    .. code-block:: yaml

        name: string not search example
        condition: event.url is not match("http://www.example.com", ignorecase=true)
        action:
          print_event:

| In the above example we check if the event.url does not have "http://www.example.com" in the beginning
| And the option controls that this is a case insensitive search.

String regular expression
-------------------------

    .. code-block:: yaml

        name: string regex example
        condition: event.url is regex("example\.com", ignorecase=true)
        action:
          print_event:

| To search for a regex pattern in the string. In the above example we check if
| the event.url has "example.com" in its value. The option controls that this
| is a case insensitive search

    .. code-block:: yaml

        name: string not regex example
        condition: event.url is not regex("example\.com", ignorecase=true)
        action:
          print_event:

| In the above example we check if the event.url does not have "example.com" in its value
| And the option controls that this is a case insensitive search.


Check if an item exists in a list
---------------------------------

| The following examples show how to use `in` `not in` `contains` and `not contains` operators to check if an item exists in a list

    .. code-block:: yaml
        # variables file
        expected_levels:
          - "WARNING"
          - "ERROR"

    .. code-block:: yaml

        name: check if an item exist in a list
        condition: event.level in vars.expected_levels
        action:
          debug:
            msg: matched!

    .. code-block:: yaml

        name: check if an item does no exist in a list
        condition: event.level not in ["INFO", "DEBUG"]
        action:
          debug:
            msg: matched!

    .. code-block:: yaml

        name: check if a list contains an item
        condition: event.affected_hosts contains "host1"
        action:
          debug:
            msg: matched!

    .. code-block:: yaml

        name: check if a list does not contain an item
        condition: vars.expected_levels not contains "INFO"
        action:
          debug:
            msg: This will match always for every event because INFO is not in the list!



Check if an item exists in a list based on a test
-------------------------------------------------

    .. code-block:: yaml

        name: check if an item exist in list
        condition: event.levels is select('>=', 10)
        action:
          debug:
            msg: The list has an item with the value greater than or equal to 10

| In the above example "levels" is a list of integers e.g. [1,2,3,20], the test says
| check if any item exists in the list with a value >= 10. This test passes because
| of the presence of 20 in the list. If the value of "levels" is [1,2,3] then the
| test would yield False.

Check if an item does not exist in a list based on a test
---------------------------------------------------------

    .. code-block:: yaml

        name: check if an item does not exist in list
        condition: event.levels is not select('>=', 10)
        action:
          debug:
            msg: The list does not have item with the value greater than or equal to 10

| In the above example "levels" is a list of integers e.g. [1,2,3], the test says
| check if *no* item exists with a value >= 10. This test passes because none of the items
| in the list is greater than or equal to 10. If the value of "levels" is [1,2,3,20] then
| the test would yield False because of the presence of 20 in the list.

| The result of the *select* condition is either True or False. It doesn't return the item or items.
| The select takes 2 arguments which are comma delimited, **operator** and **value**.
| The different operators we support are >,>=,<,<=,==,!=,match,search,regex
| The value is based on the operator used, if the operator is regex then the value is a pattern.
| If the operator is one of >,>=,<,<= then the value is either an integer or a float

You can find more information for the *select* condition also in the Ansible playbook `manual <https://docs.ansible.com/ansible/latest/playbook_guide/complex_data_manipulation.html#loops-and-list-comprehensions>`_.

Checking if an object exists in a list based on a test
------------------------------------------------------

    .. code-block:: yaml

        name: check if an object exist in list
        condition: event.objects is selectattr('age', '>=', 20)
        action:
          debug:
            msg: An object with age greater than 20 found

| In the above example "objects" is a list of object's, with multiple properties. One of the
| properties is age, the test says check if any object exists in the list with an age >= 20.

Checking if an object does not exist in a list based on a test
---------------------------------------------------------------

    .. code-block:: yaml

        name: check if an object does not exist in list
        condition: event.objects is not selectattr('age', '>=', 20)
        action:
          debug:
            msg: No object with age greater than 20 found

| In the above example "objects" is a list of object's, with multiple properties. One of the
| properties is age, the test says check if *no* object exists in the list with an age >= 20.

| The result of the *selectattr* condition is either True or False. It doesn't return the
| matching object or objects.
| The *selectattr* takes 3 arguments which are comma delimited, **key**, **operator** and **value**.
| The key is a valid key name in the object.
| The different operators we support are >, >=, <, <=, ==, !=, match, search, regex, in, not in,
| contains, not contains.
| The value is based on the operator used, if the operator is regex then the value is a pattern.
| If the operator is one of >, >=, <, <= then the value is either an integer or a float.
| If the operator is in or not in then the value is list of integer, float or string.

You can find more information for the *selectattr* condition also in the Ansible playbook `manual <https://docs.ansible.com/ansible/latest/playbook_guide/complex_data_manipulation.html#loops-and-list-comprehensions>`_.


FAQ
***

| **Q:** In a multiple condition scenario when 1 event matches and the rest of the events don't match
| how long does the Rule engine keep the previous event around?

| **Ans:** The partially matched events are kept in memory based on the timeout defined at the rule level.
| If the rule doesn't have a timeout, we look at the ruleset attribute **default_events_ttl**, if that is
| missing we keep the events for 2 hours. The events are evicted once all conditions match or the timeout
| is reached.

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

| **Q:** What are the caveats of using **is not defined**?
| **Ans:** The is not defined should be used sparingly to
|          a. initialize a variable
|          b. immediately following a retract fact
| If a rule only has one condition with is not defined, then
| placement of this rule is important. If the rule is defined
| first in the rulebook it will get executed all the time till
| the variable gets defined this might lead to misleading results and
| skipping of other rules. You should typically combine the
| is not defined with another comparison. It's not important to check
| if an attribute exists before you use it in a condition. The rule engine
| will check for the existence and only then compare it. If its missing, the
| comparison fails.


| **Q:** If a condition string has an embedded colon followed by a space in it how do I escape it?

| **Ans:** During the rulebook parsing you would see this error message:
| ERROR - Terminating mapping values are not allowed here.
| To resove this eror you would have to quote the whole condition string or use the > or | and
| move the entire condition to a separate line.

Example:
    .. code-block:: yaml

      name: rule1
      condition: 'event.abc == "test: 1"'


    .. code-block:: yaml

      name: rule1
      condition: >
        event.abc == "test: 1"

    .. code-block:: yaml

      name: rule1
      condition: |
        event.abc == "test: 1"
