=======
Actions
=======

Event driven automation supports several built-in actions that can be run from rules.  These are:

    * run_playbook - run a playbook using ansible-runner
    * set_fact - set a long term fact
    * retract_fact - remove a long term fact
    * post_event - send a new short term event to the rule engine
    * debug - print the current event and facts along with any variables and arguments to the action
    * print_event - print the data from the matching event
    * noop - do nothing
    * shutdown - shutdown the rule engine and terminate `ansible-rulebook`

