=======
Actions
=======

When a rule matches the condition(s), it fires the corresponding action for the rule.

.. note::
    Actions can use Jinja filters to transform and manipulate data. See :doc:`jinja_filters` for
    details on available filters including regex_replace, basename, dirname, and normpath, as well
    as Python string methods. Note that Jinja filters cannot be used in conditions.

The following actions are supported:

- `run_playbook`_
- `run_module`_
- `run_job_template`_
- `run_workflow_template`_
- `run_ao_workflow`_
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
     - | Boolean, the artifacts from the playbook execution are inserted back into the rule set as facts. It is recommended
       | that the playbook should use the ansible.builtin.set_stats task to set this data.
     - No
   * - post_events
     - | Boolean, the artifacts from the playbook execution are inserted back into the rule set as events. It is recommended
       | that the playbook should use the ansible.builtin.set_stats task to set this data.
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
   * - lock
     - An optional string based lock ensures sequential execution of this action when execution strategy is set to parallel. It can also be a string field from the event payload. The locks are per ruleset, if a lock is in place all actions that use the same lock will wait till the earlier action has completed.
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
   * - lock
     - An optional string based lock ensures sequential execution of this action when execution strategy is set to parallel. It can also be a string field from the event payload. The locks are per ruleset, if a lock is in place all actions that use the same lock will wait till the earlier action has completed.
     - No
   * - labels
     - Optional list of strings as labels, which can be added to the job in the controller. Requires that Prompt on launch for Labels is enabled. If its not enabled the labels are ignored. ansible-rulebook will add a default label called "Activated by Event-Driven Ansible"
     - No

run_job_template
****************

Run a job template.

.. note::
    ``--controller-url`` and either ``--controller-token`` or ``--controller-username`` and ``--controller-password`` cmd options must be provided to use this action

    In order to access event information under the ``ansible_eda`` namespace, be sure to check the box for "Prompt on launch" for the Variables field within the job template. Alternatively, a survey can be created that includes the variable ``ansible_eda``. Similarly, if you plan to limit host execution based on event information, enable "Prompt on launch" for the Limit field within the job template.

.. note::
    You can define the environment variable ``EDA_CONTROLLER_CONNECTION_LIMIT`` to limit the number of concurrent connections to the controller. The default is 30.

.. note::
    The controller URL is the API end point, that ansible-rulebook will try to reach.
    If you have a path specified in your URL it should have the api embedded in it.
    If you have just provided a host and port but no path we will append api to the URL$
    for backward compatibility.

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
   * - include_events
     - Should we include the matching events in the payload sent to controller. Default is true
     - No
   * - set_facts
     - | The artifacts from the job template execution are inserted back into the rule set as facts. It is recommended
       | that the playbook inside the job template should use the ansible.builtin.set_stats task to set this data.
     - No
   * - post_events
     - | The artifacts from the job template execution are inserted back into the rule set as events. It is recommended
       | that the playbook inside the job template should use the ansible.builtin.set_stats task to set this data.
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
     - Additional arguments sent to the job template launch API. Any answers to the survey and other extra vars should be set in nested key extra_vars. Event(s) and fact(s) will be automatically included in extra_vars too. Optionally if the job_args includes an attribute called limit it can be used to over write the limit set from the event payload.
     - No
   * - lock
     - An optional string based lock ensures sequential execution of this action when execution strategy is set to parallel. It can also be a string field from the event payload. The locks are per ruleset, if a lock is in place all actions that use the same lock will wait till the earlier action has completed.
     - No
   * - labels
     - Optional list of strings as labels, which can be added to the job in the controller. Requires that Prompt on launch for Labels is enabled. If its not enabled the labels are ignored. ansible-rulebook will add a default label called "Activated by Event-Driven Ansible". If the label gets resolved as None or an empty string it will be dropped. If there are duplicate labels the duplicate ones will be removed. e.g {{ event.payload.my_label | default(None) }} if the attribute doesn't exist we will skip the label.
     - No
   * - add_event_uuid_label
     - A boolean field, when set to true can leverage the event.meta.uuid field as a label, you can establish clear traceability between triggering events and their resulting jobs.
     - No

run_workflow_template
*********************

Run a workflow template.

.. note::
    ``--controller-url`` and either ``--controller-token`` or ``--controller-username`` and ``--controller-password`` cmd options must be provided to use this action

.. note::
    You can define the environment variable ``EDA_CONTROLLER_CONNECTION_LIMIT`` to limit the number of concurrent connections to the controller. The default is 30.


