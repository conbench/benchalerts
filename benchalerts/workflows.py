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

from .clients import ConbenchClient, GitHubRepoClient
from .log import log
from .parse_conbench import (
    _clean,
    benchmarks_with_z_regressions,
    regression_check_status,
    regression_details,
    regression_summary,
)


def update_github_status_based_on_regressions(
    contender_sha: str,
    z_score_threshold: Optional[float] = None,
    repo: Optional[str] = None,
    github: Optional[GitHubRepoClient] = None,
    conbench: Optional[ConbenchClient] = None,
) -> dict:
    """Grab the benchmark result comparisons for a given contender commit, and post to
    GitHub whether there were any regressions, in the form of a commit status.

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
        A GitHubRepoClient instance. Either provide this or ``repo``.
    conbench
        A ConbenchClient instance. If not given, one will be created using the standard
        environment variables.

    Environment variables
    ---------------------
    BUILD_URL
        The URL of the build running this code. If provided, the GitHub status will link
        to the build when there's an error in this workflow.
    GITHUB_APP_ID
        The ID of a GitHub App that has been set up according to this package's
        instructions and installed to your repo. Recommended over GITHUB_API_TOKEN. Only
        required if a GitHubRepoClient is not provided.
    GITHUB_APP_PRIVATE_KEY
        The private key file contents of a GitHub App that has been set up according to
        this package's instructions and installed to your repo. Recommended over
        GITHUB_API_TOKEN. Only required if GitHubRepoClient is not provided.
    GITHUB_API_TOKEN
        A GitHub Personal Access Token with the ``repo:status`` permission. Only
        required if not going with GitHub App authentication and if a GitHubRepoClient
        is not provided.
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
        GitHub's details about the new status.
    """
    build_url = os.getenv("BUILD_URL")
    github = github or GitHubRepoClient(repo=repo)

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
        all_comparisons, _ = conbench.get_comparison_to_baseline(
            contender_sha=contender_sha, z_score_threshold=z_score_threshold
        )
        regressions = benchmarks_with_z_regressions(all_comparisons)
        log.info(f"Found the following regressions: {regressions}")

        if not all_comparisons:
            desc = "Could not find any baseline runs to compare to"
            state = github.StatusState.SUCCESS
        elif regressions:
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


def update_github_check_based_on_regressions(
    contender_sha: str,
    z_score_threshold: Optional[float] = None,
    warn_if_baseline_isnt_parent: bool = True,
    repo: Optional[str] = None,
    github: Optional[GitHubRepoClient] = None,
    conbench: Optional[ConbenchClient] = None,
) -> dict:
    """Grab the benchmark result comparisons for a given contender commit, and post to
    GitHub whether there were any regressions, in the form of a commit check.

    You must use GitHub App authentication to use this workflow.

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
    warn_if_baseline_isnt_parent
        If True, will add a warning to all reports generated where the baseline commit
        isn't the contender commit's direct parent. This is good to leave True for
        workflows run on the default branch, but might be noisy for workflows run on
        pull request commits.
    repo
        The repo name to post the status to, in the form 'owner/repo'. Either provide
        this or ``github``.
    github
        A GitHubRepoClient instance. Either provide this or ``repo``.
    conbench
        A ConbenchClient instance. If not given, one will be created using the standard
        environment variables.

    Environment variables
    ---------------------
    BUILD_URL
        The URL of the build running this code. If provided, the GitHub Check will link
        to the build when there's an error in this workflow.
    GITHUB_APP_ID
        The ID of a GitHub App that has been set up according to this package's
        instructions and installed to your repo. Only required if a GitHubRepoClient is
        not provided.
    GITHUB_APP_PRIVATE_KEY
        The private key file contents of a GitHub App that has been set up according to
        this package's instructions and installed to your repo. Only required if
        GitHubRepoClient is not provided.
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
        GitHub's details about the new check.
    """
    build_url = os.getenv("BUILD_URL")
    github = github or GitHubRepoClient(repo=repo)

    def update_check(status, title, summary, details, details_url):
        """Shortcut for updating the "Conbench regression analysis" check on the given
        SHA, with debug logging.
        """
        res = github.update_check(
            name="Conbench regression analysis",
            commit_sha=contender_sha,
            status=status,
            title=title,
            summary=summary,
            details=details,
            details_url=details_url,
        )
        log.debug(res)
        return res

    # mark the task as pending
    update_check(
        status=github.CheckStatus.IN_PROGRESS,
        title="Finding possible regressions",
        summary=f"Analyzing `{contender_sha[:8]}` for regressions...",
        details=None,
        details_url=build_url,
    )

    # If anything above this line fails, we can't tell github that it failed.
    # If anything in here fails, we can!
    try:
        conbench = conbench or ConbenchClient()
        all_comparisons, baseline_is_parent = conbench.get_comparison_to_baseline(
            contender_sha=contender_sha, z_score_threshold=z_score_threshold
        )
        regressions = benchmarks_with_z_regressions(all_comparisons)

        status = regression_check_status(all_comparisons)
        summary = regression_summary(
            all_comparisons,
            baseline_is_parent,
            contender_sha,
            warn_if_baseline_isnt_parent,
        )
        details = regression_details(all_comparisons)
        # point to the homepage table filtered to runs of this commit
        url = f"{os.environ['CONBENCH_URL']}/?search={contender_sha}"

        return update_check(
            status=status,
            title=f"Found {len(regressions)} regression(s)",
            summary=summary,
            details=details,
            details_url=url,
        )

    except Exception as e:
        summary = _clean(
            """
            The CI build running the regression analysis failed. This does not
            necessarily mean this commit has benchmark regressions, but there is an
            error that must be resolved before we can find out.
            """
        )
        details = f"Error: `{repr(e)}`\n\nSee build link below."
        update_check(
            status=github.CheckStatus.NEUTRAL,
            title="Error when finding regressions",
            summary=summary,
            details=details,
            details_url=build_url,
        )
        log.error(f"Updated status with error: {e}")
        raise
