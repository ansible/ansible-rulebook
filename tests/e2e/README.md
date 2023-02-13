# E2E test suite for ansible-rulebook

## Install

*Requirements*: A working installation of ansible-rulebook see [official documentation for more details](https://ansible-rulebook.readthedocs.io/en/latest/installation.html).

```sh
git clone git@github.com:ansible/ansible-rulebook.git
pip install -r requirements_test.txt
```

## Usage

```sh
pytest -m e2e -n auto
```

## Configuration

Configuration is managed by [dynaconf library](https://www.dynaconf.com/)

Default configuration is located in `tests/e2e/config/default.yml`
You can use your custom configuration file by setting `EDA_E2E_SETTINGS` environment variable:

```sh
export EDA_E2E_SETTINGS=/path/to/your/config.yml
```

You can also override configuration by setting environment variables with the name of the configuration key in uppercase and prefixed by `EDA_E2E_`:

```sh
export EDA_E2E_CMD_TIMEOUT=60
```
