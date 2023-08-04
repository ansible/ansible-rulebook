.. _decision-environment:

====================
Decision Environment
====================

.. note::

    Some of the examples in this section refer to Rulebooks store in collections. If you are interested in packaging your event driven automation 
    in collections, please see the :ref:`Rulebook and Collections <rulebook-collections>` section.

Decision Environments are `Execution Environments <https://ansible-builder.readthedocs.io/en/latest/>`_ tailored towards running Ansible
Rulebook tasks. These represent container images that launch and run the rulebook process and contain all of the dependencies, collections,
and configuration needed to run a rulebook.

A basic and minimal decision_environment is included at the root of the repository. This is a good starting point for building your own:

.. code-block:: shell

    ansible-builder build -f minimal-decision-environment.yml -t minimal-decision-environment:latest

This will build a container image named ``minimal-decision-environment:latest`` that can be used as the basis for your own decision environment.

Lets run a rulebook using this decision environment, lets make sure we have a local inventory that has localhost in it we're going to use:

.. code-block:: shell

    echo "localhost ansible_connection=local" > inventory

Now lets run a rulebook using this decision environment:

.. code-block:: shell

    docker run -it --rm -v ./inventory:/tmp/inventory ansible-execution-env:latest ansible-rulebook -r ansible.eda.hello_events -i /tmp/inventory


Using your own rulebooks and projects with the decision environment
-------------------------------------------------------------------

The minimal decision environment is a good starting point, but you will likely want to add your own rulebooks and projects to it.

.. note::

    Have a look at the `Ansible Builder Execution Environment Definition <https://ansible-builder.readthedocs.io/en/latest/definition/>`_ for details on how to add collections and dependencies to your decision environment.

.. code-block:: yaml

    ---
    version: 3

    images:
        base_image:
            name: 'minimal-decision-environment:latest'
    dependencies:
        python:
            - pywinrm
        system:
            - iputils [platform:rpm]
        galaxy:
            collections:
                - name: my_namespace.my_awesome_collection
                - name: community.windows
                - name: ansible.utils
                  version: 2.10.1

This shows an example where you may have your own Collection that contains rulebooks and playbooks but need to bring them together with some other collections
and some python and system dependencies.

You could also use Builder to add your own rulebooks and playbooks to the decision environment via `additional-build-steps <https://ansible-builder.readthedocs.io/en/latest/definition/#additional-build-steps>`_
and then making use of Containerfile commands to ADD or COPY to get the files into the environment.

.. code-block:: yaml

    ---
    version: 3

    images:
        base_image:
            name: 'minimal-decision-environment:latest'
    dependencies:
        python:
            - pywinrm
        system:
            - iputils [platform:rpm]
        galaxy:
            collections:
                - name: community.windows
                - name: ansible.utils
                  version: 2.10.1
    additional_build_steps:
        prepend_builder:
            - 'RUN mkdir -p /opt/ansible/my_rulebooks'
            - 'COPY my_rulebook.yml /opt/ansible/my_rulebooks'

.. note::

    container_init.cmd is an optional override that can be used to override the default command that is run when the container is launched. This is useful if you want to
    run a playbook or rulebook without needing to supply the full command line arguments. It can still be overridden at runtime by passing a command to the container.
