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
import pytest

from ansible_rulebook.exception import InvalidFilterNameException
from ansible_rulebook.util import has_builtin_filter


def test_bad_builtin_filter():
    with pytest.raises(InvalidFilterNameException):
        has_builtin_filter("eda.builtin.")


def test_has_builtin_filter():
    assert has_builtin_filter("eda.builtin.insert_meta_info")


def test_has_builtin_filter_missing():
    assert not has_builtin_filter("eda.builtin.something_missing")


def test_builtin_filter_bad_prefix():
    assert not has_builtin_filter("eda.gobbledygook.")
