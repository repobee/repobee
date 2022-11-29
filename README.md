![RepoBee Logo](docs/images/RepoBee_large-black.png)

![Build Status](https://github.com/repobee/repobee/workflows/tests/badge.svg)
[![Code Coverage](https://codecov.io/gh/repobee/repobee/branch/master/graph/badge.svg)](https://codecov.io/gh/repobee/repobee)
[![Documentation Status](https://readthedocs.org/projects/repobee/badge/?version=stable)](http://repobee.readthedocs.io/en/stable/)
[![PyPi Version](https://badge.fury.io/py/repobee.svg)](https://badge.fury.io/py/repobee)
![Supported Python Versions](https://img.shields.io/badge/python-3.8%2C%203.9%2C%203.10%2C%203.11-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Overview
RepoBee is a command line tool that allows teachers and teaching assistants to
work with large amounts of student Git repositories on the GitHub, GitLab and
Gitea platforms (cloud and self-hosted). The archetypical use case is to
automate creation of student repositories based on template repositories, that
can contain for example instructions and skeleton code. Given any number of
template repositories, creating a copy for each student or group is
[just one command away](https://docs.repobee.org/en/stable/repos.html#set-up-student-repositories-the-setup-action).
RepoBee also has functionality for
[updating student repos](https://docs.repobee.org/en/stable/repos.html#updating-student-repositories-the-update-action),
[batch cloning of student repos](https://docs.repobee.org/en/stable/repos.html#cloning-repos-in-bulk-the-clone-action),
[opening, closing and listing issues](https://docs.repobee.org/en/stable/issues.html),
[no-blind](https://docs.repobee.org/en/stable/peer.html) and
[double-blind](https://docs.repobee.org/en/stable/peer.html#double-blind-peer-review)
peer review, and much more!

In addition, RepoBee features a powerful
[plugin system](https://docs.repobee.org/en/stable/plugins.html) that allows
users to either use existing plugins, or
[write their own](https://docs.repobee.org/en/stable/repobee_plug/index.html).
Plugins can do a wide range of things, including making RepoBee compatible with
multiple hosting platforms (GitHub, GitLab, Gitea), providing compatibility
with repositories managed by GitHub Classroom, or running JUnit4 test classes
on cloned student repositories.

Still not quite sure what RepoBee actually does? The demo video below briefly
explains some of the most important concepts, and showcases how RepoBee can be
used to setup and clone student repositories, as well as how to write a simple
plugin.

https://user-images.githubusercontent.com/14223379/121573132-2d725380-ca25-11eb-8aa0-8f50ac3f28f0.mp4

> Short video demonstration of using RepoBee and writing a simple plugin. [For a higher-quality version of this demo, click this link!](https://repobee.org/media/repobee-demo.mp4)

### Feature highlights
RepoBee has a lot going for it. Here are some of the things we are most proud
of:

* Compatible with GitHub, GitLab and Gitea: No platform lock-in!
* Support for group assignments (multiple students per repository)
* No-blind and double-blind peer review, directly on the hosting platform
* Generate, clone and update student repositories based on templates
* Open, close and list issues
* Extend and customize RepoBee with the
  [plugin system](https://repobee.readthedocs.io/en/stable/plugins.html)
* Very little configuration required on the Git service platform side
    - The only requirement is to have an Organization/Group with private repository
      capabilities!
* No local configuration required
    - Although [setting a few defaults](https://docs.repobee.org/en/stable/getting_started.html#configure-repobee-for-the-target-organization-the-config-category)
      is highly recommended

For a full list of RepoBee's built-in (i.e. non-plugin) features, see the
[user guide](https://docs.repobee.org/en/stable/userguide.html) and
[CLI reference](https://docs.repobee.org/en/stable/cli.html).

### Getting started
First, either [install RepoBee](#install) or grab the [Docker image](#docker).
Then, start exploring the [Docs](https://repobee.readthedocs.io/en/stable/),
where you (among other things) will find the [user
guide](https://repobee.readthedocs.io/en/stable/userguide.html). It covers use
of RepoBee's various commands by way of practical example, and should set you
on the right path with little effort.

We also provide a [Gitea test instance](https://gitea.repobee.org) for playing
around around with RepoBee in an environment where messing up has no
consequence. See the
[RepoBee Gitea docs](https://docs.repobee.org/en/stable/gitea.html) for details
on how to use RepoBee with Gitea.

### Install
We provide an install script that sets up an isolated and correctly configured
environment for RepoBee, granted that you have [Python 3.8+ and Git
installed](https://docs.repobee.org/en/stable/install.html#requirements). The script
supports macOS, Linux and Windows Subsystem for Linux (WSL). You can execute it
directly using `curl`, with either `bash` or `zsh`.

> **IMPORTANT:** If you use any other shell than bash or zsh, you must still
> execute the install script with one of them.

```bash
$ bash <(curl -s https://repobee.org/install.sh)
```

```bash
$ zsh <(curl -s https://repobee.org/install.sh)
```

For additional details, please see [the install
docs](https://docs.repobee.org/en/stable/install.html).

### Docker
We offer a fully featured
[Docker image](https://docs.repobee.org/en/stable/docker.html#docker-usage)
that can be used instead of installing RepoBee.

## Versioning
As of December 17th 2018, RepoBee's CLI is a stable release and adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The internals
of RepoBee _do not_ adhere to this versioning, so using RepoBee as a library
is not recommended.

The plugin system is mostly stable as of RepoBee 3.0, but there is a slight
risk of breakage due to unforeseen problems. **If you develop a plugin, please
get in touch so that can be taken into consideration if breaking changes are
introduced to the plugin system**.

## License
This software is licensed under the MIT License. See the [LICENSE](LICENSE)
file for specifics.

## Citing RepoBee in an academic context
If you want to reference RepoBee in a paper, please cite the following paper:

> Simon Larsén and Richard Glassey. 2019. RepoBee: Developing Tool Support for
> Courses using Git/GitHub. In Proceedings of the 2019 ACM Conference on
> Innovation and Technology in Computer Science Education (ITiCSE '19). ACM,
> New York, NY, USA, 534-540. DOI: https://doi.org/10.1145/3304221.3319784
