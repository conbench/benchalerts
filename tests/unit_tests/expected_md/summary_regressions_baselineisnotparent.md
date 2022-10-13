Contender commit `abc` had 2 regressions compared to its baseline commit.

### Benchmarks with regressions:

- Run ID [some_contender1](https://conbench/some_baseline1...some_contender1)
  - `snappy, nyctaxi_sample, parquet, arrow`

- Run ID [some_contender2](https://conbench/some_baseline2...some_contender2)
  - `snappy, nyctaxi_sample, parquet, arrow`

### Note

The baseline commit was not the immediate parent of the contender commit. If this is a pull request, that's probably okay, because the baseline is the commit from which your branch branched.
