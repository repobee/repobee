# repomate

[![Build Status](https://travis-ci.com/slarse/repomate.svg?token=1VKcbDz66bMbTdt1ebsN&branch=master)](https://travis-ci.com/slarse/repomate)
[![Code Coverage](https://codecov.io/gh/slarse/repomate/branch/master/graph/badge.svg)](https://codecov.io/gh/slarse/repomate)
[![Documentation Status](https://readthedocs.org/projects/repomate/badge/?version=latest)](http://repomate.readthedocs.io/en/latest/?badge=latest)
[![PyPi Version](https://badge.fury.io/py/repomate.svg)](https://badge.fury.io/py/repomate)
![Supported Python Versions](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg)
![Supported Platforms](https://img.shields.io/badge/platforms-OSX%2C%20Linux-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)


### Overview

A CLI tool for administrating large amounts of GitHub repositories, geared towards teachers.

### Install

#### Requirements
`repomate` requires Python 3.5+ and a somewhat up-to-date version of `git`.
Officially supported platforms are `Ubuntu 17.04+` and `OSX`, but `repomate`
should run fine on any Linux distribution and also on
[WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10) on Windows 10.
Please report any issues with operating systems and/or `git` versions on the
issue tracker.


#### Option 1: Install from PyPi with `pip`

> **Important:** Not yet available on PyPi!

The latest release of `repomate` is on PyPi, and can thus be installed as usual with `pip`.
I strongly discourage system-wide `pip` installs (i.e. `sudo pip install <package>`), as this
may land you with incompatible packages in a very short amount of time. A per-user install
can be done like this:

1. Execute `pip install --user repomate` to install the package.
2. Further steps to be added ...


#### Option 2: Clone the repo and the install with `pip`

If you want the dev version, you will need to clone the repo, as only release versions are uploaded
to PyPi. Unless you are planning to work on this yourself, I suggest going with the release version.

1. Clone the repo with `git`:
    - `git clone https://github.com/slarse/repomate`
2. `cd` into the project root directory with `cd repomate`.
3. Install the requirements with `pip install -r requirements.txt`
    - To be able to run the tests, you must install the `requirements.test.txt` file.
4. Install locally with `pip`.
    - `pip install --user .`, this will create a local install for the current user.
    - Or just `pip install .` if you use `virtualenv`.
    - For development, use `pip install -e .` in a `virtualenv`.
5. Further steps to be added ...


### Configuration

There is one mandatory environment variable, and an optional configuration file
that can be added.

#### GITS_PET_OAUTH

For the tool to work at all, an environment variable called `GITS_PET_OAUTH`
must contain an OAUTH2 token to whichever GitHub instance you intend to use.
See [the GitHub docs](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/)
for how to create a token. Once you have it, configure the environment
variable with `export GITS_PET_OAUTH=<YOUR TOKEN>`. If it is not
configured, you will get an error message when trying to run `repomate`

#### Config file

An optional configuration file can be added, which specifies default values
for the `--github_base_url`, `--org_name`, `--user` and
`--students-list` command line options. The file should look
something like this:


```bash
[DEFAULTS]
github_base_url = https://some-api-v3-url
user = YOUR_USERNAME
org_name = ORGANIZATION_NAME
students_file = STUDENTS_FILE_ABSOLUTE_PATH
```

To find out where to place the file (and what to name it) run `repomate -h`.
At the very top, there should be a line looking something like this:

`[INFO] no config file found. Expected config file location: /home/USERNAME/.config/repomate/config.cnf`

The filepath at the end is where you should put your config file.

### Running repomate

Run `repomate -h` for usage. All the commands have help sections of their own,
so e.g. `gits-pet setup -h` will provide the help section for the `setup`
command.
   
### License

This software is licensed under the MIT License. See the [LICENSE](LICENSE) file for specifics.

### Contributing

To be added ...
