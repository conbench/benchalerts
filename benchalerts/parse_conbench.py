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


def _clean(text: str) -> str:
    """Clean text so it displays nicely as GitHub Markdown."""
    return textwrap.fill(textwrap.dedent(text), 10000).replace("  ", "\n\n").strip()


def benchmarks_with_z_regressions(all_comparisons: dict) -> List[Tuple[str, str]]:
    """Find the compare_urls and names of benchmarks whose z-scores were extreme enough
    to constitute a regression.

    Parameters
    ----------
    all_comparisons
        The dict output of ConbenchClient.get_comparison_to_baseline().

    Returns
    -------
    List[Tuple[str, str]]
        List of tuples of (compare_url, benchmark_name) for all benchmarks with
        regressions.
    """
    return [
        (compare_url, benchmark["benchmark"])
        for compare_url, benchmarks in all_comparisons.items()
        for benchmark in benchmarks
        if benchmark["contender_z_regression"]
    ]


def regression_summary(
    all_comparisons: dict, baseline_is_parent: bool, contender_sha: str
) -> str:
    """Generate a Markdown summary of what happened regarding regressions."""
    regressions = benchmarks_with_z_regressions(all_comparisons)
    summary = _clean(
        f"""
        Contender commit `{contender_sha[:8]}` had {len(regressions)} regressions
        compared to its baseline commit.
        """
    )

    if regressions:
        summary += "\n\n### Benchmarks with regressions:"
        previous_compare_url = ""
        for compare_url, benchmark in regressions:
            if compare_url != previous_compare_url:
                run_id = compare_url[-32:]
                summary += f"\n\n- Run ID [{run_id}]({compare_url})"
                previous_compare_url = compare_url
            summary += f"\n  - `{benchmark}`"

    if not baseline_is_parent:
        summary += "\n\n" + _clean(
            """
            ### Note

            The baseline commit was not the immediate parent of the contender commit. If
            this is a pull request, that's probably okay, because the baseline is the
            commit from which your branch branched.
            """
        )

    return summary


def regression_details(all_comparisons: dict) -> str:
    """Generate Markdown details of what happened regarding regressions."""
    z_score_threshold = next(iter(all_comparisons.values()))[0]["threshold_z"]
    details = _clean(
        f"""\
        Conbench has details about {len(all_comparisons)} total run(s) on this commit.

        This report was generated using a z-score threshold of {z_score_threshold}. A
        regression is defined as a benchmark exhibiting a z-score higher than the
        threshold in the "bad" direction (e.g. down for iterations per second; up for
        total time taken).
        """
    )
    return textwrap.dedent(details)
