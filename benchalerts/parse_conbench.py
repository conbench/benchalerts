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

import textwrap
from typing import List, Tuple

from .clients import CheckStatus
from .talk_to_conbench import RunComparison


def _clean(text: str) -> str:
    """Clean text so it displays nicely as GitHub Markdown."""
    return textwrap.fill(textwrap.dedent(text), 10000).replace("  ", "\n\n").strip()


def benchmarks_with_errors(
    comparisons: List[RunComparison],
) -> List[Tuple[str, str, str, str]]:
    """Find the run IDs, webapp links, display names, and case URLs of benchmark
    cases that had errors."""
    out = []

    for comparison in comparisons:
        if comparison.compare_results:
            out += [
                (
                    comparison.contender_id,
                    comparison.compare_link,
                    case["benchmark"],
                    comparison.case_link(case["contender_id"]),
                )
                for case in comparison.compare_results
                if case["contender_error"]
            ]
        else:
            out += [
                (
                    comparison.contender_id,
                    comparison.contender_link,
                    case["tags"].get("name", str(case["tags"])),
                    comparison.case_link(case["id"]),
                )
                for case in comparison.benchmark_results or []
                if case["error"]
            ]

    return out


def benchmarks_with_z_regressions(
    comparisons: List[RunComparison],
) -> List[Tuple[str, str, str, str]]:
    """Find the run IDs, webapp links, display names, and case URLs of benchmark
    cases whose z-scores were extreme enough to constitute a regression.
    """
    out = []

    for comparison in comparisons:
        compare_results = comparison.compare_results or []
        out += [
            (
                comparison.contender_id,
                comparison.compare_link,
                case["benchmark"],
                comparison.case_link(case["contender_id"]),
            )
            for case in compare_results
            if case["contender_z_regression"]
        ]

    return out


def regression_summary(
    comparisons: List[RunComparison], warn_if_baseline_isnt_parent: bool
) -> str:
    """Generate a Markdown summary of what happened regarding errors and regressions."""
    sha = comparisons[0].contender_info["commit"]["sha"][:8]
    errors = benchmarks_with_errors(comparisons)
    regressions = benchmarks_with_z_regressions(comparisons)
    summary = ""

    if errors:
        summary += _clean(
            """
            ## Benchmarks with errors

            These are errors that were caught while running the benchmarks. You can
            click the link next to each case to go to the Conbench entry for that
            benchmark, which might have more information about what the error was.
            """
        )
        previous_run_id = ""
        for run_id, run_url, name, error_url in errors:
            if run_id != previous_run_id:
                summary += f"\n\n- Run ID [{run_id}]({run_url})"
                previous_run_id = run_id
            summary += f"\n  - `{name}` ([link]({error_url}))"
        summary += "\n\n"

    summary += "## Benchmarks with performance regressions\n\n"

    if not any(comparison.baseline_info for comparison in comparisons):
        summary += _clean(
            f"""
            Conbench could not find a baseline run for contender commit `{sha}`. A
            baseline run needs to be on the default branch in the same repository, with
            the same hardware and context, and have at least one of the same benchmark
            cases.
            """
        )
        return summary

    summary += _clean(
        f"""
        Contender commit `{sha}` had {len(regressions)} performance regressions compared
        to its baseline commit.
        """
    )

    if regressions:
        summary += "\n\n### Benchmarks with regressions:"
        previous_compare_url = ""
        for run_id, compare_url, benchmark, case_url in regressions:
            if compare_url != previous_compare_url:
                summary += f"\n\n- Run ID [{run_id}]({compare_url})"
                previous_compare_url = compare_url
            summary += f"\n  - `{benchmark}` ([link]({case_url}))"

    if (
        any(not comparison.baseline_is_parent for comparison in comparisons)
        and warn_if_baseline_isnt_parent
    ):
        summary += "\n\n" + _clean(
            """
            ### Note

            The baseline commit was not the immediate parent of the contender commit.
            See the link below for details.
            """
        )

    return summary


def regression_details(comparisons: List[RunComparison]) -> str:
    """Generate Markdown details of what happened regarding regressions."""
    if not any(comparison.baseline_info for comparison in comparisons):
        return None

    z_score_threshold = comparisons[0].compare_results[0]["threshold_z"]
    details = _clean(
        f"""\
        Conbench has details about {len(comparisons)} total run(s) on this commit.

        This report was generated using a z-score threshold of {z_score_threshold}. A
        regression is defined as a benchmark exhibiting a z-score higher than the
        threshold in the "bad" direction (e.g. down for iterations per second; up for
        total time taken).
        """
    )
    return details


def regression_check_status(
    comparisons: List[RunComparison],
) -> CheckStatus:
    """Return a different status based on regressions."""
    regressions = benchmarks_with_z_regressions(comparisons)

    if any(comparison.has_errors for comparison in comparisons):
        # has errors
        return CheckStatus.ACTION_REQUIRED
    if not any(comparison.baseline_info for comparison in comparisons):
        # no baseline runs found
        return CheckStatus.SKIPPED
    elif regressions:
        # at least one regression
        return CheckStatus.FAILURE
    else:
        # no regressions
        return CheckStatus.SUCCESS
