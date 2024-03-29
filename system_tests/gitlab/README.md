# GitLab system tests
This directory contains system tests for testing with GitLab as a platform.
Note that all secrets here are generated solely for this integration testing,
so there is no need to panic about secret keys and certificates (all
self-signed and generated for this alone) in a public repository.

## Attribution
The [`docker-compose.yml`](docker-compose.yml) file is based on [this repo by
Daniel Eagle](https://github.com/GetchaDEAGLE/gitlab-https-docker). It's
explained in full over there.

## Setting up
Before you can use any of the components in this directory, there are a few
things you need to do, as explained in the following subsections.

### Setup Docker
You need both `docker` and `docker-compose` in order to setup the GitLab
instance. Ensure that these are installed, and **make sure to start the Docker
daemon.** With systemd, you can do that like so:

```bash
$ sudo systemctl start docker
```

If you use something other than systemd, refer to the documentation of that
service manager.

### Disable SSL verification
In order to be able to run RepoBee with the GitLab instance, you must disable
SSL verification both for Git and RepoBee.

```bash
$ export REPOBEE_NO_VERIFY_SSL=true
$ git config --global http.sslverify false
# disabling warnings is recommended
$ export PYTHONWARNINGS="ignore:Unverified HTTPS request"
```

**Always remember to re-enable SSL verification in Git when you are done.**

```bash
$ git config --global http.sslverify true
```

## Usage
The systems test GitLab instance can be used for two things: running the system
tests, and local development of RepoBee with the test instance. Regardless of
which of these use cases you intend to go with, ensure that you've first
performed the [setup steps](#setting-up).

### Running the system tests
Assuming you've got everything setup correctly, executing the system tests
should be as simple as this.

```bash
$ python -m pytest test_gitlab_system.py
```

> **Note:** You may need `sudo` depending on if you're part of the `docker`
> group or not.

### Using the GitLab instance for local development
The `gitlabmanager.py` script manages the GitLab test instance. Run it with
`python gitlabmanager.py <command>`, where `<command>` is typically one of the
following.

> **Note:** You may need to execute with `sudo` if you're not part of the
> `docker` group.

* `setup`: Setup the instance, including users and the access token for the
  RepoBee user.
  - To change the users, edit [`students.txt`](students.txt)
  - The RepoBee user is hard-coded in the `TEACHER`
    constant in [`_helpers/const.py`](_helpers/const.py)
* `teardown`: Tear down the instance and remove any files managed by it.
* `restore`: Setup the template group (with template repos) and the target group.

The base URL for the GitLab instance is `https://localhost:3000`. Of course,
you will also need to activate the `gitlab` plugin for RepoBee.

#### Login details
If you've run the `setup` command, you should now be able to access the
instance at `https://localhost:3000`, and login with the following credentials.

* Username: `root`
* Password: `password`
* OAUTH2 token: See the [token file](token)

You can clone a repository using the token. For example, try `git clone
https://oauth2:<TOKEN>@localhost:3000/dd1337-master/task-3.git`.
Note that you must have executed the `restore` command at least once for
this to work.

### Sample RepoBee configuration file
Replace `<TOKEN>` with [this token](token).

```
[repobee]
base_url = https://localhost:3000
token = <TOKEN>
org_name = dd1337-fall2020
template_org_name = dd1337-master
user = oauth2
```

> **Important:** Also remember to activate the `gitlab` plugin with `repobee
> plugin activate`.
