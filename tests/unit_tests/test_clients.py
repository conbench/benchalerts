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

from benchalerts.clients import ConbenchClient, GithubRepoClient

from .mocks import MockAdapter


@pytest.mark.parametrize("github_auth", ["pat", "app"], indirect=True)
class TestGithubRepoClient:
    @property
    def gh(self):
        return GithubRepoClient("some/repo", adapter=MockAdapter())

    def test_create_pull_request_comment_with_number(self, github_auth):
        output = self.gh.create_pull_request_comment(comment="test", pull_number=1347)
        assert output["body"] == "test"

    def test_create_pull_request_comment_with_sha(self, github_auth):
        output = self.gh.create_pull_request_comment(comment="test", commit_sha="abc")
        assert output["body"] == "test"

    def test_create_pull_request_comment_bad_input(self, github_auth):
        with pytest.raises(ValueError, match="missing"):
            self.gh.create_pull_request_comment(comment="test")

    def test_comment_with_sha_fails_with_no_matching_prs(self, github_auth):
        with pytest.raises(ValueError, match="pull request"):
            self.gh.create_pull_request_comment(comment="test", commit_sha="no_prs")

    def test_update_commit_status(self, github_auth):
        res = self.gh.update_commit_status(
            commit_sha="abc",
            title="tests",
            description="Testing something",
            state=self.gh.StatusState.SUCCESS,
            details_url="https://conbench.biz/",
        )
        assert res["description"] == "Testing something"

    def test_update_commit_status_bad_state(self, github_auth):
        with pytest.raises(TypeError, match="StatusState"):
            self.gh.update_commit_status(
                commit_sha="abc",
                title="tests",
                description="Testing something",
                state="sorta working",
                details_url="https://conbench.biz/",
            )


@pytest.mark.parametrize("github_auth", ["none"], indirect=True)
def test_github_fails_missing_env(github_auth):
    with pytest.raises(ValueError, match="GITHUB_APP_ID"):
        TestGithubRepoClient().gh


@pytest.mark.parametrize("github_auth", ["none"], indirect=True)
def test_github_fails_missing_env_2(github_auth, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_APP_ID", "123456")
    with pytest.raises(ValueError, match="GITHUB_APP_PRIVATE_KEY"):
        TestGithubRepoClient().gh


class TestConbenchClient:
    @property
    def cb(self):
        return ConbenchClient(adapter=MockAdapter())

    def test_conbench_fails_missing_env(self, missing_conbench_env):
        with pytest.raises(ValueError, match="CONBENCH_URL"):
            self.cb

    @pytest.mark.parametrize("z_score_threshold", [None, 500])
    def test_get_comparison_to_baseline(self, conbench_env, z_score_threshold):
        output = self.cb.get_comparison_to_baseline("abc", z_score_threshold)
        assert isinstance(output, dict)
        assert len(output) == 1
        assert isinstance(output["101"], list)
        assert len(output["101"]) == 2

    def test_comparison_fails_when_no_commits(self, conbench_env):
        with pytest.raises(ValueError, match="commits"):
            self.cb.get_comparison_to_baseline("no_commits")

    def test_comparison_fails_when_no_baseline(self, conbench_env):
        with pytest.raises(ValueError, match="baseline"):
            self.cb.get_comparison_to_baseline("no_baseline")

    def test_comparison_fails_when_no_runs(self, conbench_env):
        with pytest.raises(ValueError, match="runs"):
            self.cb.get_comparison_to_baseline("no_runs")
