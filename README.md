# benchalerts

A package to facilitate automated alerting based on
[Conbench](https://github.com/conbench/conbench) data.

## Installing

To install the latest version:

    pip install git+https://github.com/conbench/benchalerts.git

To install a specific version (must specify a full MAJOR.MINOR.PATCH version):

    pip install git+https://github.com/conbench/benchalerts.git@0.1.0

## Contributing

To start, clone the repo, install the editable package, and initialize pre-commit:

    git clone https://github.com/conbench/benchalerts.git
    cd benchalerts

    # (it's recommended to activate a virtual environment first!)
    pip install -e '.[dev]'
    pre-commit install

After making changes, run tests:

    pytest tests/

This will run both unit and integration tests, but integration tests will be skipped if
the correct environment variables are not set. See `tests/integration_tests/README.md`
for instructions.

Code is linted with `black`, `flake8`, and `isort`. `pre-commit` should automatically
lint your code before a commit, but you can always lint manually by running

    pre-commit run --all-files

Please ensure new files contain our license header; this will be checked in CI as well.

## License information

Copyright (c) 2022, Voltron Data.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
