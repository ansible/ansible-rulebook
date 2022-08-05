==============
ansible-events
==============


.. image:: https://img.shields.io/pypi/v/ansible_events.svg
        :target: https://pypi.python.org/pypi/ansible_events

.. image:: https://img.shields.io/travis/benthomasson/ansible_events.svg
        :target: https://travis-ci.com/benthomasson/ansible_events

.. image:: https://readthedocs.org/projects/ansible-events/badge/?version=latest
        :target: https://ansible-events.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

* Free software: Apache Software License 2.0
* Documentation: https://ansible-events.readthedocs.io.


Event driven automation for Ansible.


The real world is fully of events that change the state of our software and systems.
Our automation needs to be able to react to those events.  Ansible-events is a command
line tool that allows you to recognize which events that you care about and react accordingly
by running a playbook or other actions.


Let's get started with a simple hello world example to familiarize ourselves with the concepts::

    ---
    - name: Hello Events
      hosts: localhost
      sources:
        - benthomasson.eda.range:
            limit: 5
      rules:
        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: benthomasson.eda.hello
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
          benthomasson.eda.alertmanager:
            host: 0.0.0.0
            port: 8000
      rules:
        - name: restart web server
          condition: event.alert.labels.job == "fastapi" and event.alert.status == "firing"
          action:
            run_playbook:
              name: benthomasson.eda.start_app
    ...


This example sets up a webhook to receive events from alertmanager and then matches events
where the `fastapi` job alert has a staus of `firing`.  This runs a playbook that will
remediate the issue.



Features
--------

* Conditionally launch playbooks based on rules that match events in event streams.



Examples
--------

Rules are organized into rulesets using a syntax that is similar to ansible-playbooks::

    ---
    - name: Hello Events
      hosts: localhost
      sources:
        - benthomasson.eda.range:
            limit: 5
      rules:
        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: benthomasson.eda.hello
    ...

Each ruleset defines: a set of hosts to pass to the playbook, a set of event sources,
and a set of rules.   The set of hosts is the normal hosts pattern from ansible playbooks.
The event sources are a new type of plugin that subscribe to events from event streams.
The rules have conditions that match values in the events and actions that can run playbooks,
assert facts, retract facts, and print information to the console.


Let's look closer at the event source::

        - benthomasson.eda.range:
            limit: 5

This section of YAML defines that an event source plugin from the benthomasson.eda should
be loaded and given the arguments: limit=5.  This source will generate a range of numbers
from zero to 4 and then exit.

The rules YAML structure looks like the following::

        - name: Say Hello
          condition: event.i == 1
          action:
            run_playbook:
              name: benthomasson.eda.hello


This block of YAML defines a rule with name "Say Hello", a condition that matches
when an event has an value "i" that is equal to 1, and an action that runs a playbook
inside the collection benthomasson.eda.



How to install
--------------

Via PyPi:
#########

.. code-block:: shell-session

    pip install ansible-events

Via Docker:
###########

.. code-block:: shell-session

    docker build -t ansible-events .


Usage
--------------

.. code-block:: shell-session

    ansible-events --help


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
