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
import datetime
import enum
import os
import textwrap
from json import dumps
from typing import Optional, Tuple

import jwt
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
        self._maybe_raise(res)
        return res.json()

    def post(self, path: str, json: dict = None) -> Optional[dict]:
        json = json or {}
        url = self.base_url + path
        log.debug(f"POST {url} {dumps(json)}")
        res = self.session.post(url=url, json=json, timeout=self.timeout_s)
        self._maybe_raise(res)
        if res.content:
            return res.json()

    @staticmethod
    def _maybe_raise(res: requests.Response):
        try:
            res.raise_for_status()
        except requests.HTTPError as e:
            try:
                res_content = e.response.content.decode()
            except AttributeError:
                res_content = e.response.content
            log.error(f"Response content: {res_content}")
            raise


class GitHubAppClient(_BaseClient):
    """A client to interact with a GitHub App.

    Parameters
    ----------
    adapter
        A requests adapter to mount to the requests session. If not given, one will be
        created with a backoff retry strategy.

    Environment variables
    ---------------------
    GITHUB_APP_ID
        The numeric GitHub App ID you can get from its settings page.
    GITHUB_APP_PRIVATE_KEY
        The full contents of the private key file downloaded from the App's settings
        page.
    """

    def __init__(self, adapter: Optional[HTTPAdapter] = None):
        app_id = os.getenv("GITHUB_APP_ID")
        if not app_id:
            fatal_and_log("Environment variable GITHUB_APP_ID not found")

        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        if not private_key:
            fatal_and_log("Environment variable GITHUB_APP_PRIVATE_KEY not found")

        super().__init__(adapter=adapter)
        encoded_jwt = self._encode_jwt(app_id=app_id, private_key=private_key)
        self.session.headers = {"Authorization": f"Bearer {encoded_jwt}"}
        self.base_url = "https://api.github.com/app"

    @staticmethod
    def _encode_jwt(app_id: str, private_key: str) -> str:
        """Create, sign, and encode a JSON web token to use for GitHub App endpoints."""
        payload = {
            "iss": app_id,
            "iat": datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
        }
        encoded_jwt = jwt.encode(payload=payload, key=private_key, algorithm="RS256")
        return encoded_jwt

    def get_app_access_token(self) -> str:
        """Authenticate as the GitHub App and generate an app installation access token.

        The token lasts for 1 hour, which should be plenty of time to do anything this
        package needs to do.

        Returns
        -------
        str
            A temporary API token to use for the GitHub API endpoints that the app has
            permission to access.
        """
        # We tell developers to create a new app for each organization, so they can
        # control the private key. So there should be exactly 1 installation here.
        # (Note: 1 installation could have multiple repos in the same organization.)
        installations = self.get("/installations")
        install_id = installations[0]["id"]

        token_info = self.post(f"/installations/{install_id}/access_tokens")
        return token_info["token"]


class GitHubRepoClient(_BaseClient):
    """A client to interact with a GitHub repo.

    You may authenticate with the GitHub API using a GitHub Personal Access Token or a
    GitHub App. The correct environment variables must be set depending on which method
    of authentication you're using. If all are set, the App method will be used.

    Parameters
    ----------
    repo
        The repo name, in the form 'owner/repo'.
    adapter
        A requests adapter to mount to the requests session. If not given, one will be
        created with a backoff retry strategy.

    Environment variables
    ---------------------
    GITHUB_APP_ID
        The numeric GitHub App ID you can get from its settings page. Only used for
        GitHub App authentication.
    GITHUB_APP_PRIVATE_KEY
        The full contents of the private key file downloaded from the App's settings
        page. Only used for GitHub App authentication.
    GITHUB_API_TOKEN
        A GitHub API token with ``repo`` access. Only used for Personal Access Token
        authentication.
    """

    def __init__(self, repo: str, adapter: Optional[HTTPAdapter] = None):
        if os.getenv("GITHUB_APP_ID") or os.getenv("GITHUB_APP_PRIVATE_KEY"):
            log.info("Attempting to authenticate as a GitHub App.")
            app_client = GitHubAppClient(adapter=adapter)
            token = app_client.get_app_access_token()
        else:
            token = os.getenv("GITHUB_API_TOKEN")
            if not token:
                fatal_and_log("Environment variable GITHUB_API_TOKEN not found.")

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

    class CheckStatus(str, enum.Enum):
        # statuses
        QUEUED = "queued"
        IN_PROGRESS = "in_progress"
        # conclusions
        ACTION_REQUIRED = "action_required"
        CANCELLED = "cancelled"
        FAILURE = "failure"
        NEUTRAL = "neutral"
        SUCCESS = "success"
        SKIPPED = "skipped"
        TIMED_OUT = "timed_out"

    def update_check(
        self,
        name: str,
        commit_sha: str,
        status: Optional[CheckStatus] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        details: Optional[str] = None,
        details_url: Optional[str] = None,
    ):
        """Adds a new (or updates an existing) GitHub Check on a commit.

        A GitHub Check is a more fully-featured commit status, but you must be
        authenticated as a GitHub App to update checks. Subsequent uses of this method
        with the same ``name`` will overwrite the previous check.

        Parameters
        ----------
        name
            The name of the check. Subsequent updates with the same name will overwrite
            the previous check.
        commit_sha
            The 40-character SHA of the commit to update.
        status
            The overall check status. Must be one of the GitHubRepoClient.CheckStatus
            enum values. If it's QUEUED or IN_PROGRESS, the "started_at" field will be
            sent in the payload with the current time in UTC. If it's another value,
            the "completed_at" field will be sent instead.
        title
            The short title of the check results. Default None. If supplied, summary
            must be supplied.
        summary
            A longer summary of the check results. Supports Markdown. Default None. If
            supplied, title must be supplied.
        details
            Details about the check results. Supports Markdown. Default None.
        details_url
            A URL to be linked to when clicking on check Details. Default None.

        Returns
        -------
        dict
            GitHub's details about the new status.
        """
        json = {"name": name, "head_sha": commit_sha}

        if status:
            if status in [self.CheckStatus.QUEUED, self.CheckStatus.IN_PROGRESS]:
                json["status"] = status.value
                json["started_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            elif isinstance(status, self.CheckStatus):
                json["conclusion"] = status.value
                json["completed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            elif status is not None:
                fatal_and_log(
                    "status must be a GitHubRepoClient.CheckStatus or None",
                    etype=TypeError,
                )

        if title:
            json["output"] = {"title": title, "summary": summary}
            if details:
                json["output"]["text"] = details

        if details_url:
            json["details_url"] = details_url

        return self.post("/check-runs", json=json)


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
            A dict where keys are compare URLs and values are lists of dicts
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
            baseline_link: Optional[str] = contender_info["links"]["baseline"]
            if not baseline_link:
                log.warning(
                    f"Conbench could not find a baseline run for run_id {run['id']}. "
                    "A baseline run needs to be on the default branch, with the same "
                    "hardware, repository, case, and context as the contender run."
                )
                continue

            baseline_info = self.get(baseline_link.split("/api")[-1])

            if baseline_info["commit"]["sha"] != contender_info["commit"]["parent_sha"]:
                baseline_is_parent = False

            path = f"/compare/runs/{baseline_info['id']}...{contender_info['id']}"
            params = {"threshold_z": z_score_threshold} if z_score_threshold else None
            comparison = self.get(path, params=params)
            comparisons[self.base_url + path] = comparison

        if not comparisons:
            baseline_is_parent = False

        return comparisons, baseline_is_parent