.. note::
    The controller URL is the api end point, that ansible-rulebook will try to reach.
    If you have a path specified in your URL it should have the api embedded in it.
    If you have just provided a host and port but no path we will append api to the URL$
    for backward compatibility.

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
   * - include_events
     - Should we include the matching events in the payload sent to controller. Default is true. If your workflow template does not have Prompt on Launch for Extra Variables or a Survey spec, you will have to set this to false.
     - No
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
     - Additional arguments sent to the workflow template launch API. Any answers to the survey and other extra vars should be set in nested key extra_vars. Event(s) and fact(s) will be automatically included in extra_vars too. Optionally if the job_args includes an attribute called limit it can be used to over write the limit set from the event payload.
     - No
   * - lock
     - An optional string based lock ensures sequential execution of this action when execution strategy is set to parallel. It can also be a string field from the event payload. The locks are per ruleset, if a lock is in place all actions that use the same lock will wait till the earlier action has completed.
     - No
   * - labels
     - Optional list of strings as labels, which can be added to the job in the controller. Requires that Prompt on launch for Labels is enabled. If its not enabled the labels are ignored. ansible-rulebook will add a default label called "Activated by Event-Driven Ansible". If the label gets resolved as None or an empty string it will be dropped. If there are duplicate labels the duplicate ones will be removed. e.g {{ event.payload.my_label | default(None) }} if the attribute doesn't exist we will skip the label.
     - No
   * - add_event_uuid_label
     - A boolean field, when set to true can leverage the event.meta.uuid field as a label, you can establish clear traceability between triggering events and their resulting jobs.
     - No

run_ao_workflow
***************

Run an Automation Orchestrator (AO) workflow via webhook trigger.

.. note::
    This action requires authentication to Red Hat Automation Orchestrator. You can provide credentials via:

    - AAP EDA credential of type "Red Hat Automation Orchestrator" (recommended)
    - Environment variables (``EDA_AO_URL``, ``EDA_AO_CLIENT_ID``, ``EDA_AO_CLIENT_SECRET``, ``EDA_AO_SSL_VERIFY``)
    - Direct action parameters (``ao_host``, ``ao_client_id``, ``ao_client_secret``, ``ao_verify_ssl``)

.. note::
    OAuth2 client_credentials authentication is required for AO service accounts. This action will obtain a fresh OAuth2 token for each workflow execution.

