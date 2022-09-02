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
