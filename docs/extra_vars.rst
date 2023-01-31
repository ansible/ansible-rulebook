=========================================
Extra vars for playbooks or job templates
=========================================

Extra vars needed by each playbook or job template should be explicitly
specified in the extra_vars section under actions in a rulebook. The values of
extra vars can be literals or references to rulebook variables. In addition to
the user specified extra vars, the rulebook engine automatically inserts 
fact/event (single match) or facts/events (multiple matches) under the top
level key ansible_eda.

Example of run_playbook and run_module actions:

.. code-block:: yaml

      action:
        run_playbook:
          name: playbooks/hello.yml
          extra_vars:
            foo: "{{ FOO }}"
            bar: BAR

Example of run_job_template action:

.. code-block:: yaml

      action:
        run_job_template:
          name: Demo
          organization: Default
          job_args:
            extra_vars:
                foo: "{{ FOO }}"
                bar: BAR

Example of a playbook that uses the extra_vars:

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

Rulebook variables can be loaded from a static file or selected from
environment variables through command line.

Example to set rulebook variables through a static file:

.. code-block:: php

    rulebook --vars myvars.yml --rulebook myrules.yml

The content of myvars.yml:

.. code-block:: php

    FOO: Foe

Example to set rulebook variables through environment variables:

.. code-block:: php

    export FOO=Foo
    export BAR=Bar
    rulebook --env-vars FOO,BAR --rulebook myrules.yml

If there is a variable name conflict because of both --env-vars and --vars are
used, the ones from --env-vars take precedent.
