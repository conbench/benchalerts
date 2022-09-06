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
from typing import Optional

from .clients import ConbenchClient, GithubRepoClient
from .log import log
from .parse_conbench import benchmarks_with_z_regressions


def update_github_status_based_on_regressions(
    contender_sha: str,
    z_score_threshold: Optional[float] = None,
    repo: Optional[str] = None,
    github: Optional[GithubRepoClient] = None,
    conbench: Optional[ConbenchClient] = None,
) -> dict:
    """Grab the benchmark result comparisons for a given contender commit, and post to
    Github whether there were any regressions, in the form of a commit status.

    Parameters
    ----------
    contender_sha
        The SHA of the contender commit to compare. Needs to match EXACTLY what
        conbench has stored; typically 40 characters. It can't be a shortened
        version of the SHA.
    z_score_threshold
        The (positive) z-score threshold. Benchmarks with a z-score more extreme than
        this threshold will be marked as regressions. Default is to use whatever
        conbench uses for default.
    repo
        The repo name to post the status to, in the form 'owner/repo'. Either provide
        this or ``github``.
    github
        A GithubRepoClient instance. Either provide this or ``repo``.
    conbench
        A ConbenchClient instance. If not given, one will be created using the standard
        environment variables.

    Environment variables
    ---------------------
    BUILD_URL
        The URL of the build running this code. If provided, the Github status will link
        to the build when there's an error in this workflow.
    GITHUB_API_TOKEN
        A Github API token with ``repo`` access. Only required if a GithubRepoClient is
        not provided.
    CONBENCH_URL
        The URL of the Conbench server. Only required if a ConbenchClient is not
        provided.
    CONBENCH_EMAIL
        The email to use for Conbench login. Only required if a ConbenchClient is not
        provided and the server is private.
    CONBENCH_PASSWORD
        The password to use for Conbench login. Only required if a ConbenchClient is not
        provided and the server is private.

    Returns
    -------
    dict
        Github's details about the new status.
    """
    build_url = os.getenv("BUILD_URL")
    github = github or GithubRepoClient(repo=repo)

    def update_status(description, state, details_url):
        """Shortcut for updating the "conbench" status on the given SHA, with debug
        logging.
        """
        res = github.update_commit_status(
            commit_sha=contender_sha,
            title="conbench",
            description=description,
            state=state,
            details_url=details_url,
        )
        log.debug(res)
        return res

    # mark the task as pending
    update_status(
        description="Finding possible regressions",
        state=github.StatusState.PENDING,
        details_url=build_url,
    )

    # If anything above this line fails, we can't tell github that it failed.
    # If anything in here fails, we can!
    try:
        conbench = conbench or ConbenchClient()
        all_comparisons = conbench.get_comparison_to_baseline(
            contender_sha=contender_sha, z_score_threshold=z_score_threshold
        )
        regressions = benchmarks_with_z_regressions(all_comparisons)
        log.info(f"Found the following regressions: {regressions}")

        if regressions:
            desc = f"There were {len(regressions)} benchmark regressions in this commit"
            state = github.StatusState.FAILURE
        else:
            desc = "There were no benchmark regressions in this commit"
            state = github.StatusState.SUCCESS

        # point to the homepage table filtered to runs of this commit
        url = f"{os.environ['CONBENCH_URL']}/?search={contender_sha}"
        return update_status(description=desc, state=state, details_url=url)

    except Exception as e:
        update_status(
            description=f"Failed finding regressions: {e}",
            state=github.StatusState.ERROR,
            details_url=build_url,
        )
        log.error(f"Updated status with error: {e}")
        raise
