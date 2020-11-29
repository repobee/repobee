![RepoBee Logo](docs/images/RepoBee_large-black.png)

[![Build Status](https://travis-ci.com/repobee/repobee.svg)](https://travis-ci.com/repobee/repobee)
[![Code Coverage](https://codecov.io/gh/repobee/repobee/branch/master/graph/badge.svg)](https://codecov.io/gh/repobee/repobee)
[![Documentation Status](https://readthedocs.org/projects/repobee/badge/?version=stable)](http://repobee.readthedocs.io/en/stable/)
[![PyPi Version](https://badge.fury.io/py/repobee.svg)](https://badge.fury.io/py/repobee)
![Supported Python Versions](https://img.shields.io/badge/python-3.6%2C%203.7%2C%203.8-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Overview
RepoBee is a command line tool that allows teachers and teaching assistants
to administrate large amounts of Git repositories on the GitHub and GitLab
platforms (cloud and self-hosted). The most basic use case is to automate
generation of student repositories based on template repositories, that can
contain for example instructions and skeleton code. Given one or more template
repositories, generating copies of these for students or groups is a single
command away! That is however just scratching the surface: RepoBee also has
functionality for updating student repos (maybe you forgot something?), batch
cloning of student repos (convenient when correcting tasks), giving students
read-only access to other students' repos for peer review, and more at that!
There is also a [plugin system](https://github.com/repobee/repobee-plug) in
place that allows Python programmers to expand RepoBee in various ways, and end
users can simply install plugins created by others. An example of such a plugin
is [`repobee-junit4`](https://github.com/repobee/repobee-junit4), which runs
teacher-defined JUnit4 test classes on Java code in cloned student repos.

RepoBee is currently being used for the introductory courses in computer science at
[KTH Royal Technical Institute of Technology](https://www.kth.se/en/eecs). The
courses have roughly 200 students and several thousands of repositories,
allowing us to test RepoBee at quite a large scale.

### Citing RepoBee in an academic context
If you want to reference RepoBee in a paper, please cite the following paper:

> Simon Larsén and Richard Glassey. 2019. RepoBee: Developing Tool Support for
> Courses using Git/GitHub. In Proceedings of the 2019 ACM Conference on
> Innovation and Technology in Computer Science Education (ITiCSE '19). ACM,
> New York, NY, USA, 534-540. DOI: https://doi.org/10.1145/3304221.3319784

### Feature highlights
* Compatible with both GitHub and GitLab (both cloud and self-hosted)
* Generate repositories for students based on template repositories
* Batch cloning of student repositories
* Peer review features: give students read access to other students'
  repositories to do code review. Easily revoke read access once reviews are
  done.
* Support for group assignments (multiple students per repository)
* Open, close and list issues for select student repositories
* Extend RepoBee with the
  [plugin system](https://repobee.readthedocs.io/en/stable/plugins.html)
* Very little configuration required on the GitHub/GitLab side
    - The only requirement is to have an Organization/Group with private repository
      capabilities!
* No local configuration required
    - Although [setting a few defaults](https://repobee.readthedocs.io/en/stable/getting_started.html#configure-repobee-for-the-target-organization-the-config-category)
      is highly recommended

### Install
We provide an install script that sets up an isolated and correctly configured
environment for RepoBee. It supports macOS, Linux and Windows Subsystem for
Linux (WSL). You can execute it directly using `curl`, with either `bash` or
`zsh`.

> **IMPORTANT:** If you use any other shell than bash or zsh, you must still
> execute the install script with one of them.

```bash
$ bash <(curl -s https://repobee.org/install.sh)
```

```bash
$ zsh <(curl -s https://repobee.org/install.sh)
```

#### Required software
RepoBee requires Python 3.6+ and Git to be installed. The install script will
complain if they are not, and point you to relevant resources. When you have
installed the requirements, simply try the install script again.

#### Tab completion
RepoBee supports tab completion for `zsh` and `bash`. Follow the instructions
from the install script to activate tab completion.

### Getting started
The best way to get started with RepoBee is to head over to the
[Docs](https://repobee.readthedocs.io/en/stable/), where you (among other
things) will find the
[user guide](https://repobee.readthedocs.io/en/stable/userguide.html).
It covers the use of RepoBee's varous commands by way of practical example,
and should set you on the right path with little effort.

## Why RepoBee?
RepoBee is being developed at KTH Royal Technical Institute of Technology to
help teachers and TAs administrate student repositories. It's a tool for
teachers, by teachers, and we use it in our everyday work. All of the features
in RepoBee are being actively used by us, and so should also be useful to other
teachers.  For newcomers, RepoBee offers an opinionated workflow that is easy
to adopt, while the more advanced users can utilize the plugin system to
augment their experience. We also recognize that lock-in is a problem, and
therefore provide compatibility with both GitHub and GitLab, with hopes of also
expanding support to Bitbucket at some point. But what you're really looking
for is probably what RepoBee can do, so below is a list of RepoBee's command
categories, which should give you a rough idea of RepoBee's capabilities.

```
repobee -h
usage: repobee [-h] [-v] {repos,teams,issues,reviews,config,plugin,manage} ...

A CLI tool for administrating large amounts of git repositories on GitHub and
GitLab instances. Read the docs at: https://repobee.readthedocs.io

Loaded plugins: distmanager-3.0.0-alpha.7, pluginmanager-3.0.0-alpha.7

positional arguments:
  {repos,teams,issues,reviews,config,plugin,manage}
    repos               manage repositories
    teams               manage teams
    issues              manage issues
    reviews             manage peer reviews
    config              configure RepoBee
    plugin              manage plugins
    manage              manage the RepoBee installation

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         display version info
```

## Versioning
As of December 17th 2018, RepoBee's CLI is a stable release and adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The internals
of RepoBee _do not_ adhere to this versioning, so using RepoBee as a library
is not recommended.

The plugin system will be mostly stable as of RepoBee 3.0, but there is a
slight risk of breakage due to unforeseen problems. **If you develop a plugin,
please get in touch so that can be taken into consideration if breaking changes
are introduced to the plugin system**.

## License
This software is licensed under the MIT License. See the [LICENSE](LICENSE)
file for specifics.
