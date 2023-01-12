===============
Getting started
===============

Let's get started with a simple hello world example to familiarize ourselves with the concepts:

.. code-block:: yaml

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



Events come from a **event source** and then are checked against **rules** to determine if an **action** should
be taken.  If the **condition** of a rule matches the event it will run the action for that rule.

In this example the event source is the Python range function.  It produces events that count from
:code:`i=0` to :code:`i=<limit>`.

When :code:`i` is equal to 1 the condition for the the :code:`Say Hello` rule matches and it runs a playbook.


Normally events would come from monitoring and alerting systems or other software. The following
is a more complete example that accepts alerts from Alertmanager:

.. code-block:: yaml


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
where the `fastapi` job alert has a status of `firing`.  This runs a playbook that will
remediate the issue.
