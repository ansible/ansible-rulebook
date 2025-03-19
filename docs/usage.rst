=====
Usage
=====

The `ansible-rulebook` CLI supports the following options:

.. code-block:: console

    usage: ansible-rulebook [-h] [-r RULEBOOK] [-e VARS] [-E ENV_VARS] [-v] [--version] [-S SOURCE_DIR] [-i INVENTORY]
                        [-W WEBSOCKET_URL] [--websocket-ssl-verify WEBSOCKET_SSL_VERIFY]
                        [--websocket-access-token WEBSOCKET_ACCESS_TOKEN]
                        [--websocket-refresh-token WEBSOCKET_REFRESH_TOKEN]
                        [--websocket-token-url WEBSOCKET_TOKEN_URL] [--id ID] [-w] [-T PROJECT_TARBALL]
                        [--controller-url CONTROLLER_URL] [--controller-token CONTROLLER_TOKEN]
                        [--controller-username CONTROLLER_USERNAME] [--controller-password CONTROLLER_PASSWORD]
                        [--controller-ssl-verify CONTROLLER_SSL_VERIFY] [--print-events]
                        [--shutdown-delay SHUTDOWN_DELAY] [--gc-after GC_AFTER] [--heartbeat HEARTBEAT]
                        [--execution-strategy {sequential,parallel}] [--hot-reload] [--skip-audit-events]
                        [--vault-password-file VAULT_PASSWORD_FILE] [--vault-id VAULT_ID] [--ask-vault-pass]

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
                            Local event source plugins dir for development.
    -i INVENTORY, --inventory INVENTORY
                            Path to an inventory file, can also be passed via the env var ANSIBLE_INVENTORY
    -W WEBSOCKET_URL, --websocket-url WEBSOCKET_URL, --websocket-address WEBSOCKET_URL
                            Connect the event log to a websocket, can also be passed via the env var EDA_WEBSOCKET_URL.
    --websocket-ssl-verify WEBSOCKET_SSL_VERIFY
                            How to verify SSL when connecting to the websocket: (yes|true) | (no|false) | <path to a CA bundle>, default to yes for wss connection, can also be passed via the env var EDA_WEBSOCKET_SSL_VERIFY.
    --websocket-access-token WEBSOCKET_ACCESS_TOKEN
                            Token used to autheticate the websocket connection, can also be passed via the env var EDA_WEBSOCKET_ACCESS_TOKEN
    --websocket-refresh-token WEBSOCKET_REFRESH_TOKEN
                            Token used to renew a websocket access token, can also be passed via the env var EDA_WEBSOCKET_REFRESH_TOKEN
    --websocket-token-url WEBSOCKET_TOKEN_URL
                            Url to renew websocket access token, can also be passed via the env var EDA_WEBSOCKET_TOKEN_URL
    --id ID               Identifier, the activation_instance id which allows the results to be communicated back to the websocket.
    -w, --worker          Enable worker mode
    -T PROJECT_TARBALL, --project-tarball PROJECT_TARBALL
                            A tarball of the project
    --controller-url CONTROLLER_URL
                            Controller API base url, e.g. https://host1:8080 can also be passed via the env var EDA_CONTROLLER_URL, if your URL has a path it should include api in it. api would only be appended if the URL only contains host, port.
    --controller-token CONTROLLER_TOKEN
                            Controller API authentication token, can also be passed via env var EDA_CONTROLLER_TOKEN
    --controller-username CONTROLLER_USERNAME
                            Controller API authentication username, can also be passed via env var EDA_CONTROLLER_USERNAME
    --controller-password CONTROLLER_PASSWORD
                            Controller API authentication password, can also be passed via env var EDA_CONTROLLER_PASSWORD
    --controller-ssl-verify CONTROLLER_SSL_VERIFY
                            How to verify SSL when connecting to the controller: (yes|true) | (no|false) | <path to a CA bundle>, default to yes for https connection, can also be passed via env var EDA_CONTROLLER_SSL_VERIFY
    --print-events        Print events to stdout, redundant and disabled with -vv
    --shutdown-delay SHUTDOWN_DELAY
                            Maximum number of seconds to wait after issuing a graceful shutdown, default: 60. The process will shutdown if all actions complete before this time period. Can also be passed via the env var EDA_SHUTDOWN_DELAY
    --gc-after GC_AFTER   Run the garbage collector after this number of events. It can be configured with the environment variable EDA_GC_AFTER
    --heartbeat HEARTBEAT
                            Send heartbeat to the server after every n secondsDefault is 0, no heartbeat is sent
    --execution-strategy {sequential,parallel}
                            Actions can be executed in sequential order or in parallel.Default is sequential, actions will be run only after the previous one ends
    --hot-reload          Will perform hot-reload on rulebook file changes (when running in non-worker mode).This option is ignored in worker mode.
    --skip-audit-events   Don't send audit events to the server
    --vault-password-file VAULT_PASSWORD_FILE
                            The file containing one ansible vault password, can also be passed via the env var EDA_VAULT_PASSWORD_FILE.
    --vault-id VAULT_ID   label@filename pointing to an ansible vault password file
    --ask-vault-pass      Ask vault password interactively 

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
