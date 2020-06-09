# Integration tests for GitLab
This directory contains integration test stuff for testing with GitLab as a
platform. Note that all secrets here are generated solely for this integration
testing, so there is no need to panic about secret keys and certificates (all
self-signed and generated for this alone) in a public repository.

## Attribution
The [`docker-compose.yml`](docker-compose.yml) file is based on [this repo by
Daniel Eagle](https://github.com/GetchaDEAGLE/gitlab-https-docker).  It's
explained in full over there.

## Usage
Run `startup.sh` to start the GitLab instance. The GitLab instance should then
be runing at `https://gitlab.integrationtest.local`. It uses a bogus SSL cert
(obviously), so just ignore the warning about the connection not being safe.

Run `restore.sh` to restore the GitLab instance to its initial state.

Run `sudo docker-compose down` to shut down the GitLab instance.

### Login details
* Username: `root`
* Password: `password`
* OAUTH2 token: See the [token](token) file
    - This token is for the `repobee-user` user account

You can clone a repository using the token. For example, try `git clone
https://oauth2:<TOKEN>@gitlab.integrationtest.local/repobee-master/task-3.git`.

### Disabling SSL verification
In order to be able to run RepoBee with the GitLab instance, you must also
disable SSL verification both for Git and RepoBee.

```
$ export REPOBEE_NO_VERIFY_SSL=true
$ git config --global http.sslverify false
```

 **Always remember to re-enable SSL verification in Git when you are done.**

 ```
 $ git config --global http.sslverify true
 ```

## First-time setup for local development
First make sure that you have `docker` and `docker-compose` installed. Then
you need create a Docker network for the integrationtest.

```
$ sudo docker network create development
```

You will need to set up a few things to make the network redirect to the GitLab
instance properly. Add the following to your `/etc/hosts` file:

```
127.0.2.1       gitlab.integrationtest.local gitlab
```

Then change the `docker-compose.yml` file according to this patch:

```
         nginx['logrotate_delaycompress'] = "delaycompress"
         # Add any other gitlab.rb configuration options if desired
     ports:
-      - '50443:443'
-      - '50022:22'
+      - '443:443'
+      - '22:22'
     volumes:
       - ./volume_data/conf:/etc/gitlab
       - ./volume_data/ssl:/etc/ssl/certs/gitlab
```

That should be it. Run `startup.sh`, and when it's done you should be able to
connect to the GitLab instance at `https://gitlab.integrationtest.local`.

> **Important:** Ports `443` and `22` must be unused as you are trying to
> allocate them for the GitLab instance. Port `22` is often used by the `sshd`
> service, so you may need to shut that down before running `startup.sh`.

### Sample RepoBee configuration file
Replace `<TOKEN>` with [this token](token).

```
[DEFAULTS]
base_url = https://gitlab.integrationtest.local
token = <TOKEN>
org_name = repobee-testing
master_org_name = repobee-master
user = oauth2
plugins = gitlab
```
