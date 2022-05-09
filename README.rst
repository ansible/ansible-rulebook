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




Event driven automation for Ansible


* Free software: Apache Software License 2.0
* Documentation: https://ansible-events.readthedocs.io.


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





Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
