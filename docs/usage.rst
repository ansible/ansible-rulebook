=====
Usage
=====

The `ansible-rulebook` CLI supports the following options:

.. code-block:: console

    usage: ansible-rulebook [-h] [-r RULEBOOK] [-e VARS] [-E ENV_VARS] [-v] [--version] [-S SOURCE_DIR] [-i INVENTORY] [-W WEBSOCKET_URL] [--websocket-ssl-verify WEBSOCKET_SSL_VERIFY]
                            [--websocket-token-url WEBSOCKET_TOKEN_URL] [--websocket-access-token WEBSOCKET_ACCESS_TOKEN] [--websocket-refresh-token WEBSOCKET_REFRESH_TOKEN]
                            [--id ID] [-w] [-T PROJECT_TARBALL] [--controller-url CONTROLLER_URL] [--controller-token CONTROLLER_TOKEN] [--controller-ssl-verify CONTROLLER_SSL_VERIFY]
                            [--print-events] [--heartbeat n] [--execution-strategy sequential|parallel] [--skip-audit-events]

    optional arguments:
    -h, --help            show this help message and exit
    -r RULEBOOK, --rulebook RULEBOOK
                            The rulebook file or rulebook from a collection
    -e VARS, --vars VARS  Variables file
    -E ENV_VARS, --env-vars ENV_VARS
                            Comma separated list of variables to import from the environment
    -v, --verbose         Causes ansible-rulebook to print more debug messages. Adding multiple -v will increase the verbosity, the default value is 0. The maximum value is 2. Events debugging might require -vv.
    --version             Show the version and exit
    -S SOURCE_DIR, --source-dir SOURCE_DIR
                            Source dir
    -i INVENTORY, --inventory INVENTORY
                            Inventory can be a file or a directory
    -W WEBSOCKET_URL, --websocket-url WEBSOCKET_URL
                            Connect the event log to a websocket
    --websocket-ssl-verify WEBSOCKET_SSL_VERIFY
                            How to verify SSL when connecting to the websocket api. yes|no|<path to a CA bundle>, default to yes for wss connection.
                            Connect the event log to a websocket
    --websocket-token-url WEBSOCKET_TOKEN_URL
                            Fetch a renewed token to authenticate websocket connection
    --websocket-access-token WEBSOCKET_ACCESS_TOKEN
                            Initial token used to authenticate websocket connection
    --websocket-refresh-token WEBSOCKET_REFRESH_TOKEN
                            A token needed to renew an authentication token
    --id ID               Identifier
    -w, --worker          Enable worker mode
    -T PROJECT_TARBALL, --project-tarball PROJECT_TARBALL
                            A tarball of the project
    --controller-url CONTROLLER_URL
                            Controller API base url, e.g. https://host1:8080, can also be passed in via env var EDA_CONTROLLER_URL
    --controller-token CONTROLLER_TOKEN
                            Controller API authentication token, can also be passed in via env var EDA_CONTROLLER_TOKEN
    --controller-ssl-verify CONTROLLER_SSL_VERIFY
                            How to verify SSL when connecting to the controller, yes|no|<path to a CA bundle>, default to yes for https connection. Can also be passed via env var EDA_CONTROLLER_SSL_VERIFY
    --print-events        Print events to stdout, redundant and disabled with -vv
    --shutdown-delay      Maximum number of seconds to wait after a graceful shutdown is issued, default is 60. Can also be set via an env var called EDA_SHUTDOWN_DELAY. The process will shutdown if all actions complete before this time period

    --heartbeat <n> Send heartbeat to the server after every n seconds. Default is 0, no heartbeat is sent

    --execution-strategy sequential|parallel. The default execution strategy is sequential.
    --skip-audit-events  Skip sending audit events to the EDA server, default is false

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

To run `ansible-rulebook` with worker mode enabled the `--worker` option can be used. The `--id`, and `--websocket-url` options can also be used to expose the event stream data::

    ansible-rulebook --rulebook rules.yml --inventory inventory.yml --websocket-url "ws://localhost:8080/api/ws2" --id 1 --worker

.. note::
    The `id` is the `activation_instance` id which allows the results to be communicated back to the websocket.
    The `--project-tarball` option can also be useful during development.

The `-v` or `-vv` options can be added to any of the above commands to increase the logging output.
