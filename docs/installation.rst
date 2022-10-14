============
Installation
============

These instructions will guide you though installing the ansible-rulebook CLI on your local system.
Please ensure you have installed all components listed in the **Requirements** section before starting the installation process.

Requirements
------------

* Python >=3.9
* Python 3 pip
* Python 3 development libraries

  * Fedora: python3-devel
  * Ubuntu: python3-dev

* Java development kit 17

  * Fedora: java-17-openjdk
  * Ubuntu: openjdk-17-jdk

* Maven
* gcc

Installation via pip
--------------------

1. Ensure the `JAVA_HOME` environment variable is set. On Fedora-like systems it should be::

    JAVA_HOME=/usr/lib/jvm/java-17-openjdk

2. We use a rules engine called Drools which is written in Java and needs to be compiled from source, by 
   setting the following environment variable::

    export PIP_NO_BINARY=jpy

3. Install `ansible-rulebook` and dependencies via `pip`::

    pip install wheel ansible-rulebook ansible ansible-runner

4. Install the required Ansible collections::

    ansible-galaxy collection install community.general ansible.eda
