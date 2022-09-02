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

from typing import List, Tuple


def benchmarks_with_z_regressions(all_comparisons: dict) -> List[Tuple[str, str]]:
    """Find the run_ids and names of benchmarks whose z-scores were extreme enough to
    constitute a regression.

    Parameters
    ----------
    all_comparisons
        The output of ConbenchClient.get_comparison_to_baseline().

    Returns
    -------
    List[Tuple[str, str]]
        List of tuples of (run_id, benchmark_name) for all benchmarks with regressions.
    """
    return [
        (run_id, benchmark["benchmark"])
        for run_id, benchmarks in all_comparisons.items()
        for benchmark in benchmarks
        if benchmark["contender_z_regression"]
    ]
