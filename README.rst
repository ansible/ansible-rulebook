================
ansible-rulebook
================

.. maintainenance status
.. image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg

.. codecov
.. image:: https://codecov.io/gh/ansible/ansible-rulebook/branch/main/graph/badge.svg?token=U1mIB6PI9I
        :target: https://codecov.io/gh/ansible/ansible-rulebook

.. gh workflow
.. image:: https://github.com/ansible/ansible-rulebook/actions/workflows/ci.yml/badge.svg?branch=main
        :target: https://github.com/ansible/ansible-rulebook/actions/workflows/ci.yml?query=branch%3Amain

.. python versions
.. image:: https://img.shields.io/pypi/pyversions/ansible-rulebook.svg
        :target: https://pypi.org/project/ansible-rulebook/

.. pypi
.. image:: https://img.shields.io/pypi/v/ansible_rulebook.svg
        :target: https://pypi.python.org/pypi/ansible_rulebook

.. Docs
.. image:: https://readthedocs.org/projects/ansible-rulebook/badge/?version=latest
        :target: https://ansible-rulebook.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

.. Last release
.. image:: https://img.shields.io/github/v/release/ansible/ansible-rulebook.svg
        :target: https://github.com/ansible/ansible-rulebook/releases

.. License
.. image:: https://img.shields.io/github/license/ansible/ansible-rulebook.svg
        :target: https://github.com/ansible/ansible-rulebook/blob/main/LICENSE


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
Installation
===============
Please follow the `Installation guide <https://ansible-rulebook.readthedocs.io/en/stable/installation.html>`_ to install ``ansible-rulebook``.

===============
Documentation
===============
Please refer to the `Getting Started guide <https://ansible-rulebook.readthedocs.io/en/stable/getting_started.html>`_ to get started with ``ansible-rulebook``.


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
