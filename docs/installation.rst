============
Installation
============

These instructions will guide you though installing the ansible-rulebook CLI on your local system.
Please ensure you have installed all components listed in the **Requirements** section before starting the installation process.

Requirements
------------

* Python >= 3.8
* Python 3 pip

  * Fedora: python3-devel
  * Ubuntu: python3-dev

* Java development kit >= 17

  * Fedora: java-17-openjdk
  * Ubuntu: openjdk-17-jdk

* Maven >=3.8

Installation via pip
--------------------

1. Ensure the `JAVA_HOME` environment variable is set if you have multiple Java installations.
On Fedora-like systems it should be::

    JAVA_HOME=/usr/lib/jvm/java-17-openjdk

2. Install `ansible-rulebook` and dependencies via `pip`::

    pip install wheel ansible-rulebook ansible ansible-runner

3. Install the required Ansible collections::

    ansible-galaxy collection install community.general ansible.eda

Installation examples
---------------------

On Fedora-like systems:

.. code-block:: shell

    dnf --assumeyes install java-17-openjdk maven python3-pip
    export JDK_HOME=/usr/lib/jvm/java-17-openjdk
    export JAVA_HOME=$JDK_HOME
    pip3 install -U Jinja2
    pip3 install ansible ansible-rulebook ansible-runner wheel

On Ubuntu systems:

.. code-block:: shell

    apt-get --assume-yes install maven openjdk-17-jdk python3-pip
    export JDK_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    export JAVA_HOME=$JDK_HOME
    export PATH=$PATH:~/.local/bin
    pip3 install -U Jinja2
    pip3 install ansible ansible-rulebook ansible-runner wheel
