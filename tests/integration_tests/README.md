# Integration tests for GitLab
This directory contains integration test stuff for testing with GitLab as a
platform. Note that all secrets here are generated solely for this integration
testing, so there is no need to panic about secret keys and certificates (all
self-signed and generated for this alone) in a public repository.

### Attribution
The [`docker-compose.yml`](https://github.com/GetchaDEAGLE/gitlab-https-docker)
file is based on
[this repo by Daniel Eagle](https://github.com/GetchaDEAGLE/gitlab-https-docker).
It's explained in full over there.
