=====
Usage
=====


`ansible-rulebook` is either used as a command line tool or used as a web service with `ansible-rulebook-ui`.  

To get help from `ansible-rulebook` run the following::

    ansible-rulebook --help

The normal method for running `ansible-rulebook` is the following::

    ansible-rulebook --inventory inventory.yml --rules rules.yml

If you are using custom event source plugins use the following::


    ansible-rulebook --inventory inventory.yml --rules rules.yml -S sources/

Here `sources` is a directory containing your event source plugins.
