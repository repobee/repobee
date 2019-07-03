.. _gitlab:

RepoBee and GitLab
******************
As of v1.5.0, RepoBee has alpha support for GitLab. Both gitlab.com and
self-hosted GitLab are supported, but currently, only a subset of the RepoBee
commands actually work with GitLab. GitLab is planned to be fully supported
by the end of August 2019.

Roadmap
=======
The roadmap for GitLab support is listed below. For the most up-to-date
activity, see the `GitLab support Kanban board`_.

===================  =============  ============
Command              Status         ETA/Added in
===================  =============  ============
show-config          Done           N/A (not platform dependent)
setup                Done           v1.5.0
update               Done           v1.5.0
clone                Done           v1.5.0
migrate              Done           v1.6.0
open-issues          Done           v1.6.0
close-issues         Done           v1.6.0
list-issues          Done           v1.6.0
assign-reviews       Not started    August 2019
purge-review-teams   Not started    August 2019
check-reviews        Not started    August 2019
verify-settings      Not started    August 2019
===================  =============  ============

GitLab terminology
==================
RepoBee uses GitHub terminology, as GitHub is the primary platform. It is
however simple to map the terminology between the two platforms as follows:

============  ========
GitHub        GitLab
============  ========
Organization  Group
Team          Subgroup
Repository    Project
Issue         Issue
============  ========

So, if you read "target organization" in the documentation, that translates
directly to "target group" when using GitLab. Although there are a few
practical differences, the concepts on both platforms are similar enough that
it makes no difference as far as using RepoBee goes. You can read more about
differences and similarities in this `GitLab blog post`_.

How to use RepoBee with GitLab
==============================
Provide the url to a GitLab instance as an argument to
``-g|--github-base-url`` (yes, it's a bit weird as it says ``github`` in the
option, but that will be changed in v2.0.0), or put it in the config file as
the value for option ``github_base_url``. That's really the only difference in
terms of CLI usage.

.. important::

   Unlike when using GitHub, the URL provided for a GitLab instance should _not_
   be to the actual REST API, but to the landing page of the instance. For
   example, if you use gitlab.com, then you should provide ``github_base_url =
   https://gitlab.com`` in the config file (or analogously on the command line).

Getting an OAUTH token for GitLab
---------------------------------
Creating an OAUTH token for a GitLab API is just as easy as creating one for
GitHub. Just follow `these instructions
<https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html>`_.
The scopes you need to tick are ``api``, ``read_user``, ``read_repository`` and
``write_repository``. That's it!

.. _`GitLab blog post`: https://about.gitlab.com/2017/09/11/comparing-confusing-terms-in-github-bitbucket-and-gitlab/
.. _`GitLab support Kanban board`: https://github.com/repobee/repobee/projects/7
