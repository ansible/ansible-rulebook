=====
Usage
=====


`ansible-rulebook` is either used as a command line tool or used as a web service with `ansible-rulebook-ui`.


The `ansible-rulebook` CLI supports the following options::

    Options:
    -h, --help                  Show this page
    -i, --inventory=<i>         Inventory
    --rulebook=<r>              The rulebook file or rulebook from a collection
    -S=<S>, --source_dir=<S>    Source dir
    --vars=<v>                  Variables file
    --env-vars=<e>              Comma separated list of variables to import
                                from the environment
    --debug                     Show debug logging, writes to stdout
    --verbose                   Show verbose logging, overwrites debug writes to stdout
    --print_events              Print events after reading from source queue
    --version                   Show the version and exit
    --websocket-address=<w>     Connect the event log to a websocket
    --id=<i>                    Identifier
    --worker                    Enable worker mode
    --project-tarball=<p>       Project tarball
    --controller_url=<u>        Controller API base url, e.g. http://host1:8080
    --controller_token=<t>      Controller API authentication token

To get help from `ansible-rulebook` run the following:

.. code-block:: console

    ansible-rulebook --help

To check the version of `ansible-rulebook` run the following:

.. code-block:: console

    ansible-rulebook --version

The normal method for running `ansible-rulebook` is the following:

.. code-block:: console

    ansible-rulebook --inventory inventory.yml --rulebook rules.yml --vars vars.yml

.. note::
    The `--rulebook` option requires the `--inventory` option. The `--vars` option is not required.

If you are using custom event source plugins use the following:

.. code-block:: console

    ansible-rulebook --inventory inventory.yml --rulebook rules.yml -S sources/

.. note::
    Here `sources` is a directory containing your event source plugins.

To run `ansible-rulebook` with worker mode enabled the `--worker` option can be used. The `--id`, and `--websocket-address` options can also be used to expose the event stream data::

    ansible-rulebook --rulebook rules.yml --inventory inventory.yml --websocket-address "ws://localhost:8080/api/ws2" --id 1 --worker

.. note::
    The `id` is the `activation_instance` id which allows the results to be communicated back to the websocket.
    The `--project-tarball` option can also be useful during development.

The `--verbose` and `--debug` options can be added to any of the above commands to increase the logging output.
