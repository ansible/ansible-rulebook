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


Event driven automation for Ansible.


The real world is full of events that change the state of our software and systems.
Our automation needs to be able to react to those events. Introducing *ansible-rulebook*; a command
line tool that allows you to recognize events that you care about and react accordingly
by running a playbook or other actions.


Features
--------

* Connect to event streams and handle events in near real time.
* Conditionally launch playbooks or Tower's job templates based on rules that match events in event streams.
* Store facts about the world from data in events
* Limit the hosts where playbooks run based on event data
* Run smaller jobs that run more quickly by limiting the hosts where playbooks run based on event data


===============
Documentation
===============
To learn more about using ``ansible-rulebook`` view the `Docs site <https://ansible-rulebook.readthedocs.io/>`_.

============
Installation
============

Head over to the Installation_ page for details on how to install *ansible-rulebook*.

.. _Installation: docs/installation.rst

===============
Contributing
===============
We ask all of our community members and contributors to adhere to the `Ansible code of conduct <https://docs.ansible.com/ansible/latest/community/code_of_conduct.html>`_.
If you have questions or need assistance, please reach out to our community team at codeofconduct@ansible.com

Refer to the Contributing guide to get started developing, reporting bugs or providing feedback.


Credits
-------

ansible-rulebook is sponsored by `Red Hat, Inc <https://www.redhat.com>`_.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
