import json
import logging
import sys
from typing import ClassVar, Dict, List

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from jsonschema import validate
from jsonschema.exceptions import ValidationError

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
        cls.schema = json.loads(data)
        return cls.schema

    @classmethod
    def rulebook(cls, instance: List[Dict]) -> None:
        try:
            validate(instance=instance, schema=cls._get_schema())
        except ValidationError:
            logger.exception("Rulebook failed validation.")
            raise
