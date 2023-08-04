.. _rulebook-collections:

========================
Rulebook and Collections
========================

It's entirely possible to build and track simple Rulebooks and Playbooks in source repos. If you find yourself building more complex
and repeatable rulebooks that depends on other content, capabilities, or modules then you may want to consider packaging them into 
a `Collection <https://docs.ansible.com/ansible/latest/collections_guide/index.html>`_ 

Collections are an existing Ansible packaging concept that have been extended to support Ansible Rulebook Content. Rulebook Collections
also work particularly well with :ref:`Decision Environments <decision-environment>`

The structure of a Collection with Rulebook content
---------------------------------------------------

Collections already have an `existing structure <https://docs.ansible.com/ansible/latest/dev_guide/developing_collections_structure.html>`_
supporting Ansible Roles, Modules, Plugins, and Documentation. Lets look at what we can add to that structure to support ansible-rulebook content::

    collection/
    ├ ...
    ├── extensions/
    │   ├── eda/
    │   │   ├── rulebooks/
    │   │   └── plugins/
    │   │       ├── event_source/
    │   │       └── event_filter/
    └ ...

There's more to a collection but these are the things added to a collection that ansible-rulebook itself is looking for. You can and will put
roles, playbooks, and other content in the collection as well. Especially if you will be calling them and making use of them from your rulebooks.

You'll initialize the Collection the same way you would any other collection::

    ansible-galaxy collection init my_collection

Then you can add the directories above and start populating it with content.

Not every Collection you write will have its own plugins but if you find yourself building your own :ref:`event sources <event-source-plugins>`
or :ref:`event filters <event-filter>` then you'll want to put them in the collection as shown above.

Using a rulebook included in a collection
-----------------------------------------

The ansible-rulebook command can take a path to a rulebook file directly but once you've put a rulebook into a collection and it's available in
the environment then you can refer to it by its fully qualified name::

    ansible-rulebook -r my_namespace.my_collection.my_rulebook

.. note::
    For more details on how to build, and publish collections see
    the `Developing Ansible Collections <https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html>`_ documentation.
