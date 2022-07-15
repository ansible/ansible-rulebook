=====
Rules
=====

Event driven automation uses rules to determine if an action should be taken when an event
is received.  The rule decides to run an action by using a condition that is supplied
by the user.   This condition can use information from the event received, information
from recently previous events, longer term facts about the system, or variables provided
by the user.

The following is an example rule::

    name:  An automatic remedation rule
    condition:  event.outage == True
    action:
        run_playbook:
            name: remediate_outage.yml

This rule searches for a recent event with the data `outage` being `True`. If an event
with this condition is found then the `remediate_outage.yml` playbook is run.





