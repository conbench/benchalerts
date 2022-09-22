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

import abc
import enum
import os
import textwrap
from json import dumps
from typing import Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .log import fatal_and_log, log


class _BaseClient(abc.ABC):
    """A client to interact with an API.

    Parameters
    ----------
    adapter
        A requests adapter to mount to the requests session. If not given, one will be
        created with a backoff retry strategy.
    """

    base_url: str
    timeout_s = 10

    def __init__(self, adapter: Optional[HTTPAdapter]):
        if not adapter:
            retry_strategy = Retry(
                total=5,
                status_forcelist=frozenset((429, 502, 503, 504)),
                backoff_factor=4,  # will retry in 2, 4, 8, 16, 32 seconds
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)

        self.session = requests.Session()
        self.session.mount("https://", adapter)

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        url = self.base_url + path
        log.debug(f"GET {url} {params=}")
        res = self.session.get(url=url, params=params, timeout=self.timeout_s)
        res.raise_for_status()
        return res.json()

    def post(self, path: str, json: dict) -> Optional[dict]:
        url = self.base_url + path
        log.debug(f"POST {url} {dumps(json)}")
        res = self.session.post(url=url, json=json, timeout=self.timeout_s)
        res.raise_for_status()
        if res.content:
            return res.json()


class GitHubRepoClient(_BaseClient):
    """A client to interact with a GitHub repo.

    Parameters
    ----------
    repo
        The repo name, in the form 'owner/repo'.
    adapter
        A requests adapter to mount to the requests session. If not given, one will be
        created with a backoff retry strategy.

    Environment variables
    ---------------------
    GITHUB_API_TOKEN
        A GitHub API token with ``repo`` access.
    """

    def __init__(self, repo: str, adapter: Optional[HTTPAdapter] = None):
        token = os.getenv("GITHUB_API_TOKEN")
        if not token:
            fatal_and_log("Environment variable GITHUB_API_TOKEN not found")

        super().__init__(adapter=adapter)
        self.session.headers = {"Authorization": f"Bearer {token}"}
        self.base_url = f"https://api.github.com/repos/{repo}"

    def create_pull_request_comment(
        self,
        comment: str,
        *,
        pull_number: Optional[int] = None,
        commit_sha: Optional[str] = None,
    ):
        """Create a comment on a pull request, specified either by pull request number
        or commit SHA.

        Parameters
        ----------
        comment
            The comment text.
        pull_number
            The number of the pull request. Specify either this or ``commit_sha``.
        commit_sha
            The SHA of a commit associated with the pull request. Specify either this
            or ``pull_number``.
        """
        if not pull_number and not commit_sha:
            fatal_and_log("pull_number and commit_sha are both missing")

        if commit_sha:
            pull_numbers = [
                pull["number"] for pull in self.get(f"/commits/{commit_sha}/pulls")
            ]
            if len(pull_numbers) != 1:
                fatal_and_log(
                    "Need exactly 1 pull request associated with commit "
                    f"'{commit_sha}'. Found {pull_numbers}."
                )
            pull_number = pull_numbers[0]

        log.info(
            f"Posting the following message to pull request #{pull_number}:\n\n"
            + comment
        )
        return self.post(f"/issues/{pull_number}/comments", json={"body": comment})

    class StatusState(str, enum.Enum):
        ERROR = "error"
        FAILURE = "failure"
        PENDING = "pending"
        SUCCESS = "success"

    def update_commit_status(
        self,
        commit_sha: str,
        title: str,
        description: str,
        state: StatusState,
        details_url: Optional[str] = None,
    ) -> dict:
        """Update the GitHub status of a commit.

        A commit may have many statuses, each with their own title. Updating a previous
        status with the same title for a given commit will result in overwriting that
        status on that commit.

        Parameters
        ----------
        commit_sha
            The 40-character SHA of the commit to update.
        title
            The title of the status. Subsequent updates with the same title will update
            the same status.
        description
            The short description of the status.
        state
            The overall status of the commit. Must be one of the
            GitHubRepoClient.StatusState enum values.
        details_url
            A URL to be linked to when clicking on status Details. Default None.

        Returns
        -------
        dict
            GitHub's details about the new status.
        """
        if not isinstance(state, self.StatusState):
            fatal_and_log(
                "state must be a GitHubRepoClient.StatusState", etype=TypeError
            )

        json = {
            "state": state.value,
            "description": textwrap.shorten(description, 140),
            "context": title,
        }
        if details_url:
            json["target_url"] = details_url

        return self.post(f"/statuses/{commit_sha}", json=json)


