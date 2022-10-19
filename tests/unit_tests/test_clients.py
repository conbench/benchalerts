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
import requests
from _pytest.logging import LogCaptureFixture

from benchalerts.clients import ConbenchClient, GitHubRepoClient

from .mocks import MockAdapter


@pytest.mark.parametrize("github_auth", ["pat", "app"], indirect=True)
class TestGitHubRepoClient:
    @property
    def gh(self):
        return GitHubRepoClient("some/repo", adapter=MockAdapter())

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

    @pytest.mark.parametrize("in_progress", [True, False])
    def test_update_check(self, github_auth, in_progress):
        res = self.gh.update_check(
            name="tests",
            commit_sha="abc",
            status=(
                self.gh.CheckStatus.IN_PROGRESS
                if in_progress
                else self.gh.CheckStatus.SUCCESS
            ),
            title="This was good",
            summary="Testing something",
            details="Some details",
            details_url="https://conbench.biz/",
        )
        assert res["output"]["summary"] == "Testing something"

    def test_update_check_bad_status(self, github_auth):
        with pytest.raises(TypeError, match="CheckStatus"):
            self.gh.update_check(name="tests", commit_sha="abc", status="okay")


@pytest.mark.parametrize("github_auth", ["none"], indirect=True)
class TestMissingGithubEnvVars:
    def test_no_vars_at_all(self, github_auth):
        with pytest.raises(ValueError, match="GITHUB_API_TOKEN"):
            TestGitHubRepoClient().gh

    def test_no_app_id(self, github_auth, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "private key")
        with pytest.raises(ValueError, match="GITHUB_APP_ID"):
            TestGitHubRepoClient().gh

    def test_no_app_pk(self, github_auth, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_APP_ID", "123456")
        with pytest.raises(ValueError, match="GITHUB_APP_PRIVATE_KEY"):
            TestGitHubRepoClient().gh


class TestConbenchClient:
    @property
    def cb(self):
        return ConbenchClient(adapter=MockAdapter())

    def test_conbench_fails_missing_env(self, missing_conbench_env):
        with pytest.raises(ValueError, match="CONBENCH_URL"):
            self.cb

    @pytest.mark.parametrize("z_score_threshold", [None, 500])
    def test_get_comparison_to_baseline(self, conbench_env, z_score_threshold):
        comparisons = self.cb.get_comparison_to_baseline("abc", z_score_threshold)
        assert isinstance(comparisons, list)
        assert len(comparisons) == 1
        assert comparisons[0].compare_link
        assert len(comparisons[0].compare_info) == 2

    def test_comparison_fails_when_no_runs(self, conbench_env):
        with pytest.raises(ValueError, match="runs"):
            self.cb.get_comparison_to_baseline("no_runs")

    def test_comparison_warns_when_no_baseline(
        self, conbench_env, caplog: LogCaptureFixture
    ):
        comparisons = self.cb.get_comparison_to_baseline("no_baseline")
        assert isinstance(comparisons, list)
        assert len(comparisons) == 1
        assert comparisons[0].contender_link
        assert not comparisons[0].compare_link
        assert not comparisons[0].baseline_info
        assert "could not find a baseline run" in caplog.text

    @pytest.mark.parametrize("path", ["/error_with_content", "/error_without_content"])
    def test_client_error_handling(self, conbench_env, path, caplog: LogCaptureFixture):
        with pytest.raises(requests.HTTPError, match="404"):
            self.cb.get(path)

        if path == "/error_with_content":
            assert 'Response content: {"code":' in caplog.text
        else:
            assert "Response content: None" in caplog.text
