import os
from typing import Dict, Optional

import pytest


@pytest.fixture(scope="function")
def update_environment():
    """Fixture factory to update environment variables
    Returns the updated environment variables,
    and restores the original environment variables after the test
    """
    env_backup = os.environ.copy()

    def _update_environment(env: Optional[Dict] = None) -> Dict:
        if env:
            os.environ.update(env)
        return os.environ

    yield _update_environment
    os.environ.clear()
    os.environ.update(env_backup)
