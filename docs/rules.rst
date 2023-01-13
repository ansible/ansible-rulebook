=====
Rules
=====

Rules is a list of rules. Event driven automation uses rules to determine if an action should be taken when an event is received.
The rule decides to run an action by evaluating the condition(s) that is defined by the rulebook author.

A rule comprises:


.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name is a string to identify the rule. This field is mandatory. Each rule in a ruleset must have an unique name across the rulebook.
     - Yes
   * - condition
     - See :doc:`conditions`
     - Yes
   * - action
     - See :doc:`actions`
     - Yes



Example:

    .. code-block:: yaml

        rules:
          - name: An automatic remediation rule
            condition: event.outage == true
            action:
              run_playbook:
                name: remediate_outage.yml

          - name: Print event with linux
            condition: event.target_os == "linux" or
            action:
              debug:
