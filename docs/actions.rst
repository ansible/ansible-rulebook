=======
Actions
=======

When a rule matches the condition(s), it fires the corresponding action for the rule.
The following actions are supported:

- `run_playbook`_
- `run_module`_
- `run_job_template`_
- `run_workflow_template`_
- `set_fact`_
- `post_event`_
- `retract_fact`_
- `print_event`_
- `shutdown`_
- `debug`_
- `none`_

run_playbook
************
Run an Ansible playbook.

.. list-table:: Run a playbook
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - | The name of the playbook, using the FQCN (fully qualified collection name), or an absolute path or a relative path.
       | If it's a relative path, it must be relative to the current working dir where the ansible-rulebook command is executed.
     - Yes
   * - set_facts
     - Boolean, the artifacts from the playbook execution are inserted back into the rule set as facts
     - No
   * - post_events
     - Boolean, the artifacts from the playbook execution are inserted back into the rule set as events
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
   * - extra_vars
     - Additional vars to be passed into the playbook as extra vars.
     - No
   * - json_mode
     - Boolean, sends the playbook events data to the stdout as json strings as they are processed by ansible-runner
     - No
   * - copy_files
     - Boolean, copy the local playbook file to the ansible-runner project directory, this is not needed if you are running a playbook from an ansible collection.
     - No


run_module
**********
Run an Ansible module

.. list-table::
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
   * - extra_vars
     - Additional vars to be passed into the playbook as extra vars.
     - No
   * - json_mode
     - Boolean, sends the playbook events data to the stdout as json strings as they are processed by ansible-runner
     - No
   * - set_facts
     - Boolean, the artifacts from the module execution are inserted back into the rule set as facts
     - No
   * - post_events
     - Boolean, the artifacts from the module execution are inserted back into the rule set as events
     - No
   * - ruleset
     - The name of the ruleset to post the event or assert the fact to, default is current rule set.
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No

run_job_template
****************

Run a job template.

.. note::
    ``--controller-url`` and either ``--controller-token`` or ``--controller-username`` and ``--controller-password`` cmd options must be provided to use this action

    In order to access event information under the ``ansible_eda`` namespace, be sure to check the box for "Prompt on launch" for the Variables field within the job template. Alternatively, a survey can be created that includes the variable ``ansible_eda``. Similarly, if you plan to limit host execution based on event information, enable "Prompt on launch" for the Limit field within the job template.

.. note::
    You can define the environment variable ``EDA_CONTROLLER_CONNECTION_LIMIT`` to limit the number of concurrent connections to the controller. The default is 30.


.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name of the job template
     - Yes
   * - organization
     - The name of the organization
     - Yes
   * - set_facts
     - The artifacts from the job template execution are inserted back into the rule set as facts
     - No
   * - post_events
     - The artifacts from the job template execution are inserted back into the rule set as events
     - No
   * - ruleset
     - The name of the ruleset to post the event or assert the fact to, default is current rule set.
     - No
   * - retry
     - If the job template fails execution, retry it once, boolean value true|false
     - No
   * - retries
     - If the job template fails execution, the number of times to retry it. An integer value
     - No
   * - delay
     - The retry interval, an integer value specified in seconds
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No
   * - job_args
     - Additional arguments sent to the job template launch API. Any answers to the survey and other extra vars should be set in nested key extra_vars. Event(s) and fact(s) will be automatically included in extra_vars too.
     - No

run_workflow_template
*********************

Run a workflow template.

.. note::
    ``--controller-url`` and either ``--controller-token`` or ``--controller-username`` and ``--controller-password`` cmd options must be provided to use this action

.. note::
    You can define the environment variable ``EDA_CONTROLLER_CONNECTION_LIMIT`` to limit the number of concurrent connections to the controller. The default is 30.


