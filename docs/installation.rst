============
Installation
============

These instructions will guide you though installing the ansible-rulebook CLI on your local system.
Please ensure you have installed all components listed in the **Requirements** section before starting the installation process.

Requirements
------------

* Python >= 3.9
* Python 3 pip

* Java development kit >= 17

  * Fedora: java-17-openjdk
  * Ubuntu: openjdk-17-jdk


Installation via pip
--------------------


1. Ensure the `JAVA_HOME` environment variable is set if you have multiple Java installations. On Fedora-like systems it should be::

    JAVA_HOME=/usr/lib/jvm/jre-17-openjdk


2. Install `ansible-rulebook` and dependencies via `pip`::

    pip install ansible-rulebook ansible ansible-runner

.. note::

    ansible-rulebook relies on the `jpy` Python package to communicate with the Java runtime. This package provide wheels for the most common platforms,
    `but not for all <https://github.com/jpy-consortium/jpy#automated-builds>`_. If you are using a platform that is not supported by `jpy` wheels, you will need to compile it by yourself.
    Refer to the `Compiling jpy section <#compiling-jpy>`_ for more information.


3. Install the ansible.eda collection which comes with various event source plugins and filters to get you started. Please refer to the instructions in the
`collection repository <https://github.com/ansible/event-driven-ansible#install>`_.


Installation examples
---------------------

On Fedora-like systems:

.. code-block:: shell

    dnf --assumeyes install java-17-openjdk python3-pip
    export JAVA_HOME=/usr/lib/jvm/jre-17-openjdk
    pip3 install ansible ansible-rulebook ansible-runner

On Ubuntu systems:

.. code-block:: shell

    apt-get --assume-yes install openjdk-17-jdk python3-pip
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    export PATH=$PATH:~/.local/bin
    pip3 install ansible ansible-rulebook ansible-runner


Compiling jpy
---------------------

To compile `jpy` from source at installation time, you will need to install the additional dependencies:

* maven
* gcc
* python-devel package
    * Fedora: python3-devel
    * Ubuntu: python3-dev
* Environment variable `JAVA_HOME` set to the path of your Java installation

Then, you can run:

.. code-block:: shell

    pip install ansible-rulebook --no-binary jpy


Refer to the `jpy project <https://github.com/jpy-consortium/jpy>`_ for more information.
