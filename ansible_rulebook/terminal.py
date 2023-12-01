#  Copyright 2023 Red Hat, Inc.
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

import datetime
import logging
import os
import pprint
import threading
import typing

logger = logging.getLogger(__name__)


class _Singleton(type):
    def __init__(cls, name, bases, dct, **kwargs) -> None:
        super().__init__(name, bases, dct, **kwargs)
        cls.__singleton = None
        cls.__lock = threading.RLock()

    def __call__(cls, *args, **kwargs) -> type:
        if not cls.__singleton:
            with cls.__lock:
                if not cls.__singleton:
                    cls.__singleton = super().__call__(*args, **kwargs)
        return cls.__singleton


class Singleton(metaclass=_Singleton):
    pass


class Display(Singleton):
    @classmethod
    def instance(cls, verbosity: int = None):
        instance = cls()
        # Display is a singleton; adjust the verbosity if specified
        if verbosity is not None:
            instance.verbosity = verbosity
        return instance

    def banner(
        self,
        banner: str = "",
        content: typing.Any = None,
        *,
        pretty: bool = False,
        verbosity: int = 0,
        **kwargs,
    ) -> None:
        banner = banner.strip()
        if banner:
            banner = f"[{banner}]"
        formatted_banner = self._format_banner(banner)
        if banner:
            formatted_banner = f"\n{formatted_banner}"
        self.output(
            formatted_banner,
            verbosity=verbosity,
            file=kwargs.get("file", None),
            flush=kwargs.get("flush", False),
        )
        if content is not None:
            self.output(content, pretty=pretty, verbosity=verbosity, **kwargs)
            self.banner(verbosity=verbosity, **kwargs)

    def output(
        self,
        content: typing.Any,
        *,
        pretty: bool = False,
        verbosity: int = 0,
        **kwargs,
    ) -> None:
        if verbosity <= self.verbosity:
            if pretty:
                content = pprint.pformat(content)
            print(content, **kwargs)

    def __init__(self, verbosity: int = 0) -> None:
        super().__init__()
        self.verbosity = verbosity

    def _format_banner(self, banner: str) -> str:
        if len(banner) > 0:
            banner = self._prefix_time(banner)
        banner = self._rule_embed(banner)
        return banner

    def _prefix_time(self, content: str) -> str:
        return f"{datetime.datetime.now().isoformat(' ')} {content}"

    def _rule(self, character: str = "*", /, text_length: int = 0) -> str:
        try:
            rule_length = int(os.get_terminal_size()[0])
        except OSError:
            rule_length = 80

        rule_length = max(0, rule_length - text_length)
        return character * rule_length

    def _rule_embed(self, content: str) -> str:
        prefix = "** "
        suffix = " "

        if len(content) == 0:
            prefix = ""
            suffix = ""

        length = len(prefix) + len(content) + len(suffix)
        rule = self._rule(text_length=length)
        content = f"{prefix}{content}{suffix}{rule}"
        return content
