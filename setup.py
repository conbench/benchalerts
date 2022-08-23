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

import setuptools

repo_root = pathlib.Path(__file__).parent

with open(repo_root / "README.md", "r") as f:
    long_description = f.read()

with open(repo_root / "requirements.txt", "r") as f:
    base_requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

with open(repo_root / "requirements-dev.txt", "r") as f:
    dev_requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

__version__ = ""
with open(repo_root / "benchalerts" / "_version.py", "r") as f:
    exec(f.read())  # only populates the __version__ variable

setuptools.setup(
    name="benchalerts",
    version=__version__,
    description="Automated alerting for conbench",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    entry_points={},
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache 2 License",
    ],
    python_requires=">=3.8",
    maintainer="Austin Dickey",
    maintainer_email="austin@voltrondata.com",
    url="https://github.com/conbench/benchalerts",
    install_requires=base_requirements,
    extras_require={"dev": dev_requirements},
)
