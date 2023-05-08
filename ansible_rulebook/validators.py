import json
import logging
import sys
from typing import ClassVar, Dict, List

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import jsonschema
from jsonschema.exceptions import SchemaError, ValidationError

DEFAULT_RULEBOOK_SCHEMA = "ruleset_schema"
logger = logging.getLogger(__name__)


class Validate:
    schema: ClassVar[Dict] = None

    @classmethod
    def _get_schema(cls):
        if cls.schema:
            return cls.schema

        path = resources.files(__package__).joinpath(
            f"./schema/{DEFAULT_RULEBOOK_SCHEMA}.json"
        )
        data = path.read_text(encoding="utf-8")
        try:
            cls.schema = json.loads(data)
            validator = jsonschema.validators.validator_for(cls.schema)
            validator.check_schema(cls.schema)
        except json.JSONDecodeError as err:
            logger.error("Can not deserialize JSON schema: %s", str(err))
            raise
        except SchemaError as err:
            logger.error("Incorrect JSON schema: %s", str(err))
            raise
        return cls.schema

    @classmethod
    def rulebook(cls, instance: List[Dict]) -> None:
        try:
            jsonschema.validate(instance=instance, schema=cls._get_schema())
        except ValidationError as err:
            logger.error("Rulebook failed validation, err %s", str(err))
            raise
