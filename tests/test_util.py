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
import glob
import os
import tempfile
from unittest.mock import patch

import pytest

from ansible_rulebook.util import untar

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.asyncio
async def test_untar():
    os.chdir(HERE)
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = await untar("./data/demo.tar.gz", tmpdirname)
        assert rc == 0
        files = set(glob.glob(f"{tmpdirname}/*"))
        assert files == set(
            [
                f"{tmpdirname}/Dockerfile",
                f"{tmpdirname}/Makefile",
                f"{tmpdirname}/docker_inventory.yml",
                f"{tmpdirname}/inventory.yml",
                f"{tmpdirname}/playbooks",
                f"{tmpdirname}/podman_inventory.yml",
                f"{tmpdirname}/requirements.yml",
                f"{tmpdirname}/requirements.txt",
                f"{tmpdirname}/rulebooks",
                f"{tmpdirname}/ssh_inventory.yml",
                f"{tmpdirname}/vars.yml",
            ]
        )


@pytest.mark.asyncio
async def test_untar_bad():
    os.chdir(HERE)
    with tempfile.TemporaryDirectory() as tmpdirname:
        rc = await untar("./data/bad.tar.gz", tmpdirname)
        assert rc != 0


@pytest.mark.asyncio
@patch("ansible_rulebook.util.shutil.which")
async def test_untar_tar_cmd_missing(mock):
    mock.return_value = None
    os.chdir(HERE)
    with pytest.raises(FileNotFoundError):
        with tempfile.TemporaryDirectory() as tmpdirname:
            await untar("./data/demo.tar.gz", tmpdirname)
