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

from benchalerts.clients import ConbenchClient, GitHubRepoClient


def test_create_pull_request_comment():
    if os.getenv("CI"):
        pytest.skip("Don't post a PR comment from CI")

    gh = GitHubRepoClient("conbench/benchalerts")
    res = gh.create_pull_request_comment(
        "posted from an integration test", commit_sha="adc9b73"
    )
    assert res


@pytest.mark.parametrize(
    ["conbench_url", "commit", "expected_len", "expected_bip"],
    [
        (
            "https://conbench.ursa.dev/",
            "bc7de406564fa7b2bcb9bf055cbaba31ca0ca124",
            8,
            True,
        ),
        (
            "https://velox-conbench.voltrondata.run",
            "2319922d288c519baa3bffe59c0bedbcb6c827cd",
            1,
            False,
        ),
    ],
)
def test_get_comparison_to_baseline(
    monkeypatch: pytest.MonkeyPatch, conbench_url, commit, expected_len, expected_bip
):
    monkeypatch.setenv("CONBENCH_URL", conbench_url)
    cb = ConbenchClient()
    res = cb.get_comparison_to_baseline(commit)
    comparisons, baseline_is_parent = res
    assert baseline_is_parent is expected_bip
    assert len(comparisons) == expected_len
    for comparison in comparisons.values():
        for benchmark in comparison:
            assert benchmark["contender_run_id"]
