=========
Rulebooks
=========

| Rulebooks contain a list of rulesets. Each ruleset within a rulebook
| should have a unique name since they can post events to each other at runtime
| based on the name. If a rulebook has multiple rulesets
| shutting down one ruleset will shutdown all the other running rulesets.


Rulesets
--------
A ruleset has the following properties:

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Name
     - Description
     - Required
   * - name
     - The name to identify the ruleset. Each ruleset must have an unique name across the rulebook.
     - Yes
   * - sources
     - The list of one or more sources that will generate events for ansible-rulebook. See :doc:`sources`
     - Yes
   * - rules
     - The list of one or more rule. See :doc:`rules`
     - Yes
   * - hosts
     - Similar to hosts in an Ansible playbook
     - Yes
   * - gather_facts
     - Collect artifacts from hosts at startup to be used in rules (default: false)
     - No
   * - default_events_ttl
     - time to keep the partially matched events around (default: 2 hours)
     - No
   * - execution_strategy
     - Action execution, sequential or parallel (default: sequential). For sequential
       strategy we wait for the each action to finish before firing of the next action.
     - No

| A ruleset **should** have a unique name within the rulebook, each ruleset runs
| as a separate session in the Rules engine. The events and facts are kept separate
| for each ruleset. At runtime, using **action** a ruleset can post events or facts
| to itself or other rulesets in the rulebook.

| The default_events_ttl takes time in the following format
| default_events_ttl : **nnn seconds|minutes|hours|days**
| e.g. default_events_ttl : 3 hours
| If the rule set doesn't define this attribute the default events ttl that is
| enforced by the rule engine is 2 hours

| When we start a rulebook we can optionally collect artifacts from the different hosts
| if **gather_facts** is set to **true**. This host data is then uploaded to the Rules
| engine as fact to be evaluated at runtime in the different rules based on the
| incoming events. Each host data is stored separately in the Rules engine. To access the
| host name use the **fact.meta.hosts** attribute. e.g.

.. code-block:: yaml

    - name: Example
      hosts: all
      gather_facts: true
      sources:
        - name: range
          ansible.eda.range:
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

| A ruleset **must** contain one or more source plugins, the configuration parameters
| can be specified after the source plugin type. The source plugin
| can also be configured with event filters which allow you to transform the
| data before passing it to the rules engine. The filters can also be used to
| limit the data that gets passed to the rules engine. The source plugin is
| started by the **ansible-rulebook** and runs in the background putting events
| into the queue to be passed onto the rules engine.
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



Distributing rulebooks
^^^^^^^^^^^^^^^^^^^^^^

The recommended method for distributing rulebooks is through a collection. In this case
the rulebook file should be placed under ``extensions/eda/rulebooks`` folder
and referred to by FQCN in the command line argument. `Eda-server <https://github.com/ansible/eda-server>`_ project will honor this path
for the projects even if the repository is not real collection.
