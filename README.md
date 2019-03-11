# repomate
[![Build Status](https://travis-ci.com/slarse/repomate.svg)](https://travis-ci.com/slarse/repomate)
[![Code Coverage](https://codecov.io/gh/slarse/repomate/branch/master/graph/badge.svg)](https://codecov.io/gh/slarse/repomate)
[![Documentation Status](https://readthedocs.org/projects/repomate/badge/?version=latest)](http://repomate.readthedocs.io/en/latest/)
[![PyPi Version](https://badge.fury.io/py/repomate.svg)](https://badge.fury.io/py/repomate)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Overview
Repomate is A CLI tool for administrating large amounts of GitHub
repositories, geared towards teachers and GitHub Enterprise. Repomate is
currently being used for the introductory courses in computer science at
[KTH Royal Technical Institute of Technology](https://www.kth.se/en/eecs). The
courses have roughly 200 students and several thousands of repositories,
allowing us to test Repomate at quite a large scale.

### Install
Repomate is on PyPi, so `python3 -m pip install repomate` should do the trick. See the
[install instructions](https://repomate.readthedocs.io/en/latest/install.html)
for more elaborate instructions.

### Getting started
The best way to get started with Repomate is to head over to the
[Docs](https://repomate.readthedocs.io/en/latest/), where you (among other
things) will find the
[user guide](https://repomate.readthedocs.io/en/latest/userguide.html).
It covers the use of Repomate's varous commands by way of practical example,
and should set you on the right path with little effort.

## Why Repomate?
Repomate was developed at KTH Royal Technical Institute of Technology to help
teachers and teaching assistants administrate GitHub repositories. It is
inspired by the old
[`teachers_pet` tool](https://github.com/education/teachers_pet), with added
features and a user experience more to our liking. Features range from creating
student repositories based on master (template) repos, to opening and closing
issues in bulk, to assigning peer reviews and cloning repos in bulk. Some parts
of Repomate can be customized using a simple but powerful [plugin
system](https://github.com/slarse/repomate-plug). For example, the
[`repomate-junit4` plugin](https://github.com/slarse/repomate-junit4) allows for
automatically running `JUnit4` test classes on production code in student repos.
Below is the output from running `repomate -h`, giving brief descriptions of
each of the main features:

```
$ repomate -h
usage: repomate [-h] [-v]
                {show-config,setup,update,migrate,clone,open-issues,
                 close-issues,list-issues,assign-reviews,
                 purge-review-teams,check-reviews,verify-settings}
                ...

A CLI tool for administering large amounts of git repositories on GitHub
instances. See the full documentation at https://repomate.readthedocs.io

positional arguments:
  {show-config,setup,update,migrate,clone,open-issues,
   close-issues,list-issues,assign-reviews,
   purge-review-teams,check-reviews,verify-settings}
    show-config         Show the configuration file
    setup               Setup student repos.
    update              Update existing student repos.
    migrate             Migrate master repositories into the target
                        organization.
    clone               Clone student repos.
    open-issues         Open issues in student repos.
    close-issues        Close issues in student repos.
    list-issues         List issues in student repos.
    assign-reviews      Randomly assign students to peer review each others'
                        repos.
    purge-review-teams  Remove all review teams associated with the specified
                        students and master repos.
    check-reviews       Fetch all peer review teams for the specified student
                        repos, and check which assigned reviews have been done
                        (i.e. which issues have been opened).
    verify-settings     Verify your settings, such as the base url and the
                        OAUTH token.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Display version info

```

## Roadmap
As of December 17th 2018, Repomate's CLI is a stable release and adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The internals
of Repomate _do not_ adhere to this versioning, so using Repomate as a library
is not recommended.

The plugin system is still to be considered in the beta phase, as it has seen
much less live action use than the rest of the CLI. Features are highly
unlikely to be cut, but hooks may be modified as new use-cases arise.

## License
This software is licensed under the MIT License. See the [LICENSE](LICENSE)
file for specifics.
