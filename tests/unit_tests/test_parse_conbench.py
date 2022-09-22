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

from copy import deepcopy

import pytest
from mocks import MockResponse, response_dir

from benchalerts.parse_conbench import benchmarks_with_z_regressions


def all_comparisons(include_regressions: bool):
    if include_regressions:
        compare_json = "GET_conbench_compare_runs_some_baseline_some_contender.json"
    else:
        compare_json = "GET_conbench_compare_runs_some_baseline_some_contender_threshold_z_500.json"
    compare_file = response_dir / compare_json
    comparisons = MockResponse.from_file(compare_file).json()
    return {
        "run_id_1": deepcopy(comparisons),
        "run_id_2": deepcopy(comparisons),
    }


@pytest.mark.parametrize("include_regressions", [False, True])
def test_benchmarks_with_z_regressions(include_regressions):
    if include_regressions:
        expected = [
            ("run_id_1", "snappy, nyctaxi_sample, parquet, arrow"),
            ("run_id_2", "snappy, nyctaxi_sample, parquet, arrow"),
        ]
    else:
        expected = []

    actual = benchmarks_with_z_regressions(all_comparisons(include_regressions))
    assert actual == expected
