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
to have a look at the
[docs for setting up a development environment](https://repobee.readthedocs.io/en/stable/contributing.html).

### Bugs, docs and feature requests
If you want to do something that is not outlined by an existing issue, then
[open an issue](https://github.com/repobee/repobee/issues/new) stating what you
want to do. **Even if you don't intend to do it yourself, requests for
enhancements are appreciated.** It may also turn out that you can indeed do it
yourself with some guidance.

> **Important:** Please report security critical problems to by email to
> slarse@slar.se instead of posting them on the issue tracker.

### Fixing an outstanding issue
If you find an issue on the issue tracker that you would like to help fix, then
_before_ you start working on it, post a comment on the issue stating your
intentions. This is to avoid starting work on something that is already being
worked on. If you get the all-clear, then just get to work and check back in on
the issue a little now and then to let people know that you're still working on
it!

## Working on your thing
[Fork the repository](https://help.github.com/en/articles/fork-a-repo) and do
your thing!

## Submitting a pull request
When you have completed whatever you were working on, or want feedback on the
work you've done so far, it is time to submit a pull request. Go to the [pull
request page](https://github.com/repobee/repobee/pulls/compare), select
`repobee/master` as the base and your own fork and branch as the compare.

### Pull request title
The pull request title should ideally be on the following form:

```
[<TAG>] <DESCRIPTION>
```

> **Note:** If the instructions seem frighteningly complex, don't worry too
> much about it. Just make a best effort attempt, and we'll help out making the
> title align with these instructions.

The `<DESCRIPTION>` should be written like a commit message, on imperative
form. For example, `Remove finder plugin` or `Add instructions for integration
test setup`.

The `<TAG>` categorizes the type of PR, and is both used for easy
identification of the PR subject, and for automatically generating change notes
on new releases. The following tags are currently used.

* `wip` - Indicates that the PR is not yet ready to be merged. We will not merge
  a PR that has the `wip` tag.
* `feat` - A new or enhanced feature. Must be backwards compatible.
* `break` - Removal of a feature, or addition of a feature that requires
  backwards incompatible changes.
* `fix` - A bug fix.
* `fact` - A refactoring.
* `docs` - For PRs that only touch documentation.
* `test` - For PRs that only touch test code.

For examples, [just have a look at past
PRs](https://github.com/repobee/repobee/pulls?q=is%3Apr+is%3Aclosed)

### Pull request body
The first line of the body should indicate which issue the PR is related to.
Typically, it should say `Fix #<ISSUE_NR>`. If the PR is not intended to
entirely fix an issue, but is related, then just write `#<ISSUE_NR>`.

The rest of the body should describe the PR, if applicable (very small and/or
obvious PRs may not need a description). If you need help, this is also the
place to ask for it. Again, don't worry too much about this, just write what you
feel is relevant and we will prod for any information we feel is missing.

## Writing a plugin
The less involved way of contributing to RepoBee is to write a plugin, as
plugins do not need to be merged into RepoBee core, but can exist as separate
repositories. **You do not need any permission to create a plugin**, but it's
much appreciated if you [open an
issue](https://github.com/repobee/repobee/issues/new) and let us know about
it. If you're interested in writing a plugin, head over to the [repobee-plug
documentation](https://repobee-plug.readthedocs.io/en/latest/). There is a
cookiecutter template to start from, so implementing a basic plugin can
literally take as little as a few minutes.

> **Note:** Plugins that are useful to a lot of people can be moved into the
> RepoBee GitHub organization, or even into the core RepoBee repository. Get in
> touch at slarse@slar.se if you are interested in getting your plugin moved
> here.
