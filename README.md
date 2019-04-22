# RepoBee - A CLI tool for administrating Git repositories on GitHub
[![Build Status](https://travis-ci.com/repobee/repobee.svg)](https://travis-ci.com/repobee/repobee)
[![Code Coverage](https://codecov.io/gh/repobee/repobee/branch/master/graph/badge.svg)](https://codecov.io/gh/repobee/repobee)
[![Documentation Status](https://readthedocs.org/projects/repobee/badge/?version=latest)](http://repobee.readthedocs.io/en/latest/)
[![PyPi Version](https://badge.fury.io/py/repobee.svg)](https://badge.fury.io/py/repobee)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Overview
RepoBee is A CLI tool for administrating large amounts of Git repositories,
geared towards teachers and GitHub Enterprise. The most basic use case is to
automate generation of student repositories based on master (i.e. template)
repositories, that can contain for example instructions and skeleton code.
There is however a whole lot more on offer, such as batch updating and cloning,
simple peer review functionality as well as issue management features. There is
also a [plugin system](https://github.com/repobee/repobee-plug) in place that
allows Python programmers to expand RepoBee in various ways. The
[`repobee-junit4` plugin](https://github.com/repobee/repobee-junit4) plugin is
one such plugin, which runs JUnit4 test classes on Java code in cloned student
repos.

RepoBee is currently being used for the introductory courses in computer science at
[KTH Royal Technical Institute of Technology](https://www.kth.se/en/eecs). The
courses have roughly 200 students and several thousands of repositories,
allowing us to test RepoBee at quite a large scale.

### Feature highlights

* Generate repositories for students based on master (template) repositories
* Clone student repositories in batches
* Peer review features: give students read access to other students'
  repositories to do code review. Easily revoke read access once reviews are
  done.
* Support for group assignments (multiple students per repository)
* Open, close and list issues for select student repositories
* Extend RepoBee with the
  [plugin system](https://repobee.readthedocs.io/en/latest/plugins.html)
* Support both for GitHub Enterprise and github.com
    - **GitLab support in the works**, see [Upcoming features](#upcoming-features)
* Very little configuration required on the GitHub side
    - The only requirement is to have an Organization with private repository
      capabilities!
* No local configuration required
    - Although [setting a few defaults](https://repobee.readthedocs.io/en/latest/configuration.html#configuration)
      is highly recommended

### Install
RepoBee is on PyPi, so `python3 -m pip install repobee` should do the trick. See the
[install instructions](https://repobee.readthedocs.io/en/latest/install.html)
for more elaborate instructions.

### Getting started
The best way to get started with RepoBee is to head over to the
[Docs](https://repobee.readthedocs.io/en/latest/), where you (among other
things) will find the
[user guide](https://repobee.readthedocs.io/en/latest/userguide.html).
It covers the use of RepoBee's varous commands by way of practical example,
and should set you on the right path with little effort.

## Why RepoBee?
RepoBee was developed at KTH Royal Technical Institute of Technology to help
teachers and TAs administrate GitHub repositories. It's a tool for teachers, by
teachers, and we use it in our everyday work. All of the features in RepoBee
are of some use to us, and so should also be useful to other teachers. Below is
a complete list of core functionality as described by the `--help` option.

```
$ repobee -h
usage: repobee [-h] [-v]
                {show-config,setup,update,migrate,clone,open-issues,
                 close-issues,list-issues,assign-reviews,
                 purge-review-teams,check-reviews,verify-settings}
                ...

A CLI tool for administering large amounts of git repositories on GitHub
instances. See the full documentation at https://repobee.readthedocs.io

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
As of December 17th 2018, RepoBee's CLI is a stable release and adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The internals
of RepoBee _do not_ adhere to this versioning, so using RepoBee as a library
is not recommended.

The plugin system is considered to be in the alpha phase, as it has seen much
less live action use than the rest of the CLI. Features are highly unlikely to
be cut, but hooks may be modified as new use-cases arise as the internals of
RepoBee need to be altered.

### Upcoming features
There is still a lot in store for RepoBee. Below is a roadmap for major
features that are in the works.

| Feature                                   | Status                                                                    | ETA                       |
| -------                                   | ------                                                                    | ---                       |
| GitLab support                            | Work in progress ([#172](https://github.com/repobee/repobee/issues/172))  | Beta release by June 2019 |
| Peer review support for group assignments | Work in progress  ([#167](https://github.com/repobee/repobee/issues/167)) | June 2019                 |
| Cleaner CLI help menus                    | Work in progress ([#164](https://github.com/repobee/repobee/issues/164))  | May 2019                  |
| Plugin support for top-level CLI commands | Planning                                                                  | TBA                       |
| Travis CI plugin                          | Planning ([#165](https://github.com/repobee/repobee/issues/165))          | TBA                       |

## License
This software is licensed under the MIT License. See the [LICENSE](LICENSE)
file for specifics.