class ConbenchClient(_BaseClient):
    """A client to interact with a Conbench server.

    Parameters
    ----------
    adapter
        A requests adapter to mount to the requests session. If not given, one will be
        created with a backoff retry strategy.

    Environment variables
    ---------------------
    CONBENCH_URL
        The URL of the Conbench server. Required.
    CONBENCH_EMAIL
        The email to use for Conbench login. Only required if the server is private.
    CONBENCH_PASSWORD
        The password to use for Conbench login. Only required if the server is private.
    """

    def __init__(self, adapter: Optional[HTTPAdapter] = None):
        url = os.getenv("CONBENCH_URL")
        if not url:
            fatal_and_log("Environment variable CONBENCH_URL not found")

        super().__init__(adapter=adapter)
        self.base_url = url + "/api"

        login_creds = {
            "email": os.getenv("CONBENCH_EMAIL"),
            "password": os.getenv("CONBENCH_PASSWORD"),
        }
        if login_creds["email"] and login_creds["password"]:
            self.post("/login/", json=login_creds)

    def get_comparison_to_baseline(
        self, contender_sha: str, z_score_threshold: Optional[float] = None
    ) -> Tuple[dict, bool]:
        """Get benchmark comparisons between the given contender commit and its
        baseline commit.

        The baseline commit is defined by conbench, and it's typically the most recent
        ancestor of the contender commit that's on the default branch. This method also
        returns whether that's the immediate parent of the contender or not.

        Parameters
        ----------
        contender_sha
            The commit SHA of the contender commit to compare. Needs to match EXACTLY
            what conbench has stored; typically 40 characters. It can't be a shortened
            version of the SHA.
        z_score_threshold
            The (positive) z-score threshold to send to the conbench compare endpoint.
            Benchmarks with a z-score more extreme than this threshold will be marked as
            regressions or improvements in the result. Default is to use whatever
            conbench uses for default.

        Returns
        -------
        dict
            A dict where keys are contender run_ids and values are lists of dicts
            containing benchmark comparison information.
        bool
            True if all the baseline runs were found on the immediate parent of the
            contender commit. If False, the contender might be a non-first PR commit, or
            there could have been commits on the default branch without any logged
            Conbench runs.
        """
        comparisons = {}
        baseline_is_parent = True
        contender_runs = self.get("/runs/", params={"sha": contender_sha})
        if not contender_runs:
            fatal_and_log(
                f"Contender commit '{contender_sha}' doesn't have any runs in conbench."
            )

        log.info(f"Getting comparisons from {len(contender_runs)} runs")
        for run in contender_runs:
            contender_info = self.get(f"/runs/{run['id']}/")
            baseline_path = contender_info["links"]["baseline"].split("/api")[-1]
            baseline_info = self.get(baseline_path)

            if baseline_info["commit"]["sha"] != contender_info["commit"]["parent_sha"]:
                baseline_is_parent = False

            path = f"/compare/runs/{baseline_info['id']}...{contender_info['id']}"
            params = {"threshold_z": z_score_threshold} if z_score_threshold else None
            comparison = self.get(path, params=params)
            comparisons[contender_info["id"]] = comparison

        return comparisons, baseline_is_parent
