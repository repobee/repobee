# Contribute to RepoBee
As of version 2.0, RepoBee is open for contributions. There are a ton of things
to do, ranging from stability fixes, updating unit and system tests, improving
GitLab compatibility, contributing to the documentation, and so on. There are
two primary ways to contribute:

* Have a completely new idea (typically a bug report, feature or documentation
  request)
    - See [Bugs, docs and feature requests](#bugs-docs-and-feature-requests)
* Fix an outstanding issue on the [issue tracker](https://github.com/repobee/repobee/issues)
    - See [Fixing an oustanding issue](#fixing-an-outstanding-issue)

The two approaches differ only before actually starting to work on the issue
(see [Before you start](#before-you-start)). There is also a less obvious way
to contribute, and that is by writing a plugin. See the [Writing a
plugin](#writing-a-plugin) section below.

## Before you start
The two approaches mentioned above require slightly different starting points,
as outlined by the following two sections. Additionally, you will probably want
to have a look at the docs for setting up a development environment over at
[ReadTheDocs](https://repobee.readthedocs.io/latest/contributing.html).

### Bugs, docs and feature requests
If you want to do something that is not outlined by an existing issue, then
[open an issue](https://github.com/repobee/repobee/issues/new) stating what you
want to do. **Even if you don't intend to do it yourself, requests for
enhancements are appreciated.** It may also turn out that you can indeed do it
yourself with some guidance.

> **Important:** Please report security critical problems to by email to
> slarse@kth.se instead of posting them on the issue tracker.

### Fixing an outstanding issue
If you find an issue on the issue tracker that you would like to help fix, then
_before_ you start working on it, post a comment on the issue stating your
intentions. This is primarily to avoid starting work on something that I'm
already working on. If you get the all-clear, then just get to work and check
back in on the issue a little now and then to let people know that you're still
working on it!

## Working on your thing
[Fork the repository](https://help.github.com/en/articles/fork-a-repo) and do
your thing!

## Submitting a PR
When you have complete whatever you were working on, or want feedback on the
work you've done so far, it is time to submit a pull request. Go to the [pull
request page](https://github.com/repobee/repobee/pulls/compare), select
`repobee/master` as the base and your own fork and branch as the compare. Then
open the pull request and write whatever info is appropriate in its body. Wait
for feedback from a maintainer for further instructions. If the PR is accepted,
it will be merged into RepoBee core!

## Writing a plugin
The less involved way of contributing to RepoBee is to write a plugin, as
plugins do not need to be merged into RepoBee core, but can exist as separate
repositories. **You do not need any permission to create a plugin**, but it's
much appreciated if you [open an
issue](https://github.com/repobee/repobee/issues/new) and let me know about
it. If you're interested in writing a plugin, head over to the [repobee-plug
documentation](https://repobee-plug.readthedocs.io/en/latest/).  There is a
cookiecutter template to start from, so implementing a basic plugin can
literally take as little as a few minutes.

> **Note:** Plugins that are useful to a lot of people can be moved into the
> RepoBee GitHub organization, or even into the core RepoBee repository. Get in
> touch with me at slarse@kth.se if you are interested in getting your plugin
> moved here.
