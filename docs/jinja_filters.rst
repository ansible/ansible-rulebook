=============
Jinja Filters
=============

Jinja filters provide a way to transform and manipulate data in actions within your rulebooks.
These filters can be used to format strings, extract parts of file paths, and perform regex
replacements on event data before it is used in actions.

.. note::
    Jinja filters can be used in **actions** in rulebooks, but **cannot** be used in **conditions**.
    Conditions must use the native condition operators and tests provided by the rule engine.

Usage in Actions
****************

Jinja filters are used in actions with the standard Jinja2 syntax using the pipe (``|``) operator.
You can chain multiple filters together to perform complex transformations.

Example:

.. code-block:: yaml

    action:
      debug:
        msg: "{{ event.name | upper | replace('HELLO', 'GOODBYE') }}"

Available Filters
*****************

ansible-rulebook provides custom Jinja filters in addition to all standard Python string methods
and built-in Jinja2 filters. The custom filters are:

* regex_replace
* basename
* dirname
* normpath

regex_replace
-------------

Perform a regex substitution on a string value.

.. list-table::
   :widths: 25 150 10
   :header-rows: 1

   * - Parameter
     - Description
     - Required
   * - pattern
     - The regular expression pattern to search for
     - Yes
   * - replacement
     - The replacement string
     - Yes
   * - count
     - Maximum number of occurrences to replace (0 means replace all). Default: 0
     - No
   * - ignore_case
     - Perform case-insensitive matching. Default: false
     - No
   * - multiline
     - Enable multiline mode for regex. Default: false
     - No
   * - mandatory_count
     - Minimum number of replacements required (raises error if not met). Default: 0
     - No

Examples:

.. code-block:: yaml

    action:
      debug:
        msg: "{{ event.name | regex_replace('host1', 'host195') }}"

.. code-block:: yaml

    action:
      post_event:
        event:
          msg: "{{ event.name | regex_replace('Bamm', 'Betty', count=1) }}"

basename
--------

Extract the basename (filename) from a file path.

Examples:

.. code-block:: yaml

    # Input: "/etc/certs/cert.pem"
    # Output: "cert.pem"
    action:
      debug:
        msg: "{{ event.filepath | basename }}"

.. code-block:: yaml

    action:
      post_event:
        event:
          basename: "{{ event.filename | normpath | basename }}"

dirname
-------

Extract the directory name from a file path.

Examples:

.. code-block:: yaml

    # Input: "/etc/certs/cert.pem"
    # Output: "/etc/certs"
    action:
      debug:
        msg: "{{ event.filepath | dirname }}"

.. code-block:: yaml

    # Chaining filters: first normalize, then get dirname
    action:
      post_event:
        event:
          dirname: "{{ event.filename | normpath | dirname }}"

.. note::
    If only a filename without a path is provided, dirname returns an empty string.

normpath
--------

Normalize a file path by collapsing redundant separators and up-level references.

Examples:

.. code-block:: yaml

    # Input: "/abc//def//jhk/test.txt"
    # Output: "/abc/def/jhk/test.txt"
    action:
      debug:
        msg: "{{ event.filepath | normpath }}"

.. code-block:: yaml

    action:
      post_event:
        event:
          normal: "{{ event.filename | normpath }}"

Python String Methods
**********************

In addition to the custom filters above, all Python string methods are available as filters.
Common examples include:

* **upper** - Convert to uppercase
* **lower** - Convert to lowercase
* **capitalize** - Capitalize first character
* **replace(old, new)** - Replace occurrences of a substring
* **split(separator)** - Split string into a list

Examples:

.. code-block:: yaml

    action:
      debug:
        msg:
          - "{{ event.name | replace('.com', '') }}"
          - "{{ event.name.split('.') | first }}"
          - "{{ event.name | capitalize }}"

Chaining Filters
****************

Filters can be chained together by using multiple pipe operators. Each filter processes
the output of the previous filter in the chain.

Example:

.. code-block:: yaml

    action:
      post_event:
        event:
          # First normalize the path, then get the directory, then convert to uppercase
          clean_dir: "{{ event.filename | normpath | dirname | upper }}"

Complete Examples
*****************

Example 1: String manipulation with regex and string methods
-------------------------------------------------------------

.. code-block:: yaml

    ---
    - name: 97 jinja
      hosts: all
      sources:
        - eda.builtin.generic:
            payload:
               - name: "host1.net"
               - name: "Bamm Bamm Rubble"
            create_index: index
            shutdown_delay: 5
      rules:
        - name: regex rule
          condition: event.name is regex("host")
          actions:
            - debug:
                msg:
                  - "{{ event.name | replace('.com', '') }}"
                  - "{{ event.name.split('.') | first }}"
                  - "{{ event.name | capitalize }}"
                  - "{{ event.name | regex_replace('host1', 'host195') }}"
        - name: original event
          condition: event.name == "Bamm Bamm Rubble"
          actions:
            - post_event:
                 event:
                    msg: "{{ event.name | regex_replace('Bamm', 'Betty', count=1) }}"
        - name: posted event
          condition: event.msg == "Betty Bamm Rubble"
          action:
            print_event:

Example 2: File path manipulation
----------------------------------

.. code-block:: yaml

    ---
    - name: 98 jinja files
      hosts: all
      sources:
        - eda.builtin.generic:
            payload:
               - filename: "/abc//def//jhk/test.txt"
            create_index: index
            shutdown_delay: 5
      rules:
        - name: basename
          condition: event.basename == "test.txt"
          actions:
            - print_event:
        - name: dirname
          condition: event.dirname == "/abc/def/jhk"
          actions:
            - print_event:
        - name: normpath
          condition: event.normal == "/abc/def/jhk/test.txt"
          actions:
            - print_event:
        - name: catch_all
          condition: true
          actions:
            - post_event:
                event:
                  normal: "{{ event.filename | normpath }}"
            - post_event:
                event:
                  dirname: "{{ event.filename | normpath | dirname }}"
            - post_event:
                event:
                  basename: "{{ event.filename | normpath | basename }}"

Built-in Jinja2 Filters
***********************

ansible-rulebook also supports standard Jinja2 filters. Some commonly used ones include:

* **default(value)** - Provide a default value if the variable is undefined
* **first** - Get the first item from a list
* **last** - Get the last item from a list
* **length** - Get the length of a list or string
* **join(separator)** - Join a list into a string

For a complete list of Jinja2 filters, see the `Jinja2 documentation <https://jinja.palletsprojects.com/en/latest/templates/#list-of-builtin-filters>`_.

Example:

.. code-block:: yaml

    action:
      debug:
        msg: "{{ event.items | default([]) | length }}"

FAQ
***

| **Q:** Can I use Jinja filters in conditions?

| **Ans:** No, Jinja filters cannot be used in conditions. Conditions use the rule engine's native
| operators and tests. You can only use Jinja filters in actions to transform data before using it.

| **Q:** What happens if a Jinja filter receives a None value?

| **Ans:** The custom filters (regex_replace, basename, dirname, normpath) handle None values
| gracefully by returning an empty string. For other filters, you should use the ``default`` filter
| to provide a fallback value.

| **Q:** Can I create custom Jinja filters?

| **Ans:** Currently, ansible-rulebook provides the four custom filters listed above. For other
| transformations, you can use Python string methods, built-in Jinja2 filters, or chain multiple
| filters together.

| **Q:** How do I handle errors in regex_replace?

| **Ans:** You can use the ``mandatory_count`` parameter to ensure a minimum number of replacements
| occur. If the mandatory count is not met, an error will be raised. Without this parameter, the
| filter will return the original string if no matches are found.
