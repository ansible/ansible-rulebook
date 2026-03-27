"""
Persistence module for ansible-rulebook.

This module provides functionality for enabling and managing persistence
of rulebook execution state using either PostgreSQL or H2 databases.
It supports high availability (HA) mode by storing action states and
enabling leader election among multiple rulebook instances.
"""

import argparse
import json
import logging
from typing import Dict, Optional

import dpath
from drools import ruleset as lang

from ansible_rulebook.conf import settings
from ansible_rulebook.util import strtobool

logger = logging.getLogger(__name__)

# Required configuration keys for PostgreSQL database connection
POSTGRES_REQUIRED_KEYS = {
    "drools_db_host",
    "drools_db_port",
    "drools_db_name",
}

# Required configuration keys for H2 embedded database
H2_REQUIRED_KEYS = {"drools_db_file_path"}


def enable_persistence(
    parsed_args: argparse.Namespace, variables: Dict
) -> None:
    """
    Enable persistence for the rulebook execution.

    This function initializes the high availability (HA) mode with database
    persistence for storing rulebook state. It supports both PostgreSQL and
    H2 databases.

    Args:
        parsed_args: Command-line arguments containing persistence_id and id
        variables: Dictionary containing database connection parameters

    Returns:
        None. Sets settings.persistence_enabled if successful.
    """
    # Reset persistence_enabled to False at the start to ensure clean state
    # This is important for test isolation when multiple tests run in sequence
    settings.persistence_enabled = False

    if parsed_args is None:
        return
    if parsed_args.persistence_id is None:
        return
    # Try to get database parameters, first from PostgreSQL config, then H2
    db_params = _get_postgres_params(variables) or _get_h2_params(variables)
    if db_params is None:
        # No valid database configuration found, persistence remains disabled
        return

    # This should be a UUID but the backend currently does not
    # use UUID's it uses integer ids
    activation_uuid = f"{parsed_args.persistence_id}"
    worker_name = f"instance-{parsed_args.id}"

    # Get additional configuration parameters like sync intervals
    # and encryption
    config = _get_config_params(variables)

    logger.info(
        "Initializing drools HA mode: worker_id=%s, database=%s, ha_uuid=%s",
        activation_uuid,
        db_params["db_type"],
        activation_uuid,
    )

    # Initialize the high availability system in the drools engine
    lang.initialize_ha(
        uuid=activation_uuid,
        worker_name=worker_name,
        db_params=db_params,
        config=config,
    )
    settings.persistence_enabled = True


def update_action_info(
    rule_set: str,
    matching_uuid: str,
    index: int,
    info: dict,
    create: bool = False,
) -> None:
    """
    Update or create action information in the persistence store.

    This function stores action execution state in the database, allowing
    actions to be tracked and recovered across rulebook restarts or failover.

    Args:
        rule_set: Name of the ruleset containing the action
        matching_uuid: Unique identifier for the rule matching that
            triggered the action
        index: Index of the action within the rule's action list
        info: Dictionary containing action state information to store
        create: If True, create new action info; if False, update existing

    Returns:
        None. Action info is persisted to the database if persistence
        is enabled.
    """
    if not settings.persistence_enabled:
        return

    if create:
        # Create a new action info record in the database
        lang.add_action_info(rule_set, matching_uuid, index, json.dumps(info))
    else:
        # Update existing action info by merging new data with saved data
        saved_data = lang.get_action_info(rule_set, matching_uuid, index)
        if saved_data is None:
            action_data = {}
        else:
            try:
                action_data = json.loads(saved_data)
            except json.JSONDecodeError as e:
                logger.error("Error parsing saved action data  %s", e.msg)
                action_data = {}

        # Merge the new info into the existing data
        for k, v in info.items():
            action_data[k] = v
        logger.debug("Updating action info %s", action_data)
        lang.update_action_info(
            rule_set, matching_uuid, index, json.dumps(action_data)
        )


def get_action_a_priori(
    rule_set: str, matching_uuid: str, index: int
) -> Optional[dict]:
    """
    Retrieve previously stored action information from persistence.

    This function is used to recover action state from a previous execution,
    which is essential for resuming long-running actions or maintaining state
    across rulebook restarts in HA mode.

    Args:
        rule_set: Name of the ruleset containing the action
        matching_uuid: Unique identifier for the rule matching
        index: Index of the action within the rule's action list

    Returns:
        Dictionary containing the stored action data if it exists,
        empty dict if data exists but is corrupted, or None if no data exists.
    """
    if lang.action_info_exists(rule_set, matching_uuid, index):
        data = lang.get_action_info(rule_set, matching_uuid, index)
        if data is None:
            return {}
        logger.debug("Previous action data %s", data)
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error("Error parsing prior action data  %s", e.msg)
            return {}

    return None


