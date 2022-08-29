Integration tests
-----------------

These tests will interact with various services like Github and Conbench. To run them,
you need these environment variables set. If they are not set correctly, the
corresponding tests will be skipped.

To run tests that post comments to pull requests:

- `GITHUB_API_TOKEN` - an API token that can post to https://github.com/conbench/benchalerts/pull/5
- `CI` - this env var must NOT be set, or the tests will be skipped. By default,
    `CI=true` in Github Actions, so we'll never run these tests in the CI build.

License information
-------------------

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
