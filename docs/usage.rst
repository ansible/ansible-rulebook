=====
Usage
=====


`ansible-events` is either used as a command line tool or used as a web service with `ansible-events-ui`.  

To get help from `ansible-events` run the following::

    ansible-events --help

The normal method for running `ansible-events` is the following::

    ansible-events --inventory inventory.yml --rules rules.yml

If you are using custom event source plugins use the following::


    ansible-events --inventory inventory.yml --rules rules.yml -S sources/

Here `sources` is a directory containing your event source plugins.