def enable_leader():
    """
    Enable leader election for this rulebook instance.

    In HA mode, this function designates the current instance as eligible
    to become the leader. The leader instance is responsible for coordinating
    distributed rule execution across multiple workers.

    Returns:
        None. Enables leader mode in the drools engine if persistence
        is enabled.
    """
    if settings.persistence_enabled:
        lang.enable_leader()


def _get_postgres_params(variables: dict) -> Optional[dict]:
    """
    Extract PostgreSQL connection parameters from variables.

    This function validates that required PostgreSQL connection parameters
    are present and constructs a connection parameter dictionary including
    optional SSL and authentication settings.

    Args:
        variables: Dictionary containing configuration variables

    Returns:
        Dictionary of PostgreSQL connection parameters if all required keys
        are present, otherwise None.
    """
    # Check if all required PostgreSQL keys are present
    if not POSTGRES_REQUIRED_KEYS <= set(variables.keys()):
        return None

    # Build basic connection parameters
    db_params = {
        "host": variables["drools_db_host"],
        "port": variables["drools_db_port"],
        "database": variables["drools_db_name"],
    }
    db_params["db_type"] = "postgres"

    # Map optional parameters from variables to database parameter names
    # Supports both direct variable names and EDA filename paths
    mappings = {
        "drools_db_user": "user",
        "drools_db_password": "password",
        "drools_sslmode": "sslmode",
        "drools_sslpassword": "sslpassword",
        "eda/filename/drools_sslrootcert": "sslrootcert",
        "eda/filename/drools_sslkey": "sslkey",
        "eda/filename/drools_sslcert": "sslcert",
        "drools_sslcert": "sslcert",
        "drools_sslrootcert": "sslrootcert",
        "drools_sslkey": "sslkey",
    }

    # Add optional parameters if they exist in variables
    for key, mapped_name in mappings.items():
        value = dpath.get(variables, key, default=None)
        if value:
            db_params[mapped_name] = value

    return db_params


def _get_h2_params(variables: dict) -> Optional[dict]:
    """
    Extract H2 database connection parameters from variables.

    H2 is a lightweight embedded database suitable for development and
    single-instance deployments. This function validates and extracts
    the required file path parameter.

    Args:
        variables: Dictionary containing configuration variables

    Returns:
        Dictionary of H2 connection parameters if required keys are present,
        otherwise None.
    """
    # Check if required H2 file path key is present
    if not H2_REQUIRED_KEYS <= set(variables.keys()):
        return None

    return {"db_type": "h2", "db_file_path": variables["drools_db_file_path"]}


def _get_config_params(variables: dict) -> dict:
    """
    Extract additional configuration parameters for HA mode.

    This function builds configuration parameters for the high availability
    system including synchronization intervals, encryption keys, and grace
    periods for expired time windows.

    Args:
        variables: Dictionary containing configuration variables

    Returns:
        Dictionary of configuration parameters with default values for
        sync intervals and optional encryption and grace period settings.
    """
    # Set default synchronization intervals (in milliseconds)
    result = {}

    # Add primary encryption key if provided
    if variables.get("drools_primary_encryption_secret"):
        result["encryption_key_primary"] = variables.get(
            "drools_primary_encryption_secret"
        )

    # Add secondary encryption key if provided (for key rotation)
    if variables.get("drools_secondary_encryption_secret"):
        result["encryption_key_secondary"] = variables.get(
            "drools_secondary_encryption_secret"
        )

    # Add grace period for expired time windows if provided
    if variables.get("drools_expired_window_grace_period"):
        result["expired_window_grace_period"] = int(
            variables.get("drools_expired_window_grace_period")
        )

    # Add overwrite if provided
    if "drools_overwrite_if_rulebook_changes" in variables:
        data = variables.get("drools_overwrite_if_rulebook_changes", False)
        if isinstance(data, bool):
            result["overwrite_if_rulebook_changes"] = data
        else:
            result["overwrite_if_rulebook_changes"] = strtobool(str(data))

    # Add dedup buffer size
    if variables.get("drools_deduplication_window_size"):
        result["dedup_buffer_size"] = int(
            variables.get("drools_deduplication_window_size")
        )
    return result
