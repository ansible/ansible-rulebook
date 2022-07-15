==========
Conditions
==========

In event driven automation a condition determines if a rule fires (runs its action).  Conditions
are written in format that is similar to the conditionals format in `Ansible playbooks`_::

    event.status == "enabled"


Each condition will match one event.  The condition much have a value with the ``event`` prefix
to compare to other variables or values.  The line above can be read as **if you find an event
with status equal to "enabled" then run the action.**

That event will be stored as a variable named ``event`` for the action to access.

Conditions support the following operators:

* ``==`` - equality
* ``>`` - greater than
* ``>=`` - greater than or equal to
* ``<`` - less than
* ``<=`` - less than or equal to
* ``and`` - true if both adjoining statements are true
* ``or`` - true if either adjoining statement is true
* ``is defined`` - true if a value is defined
* ``is not defined`` - true if a value has been removed (does not exist)
* ``+`` - add a value
* ``-`` - subtract a value
* ``{{x}}`` - variable substition for variable ``x``




.. _Ansible playbooks: https://docs.ansible.com/ansible/latest/user_guide/playbooks_conditionals.html


..
