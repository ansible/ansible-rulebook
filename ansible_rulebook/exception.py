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

    pass


class SourceFilterNotFoundException(Exception):

    pass


class SourcePluginMainMissingException(Exception):

    pass


class SourcePluginNotAsyncioCompatibleException(Exception):

    pass


class ControllerNeededException(Exception):

    pass


class InvalidFilterNameException(Exception):

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
