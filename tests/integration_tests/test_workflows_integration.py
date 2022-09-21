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
import time

import pytest

import benchalerts.workflows as flows
from benchalerts.clients import GitHubRepoClient


@pytest.mark.parametrize("z_score_threshold", [None, 500])
def test_update_github_status_based_on_regressions(
    monkeypatch: pytest.MonkeyPatch, z_score_threshold
):
    """While this test is running, you can watch
    https://github.com/conbench/benchalerts/pull/5 to see the statuses change!
    """
    if not os.getenv("GITHUB_API_TOKEN"):
        pytest.skip("GITHUB_API_TOKEN env var not found")

    # note: something *might* go wrong if we go past 1000 statuses on this test SHA?
    # https://docs.github.com/en/rest/commits/statuses#create-a-commit-status
    test_status_repo = "conbench/benchalerts"
    test_status_commit = "4b9543876e8c1cee54c56980c3b2363aad71a8d4"

    arrow_conbench_url = "https://conbench.ursa.dev/"
    arrow_commit = "13a7b605ede88ca15b053f119909c48d0919c6f8"

    github_run_id = os.getenv("GITHUB_RUN_ID", "2974120883")
    build_url = f"https://github.com/{test_status_repo}/actions/runs/{github_run_id}"
    monkeypatch.setenv("BUILD_URL", build_url)

    # first, test an error
    monkeypatch.delenv("CONBENCH_URL", raising=False)
    with pytest.raises(ValueError, match="CONBENCH_URL not found"):
        flows.update_github_status_based_on_regressions(
            contender_sha=test_status_commit, repo=test_status_repo
        )

    # sleep to see the updated status on the PR
    time.sleep(3)

    # next, a success if z_score_threshold=500, or failure if z_score_threshold=None
    monkeypatch.setenv("CONBENCH_URL", arrow_conbench_url)

    class GitHubDifferentRepoClient(GitHubRepoClient):
        def update_commit_status(self, commit_sha, **kwargs):
            """Even though we're grabbing Arrow benchmarks, we want to post to our own
            repo for testing. This overrides the method to post statuses to a different
            commit.
            """
            return super().update_commit_status(commit_sha=test_status_commit, **kwargs)

    github = GitHubDifferentRepoClient(repo=test_status_repo)

    flows.update_github_status_based_on_regressions(
        contender_sha=arrow_commit, z_score_threshold=z_score_threshold, github=github
    )

    # sleep to see the updated status on the PR
    time.sleep(3)
