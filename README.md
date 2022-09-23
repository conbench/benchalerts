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

    pytest -vvrs --log-level=DEBUG tests/

This will run both unit and integration tests, but integration tests will be skipped if
the correct environment variables are not set. See `tests/integration_tests/README.md`
for instructions.

Code is linted with `black`, `flake8`, and `isort`. `pre-commit` should automatically
lint your code before a commit, but you can always lint manually by running

    pre-commit run --all-files

Please ensure new files contain our license header; this will be checked in CI as well.

## GitHub App Authentication

The preferred method that `benchalerts` recommends for authenticating and posting to
GitHub is to use a machine user called a
[GitHub App](https://docs.github.com/en/developers/apps/getting-started-with-apps/about-apps).
Using an App will allow you to post using a "bot" entity without taking up a seat in
your organization, and will allow you to use the extra features of the
[Checks API](https://docs.github.com/en/rest/guides/getting-started-with-the-checks-api).
These features give much more context when analyzing benchmark runs.

Each Conbench server must create its own GitHub App for security reasons. To do so,
follow these instructions.

### Creating a GitHub App to work with `benchalerts`

1. Go to the official
    [GitHub instructions](https://docs.github.com/en/developers/apps/building-github-apps/creating-a-github-app)
    for creating an App.
    - If you are an admin of your GitHub organization, follow the instructions for "a
        GitHub App owned by an organization." This method is preferred because the org
        will own the app instead of a user, who may not be part of the org in the
        future. (This will not affect the identity of the bot that posts to GitHub, just
        the ownership of the App.)
    - If not, you can follow the instructions for "a GitHub App owned by a personal
        account." You will send an installation request to org admins after creating the
        app. You can always transfer the ownership of the app to an org later.
1. For the App Name, use `conbench-<your org>`.
1. For the Homepage URL, use the link to your Conbench server.
1. Ignore the Callback URL and Setup URL.
1. Uncheck the "Active" box under Webhook. Since this App will not be an active service,
    we don't need GitHub to push webhook events to the App.
1. For full use of this package, the App requires the following permissions:
    - Repository > Checks > Read and Write
    - Repository > Commit statuses > Read and Write
    - Repository > Pull requests > Read and Write
1. After creating the App, save the App ID for later.
1. In the App Settings, scroll down to Private Keys and generate a private key. This
    will download a file to your computer. Treat the contents of this file like a
    password.
1. IMPORTANT: After creation, go to
    `https://github.com/apps/<YOUR_APP_NAME>/installations/new` to install the new App
    on the repos you'd like it to be able to post to. You must be a member of the
    organization to install the App on. If you are not an admin, an email request will
    be sent to org admins, which must be approved.

### Running `benchalerts` as the GitHub App you created

All that's necessary to use `benchalerts` workflows that post to GitHub as your App is
to set the following environment variables:

- `GITHUB_APP_ID` - the App ID from above
- `GITHUB_APP_PRIVATE_KEY` - the _contents_ of the private key file from above. This is
    a multiline file, so ensure you quote the contents correctly if necessary.

Since `benchalerts` is usually used in CI, it's recommended to set these two environment
variables in your CI pipeline as secret env vars. Most CI systems have a mechanism for
doing this. For security reasons, do not check these values into version control.

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
