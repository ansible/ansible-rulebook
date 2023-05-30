====================
Decision Environment
====================

Decision Environments are `Execution Environments <https://ansible-builder.readthedocs.io/en/stable/>`_ tailored towards running Ansible
Rulebook tasks. These represent container images that launch and run the rulebook process and contain all of the dependencies, collections,
and configuration needed to run a rulebook.

A basic and minimal decision_environment is included at the root of the repository. This is a good starting point for building your own:

.. code-block:: shell

    ansible-builder build -f minimal-decision-environment.yaml -t minimal-decision-environment:latest

This will build a container image named ``minimal-decision-environment:latest`` that can be used as the basis for your own decision environment.


Using your own rulebooks and projects with the decision environment
-------------------------------------------------------------------

The minimal decision environment is a good starting point, but you will likely want to add your own rulebooks and projects to it.

..note::
    This section needs to be written