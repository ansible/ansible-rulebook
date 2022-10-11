================
ansible-rulebook
================


.. image:: https://img.shields.io/pypi/v/ansible_rulebook.svg
        :target: https://pypi.python.org/pypi/ansible_rulebook

.. image:: https://img.shields.io/travis/ansible/ansible_rulebook.svg
        :target: https://travis-ci.com/ansible/ansible_rulebook

.. image:: https://readthedocs.org/projects/ansible-rulebook/badge/?version=latest
        :target: https://ansible-rulebook.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

* Free software: Apache Software License 2.0
* Documentation: https://ansible-rulebook.readthedocs.io.


Event driven automation for Ansible.


The real world is full of events that change the state of our software and systems.
Our automation needs to be able to react to those events. Introducing *ansible-rulebook*; a command
line tool that allows you to recognize events that you care about and react accordingly
by running a playbook or other actions.

============
Installation
============

Head over to the `Installation`_ page for details on how to install *ansible-rulebook*. Once installed,
continue with the **Getting started** section below to begin writing your first rulesets.

.. _Installation: docs/installation.rst

===============
Getting started
===============

**Important:** Running *ansible-rulebook* requires setting the *JAVA_HOME* environment variable. On Fedora-like systems, this will be::

    $ export JAVA_HOME=/usr/lib/jvm/java-17-openjdk

Let's get started with a simple hello world example to familiarize ourselves with the concepts::

    ---
    - name: Hello Events
      hosts: localhost
      sources:
        - ansible.eda.range:
            limit: 5
      rules:
        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: ansible.eda.hello
    ...


Events come from a **event source** and then are checked against **rules** to determine if an **action** should
be taken.  If the **condition** of a rule matches the event it will run the action for that rule.

In this example the event source is the Python range function.  It produces events that count from
:code:`i=0` to :code:`i=<limit>`.

When :code:`i` is equal to 1 the condition for the the :code:`Say Hello` rule matches and it runs a playbook.


Normally events would come from monitoring and alerting systems or other software. The following
is a more complete example that accepts alerts from Alertmanager::

    ---
    - name: Automatic Remediation of a webserver
      hosts: all
      sources:
        - name: listen for alerts
          ansible.eda.alertmanager:
            host: 0.0.0.0
            port: 8000
      rules:
        - name: restart web server
          condition: event.alert.labels.job == "fastapi" and event.alert.status == "firing"
          action:
            run_playbook:
              name: ansible.eda.start_app
    ...


This example sets up a webhook to receive events from alertmanager and then matches events
where the `fastapi` job alert has a staus of `firing`.  This runs a playbook that will
remediate the issue.



Features
--------

* Connect to event streams and handle events in near real time.
* Conditionally launch playbooks based on rules that match events in event streams.
* Store facts about the world from data in events
* Limit the hosts where playbooks run based on event data
* Run smaller jobs that run more quickly by limiting the hosts where playbooks run based on event data



Examples
--------

Rules are organized into rulesets using a syntax that is similar to ansible-playbooks::

    ---
    - name: Hello Events
      hosts: localhost
      sources:
        - ansible.eda.range:
            limit: 5
      rules:
        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: ansible.eda.hello
    ...

Each ruleset defines: a set of hosts to pass to the playbook, a set of event sources,
and a set of rules.   The set of hosts is the normal hosts pattern from ansible playbooks.
The event sources are a new type of plugin that subscribe to events from event streams.
The rules have conditions that match values in the events and actions that can run playbooks,
assert facts, retract facts, and print information to the console.


Let's look closer at the event source::

        - ansible.eda.range:
            limit: 5

This section of YAML defines that an event source plugin from the ansible.eda should
be loaded and given the arguments: limit=5.  This source will generate a range of numbers
from zero to 4 and then exit.

The rules YAML structure looks like the following::

        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: ansible.eda.hello


This block of YAML defines a rule with name "Say Hello", a condition that matches
when an event has an value "i" that is equal to 1, and an action that runs a playbook
inside the collection ansible.eda.

For more information on usage and examples, please refer to the `Usage`_ guide.

.. _Usage: docs/usage.rst


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