.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name of the workflow template
     - Yes
   * - organization
     - The name of the organization
     - Yes
   * - set_facts
     - The artifacts from the workflow template execution are inserted back into the rule set as facts
     - No
   * - post_events
     - The artifacts from the workflow template execution are inserted back into the rule set as events
     - No
   * - ruleset
     - The name of the ruleset to post the event or assert the fact to, default is current rule set.
     - No
   * - retry
     - If the workflow template fails execution, retry it once, boolean value true|false
     - No
   * - retries
     - If the workflow template fails execution, the number of times to retry it. An integer value
     - No
   * - delay
     - The retry interval, an integer value specified in seconds
     - No
   * - var_root
     - If the event is a deeply nested dictionary, the var_root can specify the key name whose value should replace the matching event value. The var_root can take a dictionary to account for data when we have multiple matching events.
     - No
   * - job_args
     - Additional arguments sent to the workflow template launch API. Any answers to the survey and other extra vars should be set in nested key extra_vars. Event(s) and fact(s) will be automatically included in extra_vars too.
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

Example:

.. code-block:: yaml

      action:
        post_event:
          ruleset: Test rules4
          event:
            j: 4

Example, using data saved with assignment:

.. code-block:: yaml

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

Example:

.. code-block:: yaml

    action:
        set_fact:
          ruleset: Test rules4
          fact:
            j: 1

Example, using data saved with assignment in multiple condition:

.. code-block:: yaml

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

Example, using data saved with single condition:

.. code-block:: yaml

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
   * - partial
     - The fact being requested to retracted is partial and doesn't have all the keys. Default is true
     - No

Example:

.. code-block:: yaml

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

Example:

.. code-block:: yaml

    action:
      print_event:
        pretty: true
        var_root: i

Example with multiple event match:

.. code-block:: yaml

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
.. list-table:: Shutdown ansible-rulebook
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - delay
     - A numeric value about how long to wait in seconds before shutting down, default 60.0
     - No
   * - message
     - A message to be associated with this shutdown
     - No
   * - kind
     - Kind of shutdown can be either **graceful** or **now**. default is graceful.
     - No

| Generate a shutdown event which will terminate the ansible-rulebook process.
| If there are multiple rule-sets running in your rule book, issuing a shutdown will cause
| all other rule-sets to end, care needs to be taken to account for running playbooks which
| can be impacted when one of the rule set decides to shutdown. A shutdown message is
| broadcast to all running rule-sets.

Example:

    .. code-block:: yaml

       name: shutdown after 5 events
       condition: event.i >= 5
       action:
          shutdown:
            delay: 0.125
            message: Shutting down after 5 events

Results
*******

When a rule's condition(s) are satisfied we get the results back as:
  * events/facts for multiple conditions
  * event/fact if a single condition

| This data is made available to your playbook as extra_vars when its invoked.
| In all the examples below you would see that facts/fact is an exact copy of events/event respectively
| and you can use either one of them in your playbook.

debug
*****
.. list-table:: debug ansible-rulebook
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - msg
     - A simple string or an array of strings, which can have references to event or events
     - No
   * - var
     - The variable to print, which can have references to event or events. Using {{ }} is optional.
     - No

| The debug action tries to mimic the debug command in ansible.
| If no arguments are provided it prints the matching events along with other important properties
| **msg** and **var** are mutually exclusive, you can have only 1 of them in the debug
| msg can be a single string or an array of strings, with references to event or events.
| With var using the Jinja style braces is optional like shown in the example below

Example:

    .. code-block:: yaml

       name: debug with single message
       condition: event.i >= 5
       action:
          debug:
            msg: Simple debug message


    .. code-block:: yaml

       name: debug with multiple messages
       condition: event.i >= 5
       action:
          debug:
            msg:
               - "Message 1 {{ event }}"
               - Second Message

    .. code-block:: yaml

       name: debug with var
       condition: event.i >= 5
       action:
          debug:
            var: event.i


none
****
  No action, useful when writing tests
  No arguments needed
