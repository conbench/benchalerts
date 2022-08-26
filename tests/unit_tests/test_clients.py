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

MOCKED_REPO = "some/repo"
MOCKED_CB_URL = "https://conbench.biz"


@pytest.fixture
def github_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_API_TOKEN", "token")


@pytest.fixture
def missing_github_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_API_TOKEN", raising=False)


@pytest.fixture
def conbench_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONBENCH_EMAIL", "email")
    monkeypatch.setenv("CONBENCH_PASSWORD", "password")


@pytest.fixture
def missing_conbench_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONBENCH_EMAIL", raising=False)
    monkeypatch.delenv("CONBENCH_PASSWORD", raising=False)


class TestGithubRepoClient:
    def test_github_fails_missing_env(self, missing_github_env):
        with pytest.raises(ValueError, match="GITHUB_API_TOKEN"):
            GithubRepoClient(MOCKED_REPO)

    def test_create_pull_request_comment_with_number(self, github_env):
        gh = GithubRepoClient(MOCKED_REPO)
        output = gh.create_pull_request_comment(comment="test", pull_number=1347)
        assert output

    def test_create_pull_request_comment_with_sha(self, github_env):
        gh = GithubRepoClient(MOCKED_REPO)
        output = gh.create_pull_request_comment(comment="test", commit_sha="abc")
        assert output

    def test_create_pull_request_comment_bad_input(self, github_env):
        gh = GithubRepoClient(MOCKED_REPO)
        with pytest.raises(ValueError, match="specify"):
            gh.create_pull_request_comment(comment="test")

    def test_comment_with_sha_fails_with_no_matching_prs(self, github_env):
        gh = GithubRepoClient(MOCKED_REPO)
        with pytest.raises(ValueError, match="pull request"):
            gh.create_pull_request_comment(comment="test", commit_sha="no_prs")


class TestConbenchClient:
    def test_conbench_fails_missing_env(self, missing_conbench_env):
        with pytest.raises(ValueError, match="CONBENCH_EMAIL"):
            ConbenchClient(MOCKED_CB_URL)

    def test_get_comparison_to_baseline(self, conbench_env):
        cb = ConbenchClient(MOCKED_CB_URL)
        output = cb.get_comparison_to_baseline("abc")
        assert output

    def test_comparison_fails_when_no_commits(self, conbench_env):
        cb = ConbenchClient(MOCKED_CB_URL)
        with pytest.raises(ValueError, match="commits"):
            cb.get_comparison_to_baseline("no_commits")

    def test_comparison_fails_when_no_baseline(self, conbench_env):
        cb = ConbenchClient(MOCKED_CB_URL)
        with pytest.raises(ValueError, match="baseline"):
            cb.get_comparison_to_baseline("no_baseline")

    def test_comparison_fails_when_no_runs(self, conbench_env):
        cb = ConbenchClient(MOCKED_CB_URL)
        with pytest.raises(ValueError, match="runs"):
            cb.get_comparison_to_baseline("no_runs")
