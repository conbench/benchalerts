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

import pathlib
from copy import deepcopy

import pytest

from benchalerts.clients import GitHubRepoClient
from benchalerts.parse_conbench import (
    benchmarks_with_z_regressions,
    regression_check_status,
    regression_details,
    regression_summary,
)

from .mocks import MockResponse, response_dir


def mock_comparisons(include_regressions: bool):
    if include_regressions:
        compare_json = "GET_conbench_compare_runs_some_baseline_some_contender.json"
    else:
        compare_json = "GET_conbench_compare_runs_some_baseline_some_contender_threshold_z_500.json"
    compare_file = response_dir / compare_json
    comparisons = MockResponse.from_file(compare_file).json()
    return {
        "https://conbench/some_baseline1...some_contender1": deepcopy(comparisons),
        "https://conbench/some_baseline2...some_contender2": deepcopy(comparisons),
    }


def get_expected_markdown(filename: str) -> str:
    if not filename:
        return None
    file = pathlib.Path(__file__).parent / "expected_md" / (filename + ".md")
    with open(file, "r") as f:
        return f.read()


@pytest.mark.parametrize("include_regressions", [False, True])
def test_benchmarks_with_z_regressions(include_regressions):
    if include_regressions:
        expected = [
            (
                "https://conbench/some_baseline1...some_contender1",
                "snappy, nyctaxi_sample, parquet, arrow",
            ),
            (
                "https://conbench/some_baseline2...some_contender2",
                "snappy, nyctaxi_sample, parquet, arrow",
            ),
        ]
    else:
        expected = []

    actual = benchmarks_with_z_regressions(mock_comparisons(include_regressions))
    assert actual == expected


@pytest.mark.parametrize(
    ["comparisons", "baseline_is_parent", "expected_md"],
    [
        (mock_comparisons(False), False, "summary_noregressions_baselineisnotparent"),
        (mock_comparisons(False), True, "summary_noregressions_baselineisparent"),
        (mock_comparisons(True), False, "summary_regressions_baselineisnotparent"),
        (mock_comparisons(True), True, "summary_regressions_baselineisparent"),
        ({}, False, "summary_nobaseline"),
        ({}, True, "summary_nobaseline"),
    ],
)
def test_regression_summary(comparisons, baseline_is_parent, expected_md):
    contender_sha = "abc" if comparisons else "no_baseline"
    actual = regression_summary(
        comparisons,
        baseline_is_parent,
        contender_sha,
        warn_if_baseline_isnt_parent=True,
    )
    expected = get_expected_markdown(expected_md)
    assert (
        actual.strip() == expected.strip()
    ), f"see tests/unit_tests/expected_md/{expected_md}.md"


@pytest.mark.parametrize(
    ["comparisons", "expected_md"],
    [
        (mock_comparisons(False), "details_noregressions"),
        (mock_comparisons(True), "details_regressions"),
        ({}, None),
    ],
)
def test_regression_details(comparisons, expected_md):
    actual = regression_details(comparisons)
    expected = get_expected_markdown(expected_md)
    if expected:
        assert (
            actual.strip() == expected.strip()
        ), f"see tests/unit_tests/expected_md/{expected_md}.md"
    else:
        assert actual is expected


@pytest.mark.parametrize(
    ["comparisons", "expected_status"],
    [
        (mock_comparisons(False), GitHubRepoClient.CheckStatus.SUCCESS),
        (mock_comparisons(True), GitHubRepoClient.CheckStatus.FAILURE),
        ({}, GitHubRepoClient.CheckStatus.SKIPPED),
    ],
)
def test_regression_check_status(comparisons, expected_status):
    assert regression_check_status(comparisons) == expected_status
