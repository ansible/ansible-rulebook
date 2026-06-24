.. _plugin-lifecycle:

================
Plugin Lifecycle
================

Event-Driven Ansible (EDA) plugins follow a defined lifecycle to ensure smooth transitions as plugins evolve, are replaced, or removed. This lifecycle management helps collection maintainers communicate changes to users while maintaining backward compatibility during migration periods.

Understanding the Plugin Lifecycle
===================================

Ansible-rulebook supports the following stages of a plugin's lifecycle: :ref:`deprecation <deprecating-plugin>`, :ref:`removal (tombstone) <tombstoning-plugin>`, and :ref:`redirection <redirecting-plugin>`.


Deprecation
----------

When a plugin needs to be replaced or significantly changed, it enters the deprecation stage. Deprecated plugins:

* Continue to function normally
* Display deprecation warnings when used
* Indicate in which version, or when, they will be removed
* Provide guidance on migration alternatives
* Remain in the collection for a transition period

Removal (Tombstoning)
--------------------

After the deprecation period, plugins are removed from the collection. A tombstone entry:

* Raises an exception
* Displays a clear error message when attempted
* Indicates the plugin has been removed
* May reference a replacement plugin

Redirection
----------

Plugin redirection allow seamless renaming or moving of plugins. When a plugin is redirected:

* The old plugin name automatically resolves to the new plugin
* No warning is displayed (unless the target is also deprecated)
* Users can continue using the old name during migration
* The redirect can point to a plugin in a different collection

Configuring Plugin Lifecycle in Collections
============================================

A collection defines the lifecycle of the plugins contained using a metadata file located at ``extensions/eda/eda_runtime.yml``. This file uses the ``plugin_routing`` section to define deprecations, redirections, and tombstones.


The ``eda_runtime.yml`` file uses this structure:

.. code-block:: yaml

    plugin_routing:
      event_source:
        plugin_name:
          # Lifecycle configuration here
      event_filter:
        plugin_name:
          # Lifecycle configuration here

Deprecating a Plugin
====================

To deprecate a plugin, add a ``deprecation`` entry with removal information and a warning message.

Event Source Example
--------------------

.. code-block:: yaml

    plugin_routing:
      event_source:
        old_webhook:
          deprecation:
            removal_version: "2.0.0"
            warning_text: |
              Please migrate to the webhook_listener source which provides
              improved performance and additional features.

Event Filter Example
--------------------

.. code-block:: yaml

    plugin_routing:
      event_filter:
        legacy_filter:
          deprecation:
            removal_version: "3.0.0"
            warning_text: |
              Use the json_filter from eda.builtin for better
              JSON handling capabilities.

Deprecation Fields
------------------

``removal_version``
    The collection version when the plugin will be removed.

``removal_date``
    An ISO 8601 date (YYYY-MM-DD) when the plugin will be removed.

.. note::
    At least one of ``removal_version`` or ``removal_date`` must be specified. If both are provided, ``removal_date`` will be used.

``warning_text`` (required)
    A message explaining why the plugin is deprecated and what users should use instead.

When a user runs a rulebook using a deprecated plugin, they will see a warning like:

.. code-block:: text

    my_namespace.my_collection.old_webhook has been deprecated. The old_webhook
    source is deprecated and will be removed in version 2.0.0. Please migrate to
    the webhook_listener source which provides improved performance and additional
    features. This feature will be removed from event source 'old_webhook' in
    collection 'my_namespace.my_collection' version 2.0.0.

Redirecting a Plugin
====================

Plugin redirection allow you to rename plugins or move them to different collections while maintaining backward compatibility.

Simple Redirect/Rename
---------------

.. code-block:: yaml

    plugin_routing:
      event_source:
        old_name:
          redirect: my_namespace.my_collection.new_name

The redirect target must be a fully qualified collection name (FQCN) in the format ``namespace.collection.plugin_name``. It can point to a plugin in either the current collection or a different one.

Redirect with Deprecation
--------------------------

You can combine redirection with deprecation warnings:

.. code-block:: yaml

    plugin_routing:
      event_source:
        old_webhook:
          redirect: my_namespace.my_collection.webhook_listener
          deprecation:
            removal_version: "2.0.0"
            warning_text: |
              Please update your rulebooks to use the new plugin name.

This configuration:

1. Redirects ``old_webhook`` to ``webhook_listener``
2. Displays a deprecation warning when the old name is used
3. Continues to work until version 2.0.0

Redirect Chains
---------------

Ansible-rulebook follows redirect chains automatically. If plugin A redirects to B, and B redirects to C, users can reference plugin A and it will resolve to C.

.. note::
    ansible-rulebook follows at most 10 redirections


Tombstoning a Plugin
====================

After a plugin is removed, add a tombstone entry to ``eda_runtime.yml``. This prevents usage and provides clear error messages:


.. code-block:: yaml

    plugin_routing:
      event_source:
        removed_webhook:
          tombstone:
            removal_version: "2.0.0"
            warning_text: |
              Use webhook_listener instead.

Tombstone Fields
----------------

``removal_version``
    The collection version when the plugin was removed.

``removal_date``
    An ISO 8601 date (YYYY-MM-DD) when the plugin was removed.

.. note::
    At least one of ``removal_version`` or ``removal_date`` must be specified. If both are provided, ``removal_date`` will be used.

``warning_text`` (required)
    A message explaining the removal and suggesting alternatives.

When a user attempts to use a tombstoned plugin, ansible-rulebook raises an error:

.. code-block:: text

    SourcePluginNotFoundException: The my_namespace.my_collection.removed_webhook
    event source has been removed. The removed_webhook source has been removed.
    Use webhook_listener instead.

Complete Migration Example
===========================

Here's a complete example showing the lifecycle of renaming an event source from ``old_webhook`` to ``webhook_listener``:

**Version 1.5.0 - Introduce Redirect with Deprecation**

.. code-block:: yaml

    plugin_routing:
      event_source:
        old_webhook:
          redirect: my_namespace.my_collection.webhook_listener
          deprecation:
            removal_version: "2.0.0"
            warning_text: |
              The old_webhook source is deprecated and has been renamed
              to webhook_listener. Please update your rulebooks.

**Version 2.0.0 - Replace with Tombstone**

.. code-block:: yaml

    plugin_routing:
      event_source:
        old_webhook:
          tombstone:
            removal_version: "2.0.0"
            warning_text: |
              The old_webhook source has been removed.
              Use webhook_listener instead.


Technical Details
=================

Legacy Mappings
---------------

Ansible-rulebook maintains built-in legacy mappings for backward compatibility with older plugin names. These are checked before ``eda_runtime.yml`` routing:

.. code-block:: python

    # Event sources
    ansible.eda.range → eda.builtin.range
    ansible.eda.generic → eda.builtin.generic
    ansible.eda.pg_listener → eda.builtin.pg_listener

    # Event filters (partial list)
    ansible.eda.json_filter → eda.builtin.json_filter
    ansible.eda.normalize_keys → ansible.builtin.normalize_keys

Order of Operations
-------------------

When resolving a plugin name, ansible-rulebook follows this order:

1. Check built-in legacy mappings
2. Load ``eda_runtime.yml`` from the plugin's collection
3. Check for deprecation (log warning if present)
4. Check for tombstone (raise error if present)
5. Check for redirect (follow to new plugin)
6. Repeat steps 2-5 for each redirect in the chain (max 10 hops)

See Also
========

* :ref:`rulebook-collections` - Collection structure and usage
* :doc:`sources` - Event source plugins
* :doc:`filters` - Event filter plugins

