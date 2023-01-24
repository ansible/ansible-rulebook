=========
Rulebooks
=========

| Rulebooks contain a list of rulesets. Each ruleset within a rulebook
| should have a unique name since they can post events to each other at runtime
| based on the name. Sample rulebooks_. If a rulebook has multiple rulesets
| shutting down one ruleset will shutdown all the other running rulesets.


.. _rulebooks: https://github.com/ansible/ansible-rulebook/tree/main/tests/examples



Rulesets
--------
A ruleset has the following properties:

* name
* hosts similar to Ansible playbook
* gather_facts: boolean
* sources: A list of sources
* rules: a list of rules

| A ruleset **should** have a unique name within the rulebook, each ruleset runs
| as a separate session in the Rules engine. The events and facts are kept separate
| for each ruleset. At runtime, using **action** a ruleset can post events or facts
| to itself or other rulesets in the rulebook.

| When we start a rulebook we can optionally collect artifacts from the different hosts
| if **gather_facts** is set to **true**. This host data is then uploaded to the Rules
| engine as fact to be evaluated at runtime in the different rules based on the
| incoming events. Each host data is stored separately in the Rules engine. To access the
| host name use the **fact.meta.hosts** attribute. e.g.

.. code-block:: yaml

    - name: Example
      hosts: all
      sources:
        - name: range
          range:
            limit: 5
      rules:
        - name: r1
          condition: event.i == 1
          action:
            debug:

        - name: "Host specific rule"
          condition:
            all:
              - fact.ansible_os_family == "linux"
              - fact.meta.hosts == "my-host"
              - event.i == 4
          action:
            debug:

| A ruleset **must** contain one or more sources, it allows you to pass configuration
| parameters into the source plugin. The Source plugin can also be configured with
| event filters which allow you to transform the data before passing it to the Rules
| engine. The filters can also be used to limit the data that gets passed to the Rules
| engine. The source plugin is started by the **ansible-rulebook** and runs in the
| background putting events into the queue to be passed onto the Rules engine.
| When the source plugin ends we automatically generate a shutdown event and the ruleset
| terminates which terminates **ansible-rulebook**.

| A ruleset **must** contain one or more rules. The rules are evaluated by the Rules engine.
| The Rules engine will evaluate all the required conditions for a rule based on the
| incoming events. If the conditions in a rule match, we trigger the actions. The actions
| can run playbooks, modules, raise another event or fact to the same ruleset or a different
| ruleset. A ruleset stops execution when it receives the shutdown event from either the
| Source plugin or a shutdown action is invoked by one of the matching rules.


Including multiple sources
--------------------------

In a rulebook you can configure one or more sources, each emitting events in different format.

Example

.. code-block:: yaml

    sources:
      - ansible.eda.range:
          limit: 6
      - ansible.eda.webhook:
          port: 5000

The condition can match events from either source

.. code-block:: yaml

    rules:
      - name:
        condition: event.i == 2
        action:
          debug:

      - name:
        condition: event.payload.status == "OK"
        action:
          debug:

To avoid name conflicts the source data structure can use nested keys.

**Notes:**

If any source terminates, it shuts down the whole engine. All events from other sources may be lost.
