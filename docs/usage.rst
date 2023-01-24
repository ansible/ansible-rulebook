=====
Usage
=====

The `ansible-rulebook` CLI supports the following options::

    optional arguments:
    -h, --help            show this help message and exit
    --rulebook RULEBOOK   The rulebook file or rulebook from a collection
    --vars VARS           Variables file
    --env-vars ENV_VARS   Comma separated list of variables to import from the environment
    --debug               Show debug logging, written to stdout
    --verbose             Show verbose logging, written to stdout
    --version             Show the version and exit
    --redis-host-name REDIS_HOST_NAME
                            Redis host name
    --redis-port REDIS_PORT
                            Redis port
    -S SOURCE_DIR, --source-dir SOURCE_DIR
                            Source dir
    -i INVENTORY, --inventory INVENTORY
                            Inventory
    --websocket-address WEBSOCKET_ADDRESS
                            Connect the event log to a websocket
    --id ID               Identifier
    --worker              Enable worker mode
    --project-tarball PROJECT_TARBALL
                            A tarball of the project
    --controller-url CONTROLLER_URL
                            Controller API base url, e.g. http://host1:8080
    --controller-token CONTROLLER_TOKEN
                            Controller API authentication token
    --print-events        Print events to stdout, disabled if used with --debug

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
