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
     - Similar to hosts in an Ansible playbook.  This value is used for actions that require an inventory (eg: run_playbook, or run_module).  It is not used for controller actions (eg: run_job_template, run_workflow_template)
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
   * - match_multiple_rules
     - Whether the rules engine should continue processing additional rules even after the initial match.
       This option will cache events in the rules engine for a period of **default_events_ttl**. Which by
       default is 2 hours, this will cause memory bloat till the events are ejected.
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


Using vaulted strings
--------------------------

Sensitive data referenced by a rulebook must be encrypted by `ansible-vault <https://docs.ansible.com/ansible/latest/vault_guide/vault_encrypting_content.html#encrypting-content-with-ansible-vault>`_
cli. The vaulted strings can be directly embedded in the rulebook, or placed in a variables file and
referenced in the rulebook via extra vars. Only arguments to source plugins or actions can be vaulted.
Example for a rulebook that has embedded vaulted strings:

.. code-block:: yaml

      action:
        run_playbook:
          name: !vault |
            $ANSIBLE_VAULT;1.1;AES256
            34363839636133343562323339363066616165326363626133616264326565336633386438333936
            3833303135313062343861353765383633643931613535340a356532376531656566643133303833
            39396335636439363838386430346532623633303763626362646435633736613834333534663532
            3966643666326535620a626166616465386639373136396236336161333836303664633330356134
            30396661336162343734353837366437383433343461333564663236313639376633616238633463
            3765626362303336303761373538343939396434346261356164
          extra_vars:
            foo: "{{ foo_var }}"

Example for a variables file with vaulted strings:

    .. code-block:: yaml

        ---
        foo_var: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          33353433303339303239653832383938613664323063313065326365323232366537613762303736
          3864333763656663646332653738316135383562343962300a653333303538353132366336323337
          39366365303563386636613834633463303835613461393066643632356338393038306366616631
          3534326432333466390a303037323232663239636132343836313434333139623530386134326130
          3465
        match_this_int: 2


    .. warning::
        Encryption with Ansible Vault ONLY protects ‘data at rest’. Once the content is decrypted (‘data in use’), 
        rulebook and source plugin authors are responsible for avoiding any secret disclosure.

The password to decrypt the vaulted strings can be provided through one the cli arguments, namely
`--vault-id`, `--vault-password-file`, or `--ask-vault-pass`. If only one password file is used, it can be also
set via env var EDA_VAULT_PASSWORD_FILE.

Example to receive one password for all vaulted strings:

.. code-block:: console

    ansible-rulebook --rulebook rules_with_vaulted_vars.yml --vault-password-file mypassword.txt

Example to receive multiple passwords:

.. code-block:: console

    ansible-rulebook --rulebook rules.yml --vars vars.yml --vault-id pass1@mypassword1.txt --vault-id pass2@mypassword2.txt

Refer to the `Usage <usage.html>`_ page for more information.

Please note vaulted strings in a rulebook or variables file are not supported if the ansible-rulebook cli version
is 1.0.4 or older. You will see an error like `ERROR - Terminating could not determine a constructor for the tag '!vault'`

Distributing rulebooks
^^^^^^^^^^^^^^^^^^^^^^

The recommended method for distributing rulebooks is through a collection. In this case
the rulebook file should be placed under ``extensions/eda/rulebooks`` folder
and referred to by FQCN in the command line argument. `Eda-server <https://github.com/ansible/eda-server>`_ project will honor this path
for the projects even if the repository is not real collection.
