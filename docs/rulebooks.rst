=========
Rulebooks
=========

| Rulebooks contain a collection of rulesets. Each ruleset within a rulebook
| should have a unique name since they can post events to each other at runtime
| based on the name. Sample rulebooks_. If a rulebook has multiple rulesets
| shutting down one ruleset will shutdown all the other running rulesets.


========
Rulesets
========
A ruleset has the following properties

* name
* hosts similar to Ansible playbook
* gather_facts
* sources
* rules

| A ruleset **should** have a unique name within the rulebook, each ruleset runs
| as a separate session in the Rules engine. The events and facts are kept separate
| for each ruleset. At runtime, using **action** a ruleset can post events or facts 
| to itself or other rulesets in the rulebook.

| When we start a rulebook we can optionally collect artifacts from the different hosts
| if **gather_facts** is set to **true**. This host data is then uploaded to the Rules
| engine as fact to be evaluated at runtime in the different rules based on the 
| incoming events. Each host data is stored separately in the Rules engine. To access the
| host name use the **fact.meta.hosts** attribute. e.g.

::

    - name: "Host specific rule"
      condition:
        all:
          - fact.ansible_os_family == "linux"
          - fact.meta.hosts == "my-host"
          - event.i == 4 
      action:
        debug:

| A ruleset **should** contain one or more sources, it allows you to pass configuration 
| parameters into the source plugin. The Source plugin can also be configured with 
| event filters which allow you to transform the data before passing it to the Rules
| engine. The filters can also be used to limit the data that gets passed to the Rules
| engine. The source plugin is started by the **ansible-rulebook** and runs in the
| background putting events into the queue to be passed onto the Rules engine.
| When the source plugin ends we automatically generate a shutdown event and the ruleset
| terminates which terminates **ansible-rulebook**.

| A ruleset **should** contain one or more rules. The rules are evaluated by the Rules engine.
| The Rules engine will evaluate all the required conditions for a rule based on the
| incoming events. If the conditions in a rule match, we trigger the actions. The actions
| can run playbooks, modules, raise another event or fact to the same ruleset or a different
| ruleset. A ruleset stops execution when it receives the shutdown event from either the 
| Source plugin or a shutdown action is invoked by one of the matching rules.

.. _rulebooks: https://github.com/ansible/ansible-rulebook/tree/main/tests/examples
