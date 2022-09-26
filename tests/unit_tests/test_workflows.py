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

import pytest

import benchalerts.workflows as flows
from benchalerts.clients import ConbenchClient, GitHubRepoClient

from .mocks import MockAdapter


@pytest.mark.parametrize("z_score_threshold", [None, 500])
@pytest.mark.parametrize("github_auth", ["pat", "app"], indirect=True)
@pytest.mark.parametrize(
    "workflow",
    [
        flows.update_github_status_based_on_regressions,
        flows.update_github_check_based_on_regressions,
    ],
)
def test_flows(github_auth, conbench_env, z_score_threshold, workflow):
    gh = GitHubRepoClient("some/repo", adapter=MockAdapter())
    cb = ConbenchClient(adapter=MockAdapter())

    res = workflow(
        contender_sha="abc", z_score_threshold=z_score_threshold, github=gh, conbench=cb
    )
    if workflow == flows.update_github_status_based_on_regressions:
        assert res["description"] == "Testing something"
    elif workflow == flows.update_github_check_based_on_regressions:
        assert res["output"]["summary"] == "Testing something"


@pytest.mark.parametrize("github_auth", ["pat", "app"], indirect=True)
@pytest.mark.parametrize(
    "workflow",
    [
        flows.update_github_status_based_on_regressions,
        flows.update_github_check_based_on_regressions,
    ],
)
def test_flows_failure(github_auth, missing_conbench_env, workflow):
    gh = GitHubRepoClient("some/repo", adapter=MockAdapter())

    with pytest.raises(ValueError, match="not found"):
        workflow(contender_sha="abc", github=gh)


@pytest.mark.parametrize("github_auth", ["pat", "app"], indirect=True)
@pytest.mark.parametrize(
    "workflow",
    [
        flows.update_github_status_based_on_regressions,
        flows.update_github_check_based_on_regressions,
    ],
)
def test_update_github_status_based_on_regressions_no_baseline(
    github_auth, conbench_env, workflow
):
    gh = GitHubRepoClient("some/repo", adapter=MockAdapter())
    cb = ConbenchClient(adapter=MockAdapter())

    res = workflow(contender_sha="no_baseline", github=gh, conbench=cb)
    assert res["description"] == "Could not find any baseline runs to compare to"
