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
import os
from typing import Optional

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

    def get(self, path: str) -> dict:
        url = self.base_url + path
        log.debug(f"GET {url}")
        res = self.session.get(url=url, timeout=self.timeout_s)
        res.raise_for_status()
        return res.json()

    def post(self, path: str, json: dict) -> Optional[dict]:
        url = self.base_url + path
        log.debug(f"POST {url} {json}")
        res = self.session.post(url=url, json=json, timeout=self.timeout_s)
        res.raise_for_status()
        if res.content:
            return res.json()


class GithubRepoClient(_BaseClient):
    """A client to interact with a Github repo.

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
        A Github API token with ``repo`` access.
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
        The URL of the Conbench server.
    CONBENCH_EMAIL
        The email to use for Conbench login.
    CONBENCH_PASSWORD
        The password to use for Conbench login.
    """

    def __init__(self, adapter: Optional[HTTPAdapter] = None):
        login_creds = {
            "url": os.getenv("CONBENCH_URL"),
            "email": os.getenv("CONBENCH_EMAIL"),
            "password": os.getenv("CONBENCH_PASSWORD"),
        }
        for cred in login_creds:
            if not login_creds[cred]:
                fatal_and_log(f"Environment variable CONBENCH_{cred.upper()} not found")

        super().__init__(adapter=adapter)
        self.base_url = login_creds.pop("url") + "/api"
        self.post("/login/", json=login_creds)

    def get_comparison_to_baseline(self, contender_sha: str) -> list:
        """Get benchmark comparisons between the given contender commit and its
        baseline commit.

        The baseline commit is defined by conbench, and it's typically the most recent
        ancestor of the contender commit that's on the default branch.

        Note the contender_sha needs to match EXACTLY what conbench has stored;
        typically 40 characters. It can't be a shortened version of the SHA.
        """
        contender_info = self.get(f"/commits/?sha={contender_sha}")
        if len(contender_info) != 1:
            fatal_and_log(
                f"Found {len(contender_info)} commits in conbench that match the "
                f"contender SHA '{contender_sha}'."
            )

        baseline_sha = contender_info[0].get("parent_sha")
        if not baseline_sha:
            fatal_and_log(
                f"Found the contender commit ({contender_sha}) but it doesn't have a "
                "baseline commit in conbench."
            )

        commit_compare = self.get(f"/compare/commits/{baseline_sha}...{contender_sha}")
        all_runs = commit_compare["runs"]
        if len(all_runs) == 0:
            fatal_and_log(
                f"Contender commit '{contender_sha}' doesn't have any runs in conbench."
            )
        elif len(all_runs) > 1:
            fatal_and_log(
                f"Contender commit '{contender_sha}' has {len(all_runs)} runs in "
                "conbench. At this time, more than 1 run is not supported.",
                etype=NotImplementedError,
            )

        run = all_runs[0]
        comparison = self.get(
            f"/compare/runs/{run['baseline']['run_id']}...{run['contender']['run_id']}"
        )

        return comparison
