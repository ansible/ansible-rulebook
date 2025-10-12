#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from .messages import Shutdown


class ShutdownException(Exception):
    def __init__(self, shutdown: Shutdown):
        self.shutdown = shutdown

    def __str__(self):
        return str(self.shutdown)


class RulenameEmptyException(Exception):
    pass


class RulesetNameDuplicateException(Exception):
    pass


class RulesetNameEmptyException(Exception):
    pass


class RulenameDuplicateException(Exception):
    pass


class ControllerApiException(Exception):
    pass


class VarsKeyMissingException(Exception):
    pass


class InvalidAssignmentException(Exception):
    pass


class SelectattrOperatorException(Exception):
    pass


class InvalidIdentifierException(Exception):
    pass


class SelectOperatorException(Exception):
    pass


class ConditionParsingException(Exception):
    pass


class InvalidTypeException(Exception):
    pass


class PlaybookStatusNotFoundException(Exception):
    pass


class PlaybookNotFoundException(Exception):
    pass


class InventoryNeededException(Exception):
    pass


class RulebookNotFoundException(Exception):
    pass


class SourcePluginNotFoundException(Exception):
    """Exception class for source plugin not found."""

    def __init__(
        self: "SourcePluginNotFoundException",
        source_name: str,
        message: str = None,
    ) -> None:
        """Class constructor with not found source plugin"""
        if message is None:
            message = (
                f"Could not find source plugin for {source_name}. "
                f"Please ensure that the appropriate Ansible collection is "
                f"installed. If you're running from the CLI, you can use "
                f"the -S option to specify additional source directories."
            )
        super().__init__(message)


class SourceFilterNotFoundException(Exception):
    """Exception class for source filter not found."""

    def __init__(
        self: "SourceFilterNotFoundException",
        source_filter_name: str,
        message: str = None,
    ) -> None:
        """Class constructor with not found source filter"""
        if message is None:
            message = (
                f"Could not find source filter plugin {source_filter_name}"
            )
        super().__init__(message)


class SourcePluginMainMissingException(Exception):
    """Exception class for plugin main function not found."""

    def __init__(
        self: "SourcePluginMainMissingException",
        source_name: str,
        message: str = None,
    ) -> None:
        """Class constructor with not found main function in plugin"""
        if message is None:
            message = (
                f"Entrypoint missing. "
                f"Source module {source_name} must have function 'main'."
            )
        super().__init__(message)


class SourcePluginNotAsyncioCompatibleException(Exception):
    """Exception class for plugin not compatible with asyncio functionality"""

    def __init__(
        self: "SourcePluginNotAsyncioCompatibleException",
        source_name: str,
        message: str = None,
    ) -> None:
        """Class constructor with plugin not compatible with asyncio"""
        if message is None:
            message = (
                f"Entrypoint from {source_name} is not a coroutine "
                f"function."
            )
        super().__init__(message)


class ControllerNeededException(Exception):
    pass


class InvalidFilterNameException(Exception):
    pass


class InvalidSourceNameException(Exception):
    pass


class JobTemplateNotFoundException(Exception):
    pass


class WorkflowJobTemplateNotFoundException(Exception):
    pass


class WebSocketExchangeException(Exception):
    pass


class UnsupportedActionException(Exception):
    pass


class HotReloadException(Exception):
    pass


class InventoryNotFound(Exception):
    pass


class MissingArtifactKeyException(Exception):
    pass


class TokenNotFound(Exception):
    pass


class VaultDecryptException(Exception):
    pass


class AnsibleVaultNotFound(Exception):
    pass


class InvalidUrlException(Exception):
    pass


class ControllerObjectCreateException(Exception):
    pass