.. note::
    The workflow must have a webhook trigger enabled and published in Automation Orchestrator. Get the webhook UUID from the workflow's trigger configuration.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - webhook_path
     - | The webhook UUID from the AO workflow trigger configuration. This is the unique identifier
       | found in the workflow's webhook trigger parameters. Either webhook_path or workflow_name is required.
     - Conditional
   * - workflow_name
     - | The name of the workflow in AO. The action will look up the webhook path automatically.
       | Either webhook_path or workflow_name is required. Using webhook_path is recommended for better performance.
     - Conditional
   * - project
     - | When using workflow_name, optionally specify the project name to narrow the search.
     - No
   * - payload
     - | Dictionary of data to send to the AO workflow. Can use Jinja2 templates to reference event data.
       | The workflow receives this data as input parameters.
     - No
   * - ao_host
     - | AO server URL (e.g., https://ao-host.example.com/). Can be provided via action parameter,
       | AAP credential extra_vars as {{ ao_url }}, or EDA_AO_URL environment variable.
     - Conditional
   * - ao_client_id
     - | OAuth2 client ID for AO service account authentication. Can be provided via action parameter,
       | AAP credential extra_vars as {{ ao_client_id }}, or EDA_AO_CLIENT_ID environment variable.
     - Conditional
   * - ao_client_secret
     - | OAuth2 client secret for AO service account authentication. Can be provided via action parameter,
       | AAP credential extra_vars as {{ ao_client_secret }}, or EDA_AO_CLIENT_SECRET environment variable.
     - Conditional
   * - ao_verify_ssl
     - | SSL certificate verification setting. Can be "yes" (verify with system CA), "no" (disable verification),
       | or a path to a CA bundle file. Default is "yes". Can be provided via AAP credential or EDA_AO_SSL_VERIFY.
     - No
   * - timeout
     - | Maximum time in seconds to wait for workflow execution to complete. Default is 600 (10 minutes).
       | Set based on expected workflow duration.
     - No
   * - poll_interval
     - | Seconds between status checks while waiting for workflow completion. Default is 5.
       | Increase for long-running workflows to reduce API calls.
     - No
   * - post_facts
     - | Boolean, post the workflow execution results as facts to the rule set. Default is true.
       | Posted facts include execution_id, status, workflow_name, duration, and error details.
     - No
   * - post_events
     - | Boolean, post the workflow execution results as events to the rule set. Default is false.
     - No
   * - ruleset
     - | The name of the ruleset to post facts or events to. Default is current rule set.
     - No
   * - treat_errors_as_failure
     - | Boolean, whether to treat completed_with_errors status as a failure. Default is true.
       | Set to false to consider partial success as success.
     - No

**Posted Facts Structure:**

When ``post_facts`` is enabled, the action posts the following fact structure:

.. code-block:: python

    {
        "ao_execution_id": "uuid-of-execution",
        "ao_workflow_name": "name-of-workflow",
        "ao_status": "completed",  # or failed, cancelled, completed_with_errors
        "ao_webhook_path": "webhook-uuid",
        "ao_created_at": "2026-10-22T17:48:07.963156Z",
        "ao_completed_at": "2026-10-22T17:48:08.312684Z",
        "ao_duration_seconds": 0.349528,
        "ao_error_details": {...}  # Only present if execution failed
    }

**Execution Statuses:**

The action recognizes these AO workflow execution statuses:

- ``pending``: Execution queued
- ``running``: Execution in progress
- ``completed``: Success
- ``completed_with_errors``: Partial success (configurable via treat_errors_as_failure)
- ``failed``: Failure
- ``cancelled``: Cancelled

Example - Basic usage with AAP credential:

.. code-block:: yaml

    - name: Trigger disk cleanup workflow
      condition: event.payload.disk_usage | int > 90
      action:
        run_ao_workflow:
          # Credentials from AAP credential extra_vars
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"

          # Workflow identification
          webhook_path: "abc123-def456-ghi789"

          # Data sent to workflow
          payload:
            hostname: "{{ event.payload.host }}"
            disk_usage: "{{ event.payload.disk_usage }}"
            mount_point: "{{ event.payload.mount_point | default('/') }}"
            timestamp: "{{ event.meta.received_at }}"

Example - Using workflow name lookup:

.. code-block:: yaml

    - name: Trigger workflow by name
      condition: event.payload.event_type == "vm_create"
      action:
        run_ao_workflow:
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"
          workflow_name: "VM Provisioning"
          project: "IT Operations"
          payload:
            vm_name: "{{ event.payload.vm_name }}"
            cpu: "{{ event.payload.cpu | default(2) }}"
            memory: "{{ event.payload.memory | default(4) }}"

Example - With custom timeout and polling:

.. code-block:: yaml

    - name: Long-running deployment workflow
      condition: event.payload.event_type == "app_deploy"
      action:
        run_ao_workflow:
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"
          webhook_path: "abc123-def456-ghi789"
          payload:
            app_name: "{{ event.payload.app_name }}"
            version: "{{ event.payload.version }}"
          timeout: 900  # 15 minutes
          poll_interval: 10  # Check every 10 seconds
          post_facts: true

Example - Chaining workflows using posted facts:

.. code-block:: yaml

    - name: Trigger primary workflow
      condition: event.payload.event_type == "deploy"
      action:
        run_ao_workflow:
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"
          webhook_path: "primary-workflow-uuid"
          post_facts: true
          ruleset: "Deployment Pipeline"

    - name: Trigger validation after primary completes
      condition: >
        event.ao_workflow_name == "primary-workflow" and
        event.ao_status == "completed"
      action:
        run_ao_workflow:
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"
          webhook_path: "validation-workflow-uuid"
          payload:
            deployment_execution_id: "{{ event.ao_execution_id }}"

Example - Conditional workflow selection:

.. code-block:: yaml

    - name: Route to environment-specific workflow
      condition: event.payload.event_type == "deploy"
      action:
        run_ao_workflow:
          ao_host: "{{ ao_url }}"
          ao_client_id: "{{ ao_client_id }}"
          ao_client_secret: "{{ ao_client_secret }}"
          webhook_path: >
            {{ 'prod-workflow-uuid' if event.payload.environment == 'production'
               else 'dev-workflow-uuid' }}
          payload:
            app_name: "{{ event.payload.app_name }}"
            environment: "{{ event.payload.environment }}"

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
| You can also use :doc:`jinja_filters` to transform the data before posting it.

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
| You can use :doc:`jinja_filters` to transform the data in debug messages

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


FAQ
***
| **Q:** What is the purpose of lock in run_job_template, run_playbook, run_module and run_workflow_template?

| **Ans:** A lock is only relevant when you have the execution strategy set to parallel and you are executing
| multiple jobs on different systems but you want sequential control based on some attribute, e.g the name of
| the datacenter where the job is being executed, you want to ensure only one job is running on a 
| datacenter at a time but you want to run other jobs in other data centers. All jobs with the same
| lock will be run sequentially, the user has the choice of what they want to use as a lock, it could 
| be any string attribute from the event payload or it could be a static string, where you want all other
| actions to run parallel but others to run sequentially. e.g if you have
| job to run a backup of a database. The lock does not queue the tasks, it just runs them as the lock is free and 
| available, if you need to sequence tasks you can keep using the multiple actions for a rule. You can 
| do other sequencing using workflow templates instead of job templates.
Example:
    .. code-block:: yaml

        name: sample rule
        condition: event.level == "error"
        action:
          run_job_template:
            name: Fix My Datacenter
            organization: Default
            lock: "{{ event.datacenter }}"
