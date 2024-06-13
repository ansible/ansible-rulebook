===============
Getting started
===============

If ansible-rulebook is not already installed, please follow the `installation guide <installation.html>`_ to install it.

Now let's get started with a simple hello world example to familiarize ourselves with the concepts:

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


Let's build an example rulebook that will trigger an action from a
webhook. We will be looking for a specific payload from the webhook, and
if that condition is met from the webhook event, then ansible-rulebook
will trigger the desired action. Below is our example rulebook:

.. code-block:: yaml

   ---
   - name: Listen for events on a webhook
     hosts: all

     ## Define our source for events

     sources:
       - ansible.eda.webhook:
           host: 0.0.0.0
           port: 5000

     ## Define the conditions we are looking for

     rules:
       - name: Say Hello
         condition: event.payload.message == "Ansible is super cool"

     ## Define the action we should take should the condition be met

         action:
           run_playbook:
             name: say-what.yml

The playbook ``say-what.yml``:

.. code-block:: yaml

   - hosts: localhost
     connection: local
     tasks:
       - debug:
           msg: "Thank you, my friend!"

If we look at this example, we can see the structure of the rulebook.
Our sources, rules and actions are defined. We are using the webhook
source plugin from our ansible.eda collection, and we are looking for a
message payload from our webhook that contains “Ansible is super cool”.
Once this condition has been met, our defined action will trigger which
in this case is to trigger a playbook.

One important thing to take note of ansible-rulebook is that it is not
like ansible-playbook which runs a playbook and once the playbook has
been completed it will exit. With ansible-rulebook, it will continue to
run waiting for events and matching those events, it will only exit upon
a shutdown action or if there is an issue with the event source itself,
for example if a website you are watching with the url-check plugin
stops working.

With our rulebook built, we will simply tell ansible-rulebook to use it
as a ruleset and wait for events:

.. code-block:: shell

   root@ansible-rulebook:/root# ansible-rulebook --rulebook webhook-example.yml -i inventory.yml --verbose

   INFO:ansible_events:Starting sources
   INFO:ansible_events:Starting sources
   INFO:ansible_events:Starting rules
   INFO:root:run_ruleset
   INFO:root:{'all': [{'m': {'payload.message': 'Ansible is super cool!'}}], 'run': <function make_fn.<locals>.fn at 0x7ff962418040>}
   INFO:root:Waiting for event
   INFO:root:load source
   INFO:root:load source filters
   INFO:root:Calling main in ansible.eda.webhook

Now, ansible-rulebook is ready and it's waiting for an event to match.
If a webhook is triggered but the payload does not match our condition
in our rule, we can see it in the ansible-rulebook verbose output:

.. code-block:: shell

   …
   INFO:root:Calling main in ansible.eda.webhook
   INFO:aiohttp.access:127.0.0.1 [14/Oct/2022:09:49:32 +0000] "POST /endpoint HTTP/1.1" 200 158 "-" "curl/7.61.1"
   INFO:root:Waiting for event

But once our payload matches what we are looking for, that's when the
magic happens, so we will simulate a webhook with the correct payload:

.. code-block:: shell

   curl -H 'Content-Type: application/json' -d "{\"message\": \"Ansible is super cool\"}" 127.0.0.1:5000/endpoint


   INFO:root:Calling main in ansible.eda.webhook
   INFO:aiohttp.access:127.0.0.1 [14/Oct/2022:09:50:28 +0000] "POST /endpoint HTTP/1.1" 200 158 "-" "curl/7.61.1"
   INFO:root:calling Say Hello
   INFO:root:call_action run_playbook
   INFO:root:substitute_variables [{'name': 'say-what.yml'}] [{'event': {'payload': {'message': 'Ansible is super cool'}, 'meta': {'endpoint': 'endpoint', 'headers': {'Host': '127.0.0.1:5000', 'User-Agent': 'curl/7.61.1', 'Accept': '*/*', 'Content-Type': 'application/json', 'Content-Length': '36'}}}, 'fact': {'payload': {'message': 'Ansible is super cool'}, 'meta': {'endpoint': 'endpoint', 'headers': {'Host': '127.0.0.1:5000', 'User-Agent': 'curl/7.61.1', 'Accept': '*/*', 'Content-Type': 'application/json', 'Content-Length': '36'}}}}]
   INFO:root:action args: {'name': 'say-what.yml'}
   INFO:root:running Ansible playbook: say-what.yml
   INFO:root:Calling Ansible runner

   PLAY [say thanks] **************************************************************

   TASK [debug] *******************************************************************
   ok: [localhost] => {
       "msg": "Thank you, my friend!"
   }

   PLAY RECAP *********************************************************************
   localhost                  : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

   INFO:root:Waiting for event

We can see from the output above, that the condition was met from the
webhook and ansible-rulebook then triggered our action which was to
run_playbook. The playbook we defined is then triggered and once it
completes we can see we revert back to “Waiting for event”.

Event-Driven Ansible opens up the possibilities of faster resolution and
greater automated observation of our environments. It has the
possibility of simplifying the lives of many technical and
sleep-deprived engineers.


Extras
------

Video: `Writing Rulebooks <https://www.youtube.com/watch?v=PtevBKX1SYI>`__
