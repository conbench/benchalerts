# Copyright (c) 2022, Voltron Data.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import pytest

from benchalerts.clients import ConbenchClient, GithubRepoClient


def test_create_pull_request_comment():
    if os.getenv("CI"):
        pytest.skip("Don't post a PR comment from CI")

    if not os.getenv("GITHUB_API_TOKEN"):
        pytest.skip("GITHUB_API_TOKEN env var missing")

    gh = GithubRepoClient("conbench/benchalerts")
    res = gh.create_pull_request_comment(
        "posted from an integration test", commit_sha="adc9b73"
    )
    assert res


@pytest.mark.parametrize(
    "conbench_url",
    [
        "https://velox-conbench.voltrondata.run",
        "https://velox-conbench.voltrondata.run/",
    ],
)
def test_get_comparison_to_baseline(monkeypatch: pytest.MonkeyPatch, conbench_url: str):
    monkeypatch.setenv("CONBENCH_URL", conbench_url)
    cb = ConbenchClient()
    res = cb.get_comparison_to_baseline("60538ad2f41fac3925490a366c06ab2e3cef193c")
    assert len(res) == 80, f"actual len(res) is {len(res)}"
