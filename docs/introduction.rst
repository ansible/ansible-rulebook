Introduction
====================

What is Event-Driven Ansible?
-----------------------------

Event-Driven Ansible is a new way to enhance and expand automation. It
improves IT speed and agility, while enabling consistency and
resilience. The Event-Driven Ansible technology was developed by Red Hat
and is available as a developer preview. Community input is essential.
Since we are building a solution to best meet your needs, we're
providing an opportunity for you to advocate for those needs.

Event-Driven Ansible is designed for simplicity and flexibility. By
writing an Ansible Rulebook (similar to Ansible Playbooks, but more
oriented to “if-then” scenarios) and allowing Event-Driven Ansible to
subscribe to an event listening source, your teams can more quickly and
easily automate a variety of tasks across the organization. EDA is
providing a way of codifying operational logic.

Why Event-Driven?
-----------------

Automation allows us to give our systems and technology speed and
agility while minimizing human error. However, when it comes to trouble
tickets and issues, we are often left to traditional and often manual
methods of troubleshooting and information gathering. We inherently slow
things down and interrupt our businesses. We have to gather information,
try our common troubleshooting steps, confirm with different teams.

One application of Event-Driven Ansible is to codify this operation
knowledge in order to remediate technology issues near real-time, or at
least trigger troubleshooting and information collection in an attempt
to find the root cause of an outage while your support teams handle
other issues.

Event-Driven Ansible has the potential to change the way we respond to
issues and illuminates many new automation possibilities.

It opens up the possibilities of faster resolution and greater automated
observation of our environments.


Why Rulebooks?
--------------

Event-Driven Ansible contains a decision framework that was built using
Drools. We need a rulebook to tell the system what events to flag and
how to respond to them. These rulebooks are also created in YAML and are
used like traditional Ansible Playbooks, so this makes it easier to
understand and build the rulebooks we need. One key difference between
playbooks and rulebooks is the If-this-then-that coding that is needed
in a rulebook to make an event driven automation approach work.


**A rulebook is comprised of three main components:**

-  **Sources** define which event source we will use. These sources come
   from source plugins which have been built to accommodate common use
   cases. With time, more and more sources will be available. There are
   some source plugins that are available already, including: webhooks,
   Kafka, Azure service bus, file changes, and alertmanager.

-  **Rules** define conditionals we will try to match from the event
   source. Should the condition be met, then we can trigger an action.

-  **Actions** trigger what you need to happen should a condition be
   met. Some of the current actions are: run_playbook, run_module,
   set_fact, post_event, debug.

So to summarize:

**Events are processed by a rules engine**

-  Rules trigger based on conditions and actions can be carried out by
   the rules engine
-  Rules are organized into Ansible Rulebooks
-  Ansible rules can apply to events occurring on specific hosts or
   groups

**Conditional management of actions to events**

-  Simple YAML structure for logical conditions
-  Events can trigger different types of actions:
-  Run Ansible Playbooks
-  Run Modules directly
-  Post new events to the event handler

**YAML-like format familiarity**

-  Current Ansible users quickly learn and use Rulebook writing


Getting started
---------------
See `Getting Started <getting_started.html>`_


Other Resources
---------------

Whether you are beginning your automation journey or a seasoned veteran,
there are a variety of resources to enhance your automation knowledge:

-  `Self-paced lab
   exercises <https://www.redhat.com/en/engage/redhat-ansible-automation-202108061218>`__
   - We have interactive, in-browser exercises to help you get started
   with Event-Driven Ansible and ansible-rulebook.
-  `Event-Driven Ansible web page <https://ansible.com/event-driven>`__
-  `Introducing Event-Driven Ansible
   blog <https://www.ansible.com/blog/introducing-event-driven-ansible>`__
-  `Why Event-Driven
   Matters <https://www.ansible.com/blog/why-event-driven-matters>`__ -
   Have a look at another blog about why Event-Driven Ansible matters.
-  `Event-Driven Rulebooks <https://youtu.be/PtevBKX1SYI>`__ - Watch
   another example of Event-Driven Ansible on our YouTube channel.
-  `EDA and Gitops <https://youtu.be/Bb51DftLbPE>`__ - Watch another
   example of Event-Driven Ansible, but with GitOps, on our YouTube
   channel.
-  Learn more about Event-Driven Ansible at our office hours `December
   14,
   2022 <https://www.redhat.com/en/events/webinar/event-driven-ansible-office-hours-december>`__.
-  `Ansible Rulebook
   CLI <https://github.com/ansible/ansible-rulebook>`__

Office Hours
------------

Join us for Office Hours on the Event-Driven Ansible developer preview
on December 14th at 11AM ET. Get some tips and techniques, ask questions
and share your feedback! Learn from the community. See you there.
https://www.ansible.com/resources/webinars-training/event-driven-ansible-office-hours-dec


