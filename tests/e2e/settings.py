import os

import dynaconf

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(HERE, "config")
DEFAULT_CONFIG_FILE = "default.yml"


def get_settings() -> dynaconf.LazySettings:
    """
    Get the settings.
    """
    return dynaconf.LazySettings(
        environments=False,
        load_dotenv=True,
        envvar="EDA_E2E_SETTINGS",
        envvar_prefix="EDA_E2E",
        root_path=DEFAULT_CONFIG_PATH,
        settings_file=DEFAULT_CONFIG_FILE,
    )


SETTINGS = get_settings()
