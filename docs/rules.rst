=====
Rules
=====

| The rules node in a rulebook contains a list of rules. Event driven automation uses rules 
| to determine if an action or actions should be executed when an event is received.
| The rule decides to run an action or actions by evaluating the condition(s) 
| that is defined by the rulebook author. When writing the conditions for a rule you have
| to be aware of the attributes in the event payload from different sources defined in the
| ruleset.

A rule comprises of:


.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name is a string to identify the rule. This field is mandatory. Each rule in a ruleset must have an unique name across the rulebook. You can use Jinja2 substitution in the name.
     - Yes
   * - condition
     - See :doc:`conditions`
     - Yes
   * - actions
     - See :doc:`actions`
     - or action
   * - action
     - See :doc:`actions`
     - or actions
   * - enabled
     - If the rule should be enabled, default is true. Can be set to false to disable a rule.
     - No



Example: A single action

    .. code-block:: yaml

        rules:
          - name: An automatic remediation rule
            condition: event.outage == true
            action:
              run_playbook:
                name: remediate_outage.yml

          - name: Print event with linux
            condition: event.target_os == "linux"
            action:
              debug:

Example: Multiple actions

    .. code-block:: yaml

        rules:
          - name: An automatic remediation rule
            condition: event.outage == true
            actions:
              - run_playbook:
                  name: remediate_outage.yml
              - print_event:
                  pretty: true

| In the above example 2 actions are executed when the condition matches,
| The actions run sequentially in the order they are listed under actions.
| We wait for each action to finish before executing the next action.

Example: Disable a rule

    .. code-block:: yaml

        rules:
          - name: An automatic remediation rule
            condition: event.outage == true
            enabled: false
            action:
              run_playbook:
                name: remediate_outage.yml

          - name: Print event with linux
            condition: event.target_os == "linux"
            action:
              debug:

| In the above example the first rule is disabled by setting enabled to false
| This can be used when testing to temporarily disable a rule.
