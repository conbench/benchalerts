from copy import deepcopy

import pytest
from mocks import MockResponse, response_dir

from benchalerts.parse_conbench import benchmarks_with_z_regressions


@pytest.fixture
def all_comparisons():
    compare_file = response_dir / "GET_conbench_compare_runs_100_101.json"
    comparisons = MockResponse.from_file(compare_file).json()
    return {
        "run_id_1": deepcopy(comparisons),
        "run_id_2": deepcopy(comparisons) + deepcopy(comparisons),
    }


@pytest.mark.parametrize("include_regressions", [False, True])
def test_benchmarks_with_z_regressions(all_comparisons, include_regressions):
    if include_regressions:
        all_comparisons["run_id_1"][0]["contender_z_regression"] = True
        expected = [("run_id_1", "snappy, nyctaxi_sample, parquet, arrow")]
    else:
        expected = []

    actual = benchmarks_with_z_regressions(all_comparisons)
    assert expected == actual
