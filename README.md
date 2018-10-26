# repomate

[![Build Status](https://travis-ci.com/slarse/repomate.svg?token=1VKcbDz66bMbTdt1ebsN&branch=master)](https://travis-ci.com/slarse/repomate)
[![Code Coverage](https://codecov.io/gh/slarse/repomate/branch/master/graph/badge.svg)](https://codecov.io/gh/slarse/repomate)
[![Documentation Status](https://readthedocs.org/projects/repomate/badge/?version=latest)](http://repomate.readthedocs.io/en/latest/)
[![PyPi Version](https://badge.fury.io/py/repomate.svg)](https://badge.fury.io/py/repomate)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-Linux%2C%20macOS-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

`repomate` is A CLI tool for administrating large amounts of GitHub
repositories, geared towards teachers and GitHub Enterprise. `repomate` is
currently being used for the introductory courses in computer science at
[KTH Royal Technical Institute of Technology](https://www.kth.se/en/eecs). The
courses have roughly 200 students and several thousands of repositories,
allowing us to test `repomate` at quite a large scale.

### Getting started
The best way to get started with `repomate` is to head over to the
[Docs](https://repomate.readthedocs.io/en/latest/), where you (among other
things) will find the
[install instructions](https://repomate.readthedocs.io/en/latest/install.html)
and
[user guide](https://repomate.readthedocs.io/en/latest/userguide.html).


## Why `repomate`?
`repomate` was developed at KTH Royal Technical Institute of Technology to help
teachers and teaching assistants administrate GitHub repositories. It is
inspired by the old
[`teachers_pet` tool](https://github.com/education/teachers_pet), with added
features and a user experience more to our liking. Features range from creating
student repositories based on master (template) repos, to opening and closing
issues in bulk. `repomate` also allows for cloning repos in bulk, and executing
arbitrary tasks on the cloned repos by utlizing its simple but powerful
[plugin system](https://github.com/slarse/repomate-plug). Below is the output
from running `repomate -h`, giving brief descriptions of each of the main
featues:

```
(repomate-EQUnzodV) [repomate 2001] $ repomate -h
usage: repomate [-h] [-v]
                {setup,update,migrate,clone,add-to-teams,open-issues,close-issues,list-issues,
assign-peer-reviews,purge-peer-review-teams,verify-settings}
                ...

A CLI tool for administrating student repositories.

positional arguments:
  {setup,update,migrate,clone,add-to-teams,open-issues,close-issues,list-issues,assign-peer-reviews,purge-peer-review-teams,verify-settings}
    setup               Setup student repos.
    update              Update existing student repos.
    migrate             Migrate master repositories into the target
                        organization.
    clone               Clone student repos.
    add-to-teams        Create student teams and add students to them. This
                        command is automatically executed by the `setup`
                        command.
    open-issues         Open issues in student repos.
    close-issues        Close issues in student repos.
    list-issues         List issues in student repos.
    assign-peer-reviews
                        Manage peer review teams.
    purge-peer-review-teams
                        Remove all review teams associated with the specified
                        students and master repos.
    verify-settings     Verify your settings, such as the base url and the
                        OAUTH token.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Display version info

```

## License

This software is licensed under the MIT License. See the [LICENSE](LICENSE) file for specifics.
