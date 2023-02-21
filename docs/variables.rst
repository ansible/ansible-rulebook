=========
Variables
=========

Variables can be parsed into a rulebook using one or both of these command line arguments::

    --vars VARS           Variables file
    --env-vars ENV_VARS   Comma separated list of variables to import from the environment

To import variables from a JSON or YAML formatted file, the `--vars` argument should be used.
To import environment variables the `--env-vars` argument should be used. It is possible to specify
multiple environment variables separated by a comma.

.. important::
    Variables that are supplied using the `--vars` argument will have their data type preserved, but environment
    variables parsed via `--env-vars` are always treated as strings. This is important to consider when parsing
    variables into your rulebook.

.. note::
    In cases where the same variable is supplied via `--env-vars` and `--vars`, the one from
    `--env-vars` will always take precedence.


Accessing variables in your rulebook
------------------------------------

The are two important considerations to take into account when accessing variables in a rulebook:

    1. In order to use variables in conditions, the variables supplied at runtime will be placed into a namespace
    called **vars**. You must use the **vars.** prefix followed by the variable name to use variables in conditions.

    2. Jinja substitution should be used when accessing variables in any other part of the rulebook, such as in
    the source configuration or in actions.

Let's take the following example rulebook:

    .. code-block:: yaml

        ---
        - name: Testing vars
          hosts: all
          sources:
            - ansible.eda.range:
                limit: "{{ src_range_limit }}"
          rules:
            - name: Say Hello
              condition: event.i == vars.match_this_int
              action:
                debug:
                  msg: "Hi, I'm {{ MY_NAME }}."

In this rulebook we use three different variables. One, **MY_NAME**, we will supply using an environment variable.
The other two will be supplied in a file called `vars.yml` which looks like this:

    .. code-block:: yaml

        ---
        src_range_limit: 4
        match_this_int: 2

To run this rulebook we will need to use both `--vars` and `--env-vars` to parse the variables into the rulebook. Therefore,
we would execute the rulebook as follows:

    .. code-block:: console

        $ MY_NAME="Bob" ansible-rulebook -i inventory.yml --rulebook hello_there.yml --vars vars.yml --env-vars MY_NAME

Which would return the following output:

    .. code-block:: console

        2023-02-09 13:37:73.311337 : Hi, I'm Bob

.. note::
    - To avoid potential issues with variable expansion, we recommend enclosing any value that contains Jinja substituted
      variables in quotation marks, as shown in the above example.
    - Note the use of the **vars.** prefix in the condition instead of Jinja substitution, which does not work when used in
      conditions. Refer to the `Conditions <conditions.html>`_ page for more information.


Providing extra vars to actions
-------------------------------

The `run_playbook` and `run_job_template` actions include an optional parameter called **extra_vars** which can be used
for sending extra variables to the respective action. For example, you may have a playbook that runs remediation
tasks when an issue with a host is detected, but the playbook requires some variables to be provided at runtime
for it to execute properly. This is where the **extra_vars** parameter comes in.

Extra vars needed by each playbook or job template should be explicitly specified in the **extra_vars** section
under the action in your rulebook. The values of extra vars may be literals, or references to other rulebook
variables. In addition to the user supplied runtime variables described above, the rulebook engine will automatically
insert event (single match) or events (multiple matches), ruleset and rule under the top level key **ansible_eda**.

Example run_playbook action:

.. code-block:: yaml

      action:
        run_playbook:
          name: playbooks/hello.yml
          extra_vars:
            foo: "{{ FOO }}"
            bar: BAR

Example run_job_template action:

.. code-block:: yaml

      action:
        run_job_template:
          name: Demo
          organization: Default
          job_args:
            extra_vars:
                foo: "{{ FOO }}"
                bar: BAR

Example playbook that uses the extra_vars:

.. code-block:: yaml

    - name: Print extra_vars
      hosts: localhost
      gather_facts: false
      tasks:
        - name: Print variable foo set by user
          ansible.builtin.debug:
            msg: '{{ foo }}'
        - name: Print variable event set by rulebook engine
          ansible.builtin.debug:
            msg: '{{ ansible_eda.event }}'
