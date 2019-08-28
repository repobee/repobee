.. _gitlab:

RepoBee and GitLab
******************
As of v1.5.0, RepoBee has alpha support for GitLab. Both https://gitlab.com and
self-hosted GitLab are supported, but currently, some commands (including all
peer review commands) do not work. GitLab is planned to be fully supported by
in late 2019. See :ref:`gitlab_roadmap` for details.

.. note::

   GitLab support is currently in alpha, and may not yet be sufficiently stable
   for production use. Please report any issues on the `issue tracker
   <https://github.com/repobee/repobee/issues/new>`_

.. important::

   RepoBee requires GitLab 11.11 or later.

.. _gitlab_roadmap:

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
assign-reviews       Not started    Late 2019
end-reviews          Not started    Late 2019
check-reviews        Not started    Late 2019
verify-settings      Not started    v2.3.0
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
You must use the ``gitlab`` plugin for RepoBee to be able to interface with
GitLab. See :ref:`configure_plugs` for instructions on how to use plugins.
Provide the url to a GitLab instance host (*not* to the api endpoint, just to
the host) as an argument to ``--bu|--base-url``, or put it in the config file as
the value for option ``base_url``. Other than that, there are a few important
differences between GitHub and GitLab that the user should be aware of.

* As noted, the base url should be provided to the host of the GitLab instance,
  and not to any specific endpoint (as is the case when using GitHub). When
  using ``github.com`` for example, the url should be provided as
  ``base_url = https://gitlab.com`` in the config.
* The ``org-name`` and ``master-org-name`` arguments should be given the *path*
  of the respective groups. If you create a group with a long name, GitLab may
  shorten the path automatically. For example, I created the group
  ``repobee-master-repos``, and it got the path ``repobee-master``. You can find
  your path by going to the landing page of your group and checking the URL: the
  path is the last part. You can change the path manually by going to your
  group, then `Settings->General->Path,transfer,remove` and changing the group
  path.

.. _gitlab access token:

Getting an access token for GitLab
----------------------------------
Creating a personal access token token for a GitLab API is just as easy as
creating one for GitHub. Just follow `these instructions
<https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html>`_.  The
scopes you need to tick are ``api``, ``read_user``, ``read_repository`` and
``write_repository``. That's it!

.. _`GitLab blog post`: https://about.gitlab.com/2017/09/11/comparing-confusing-terms-in-github-bitbucket-and-gitlab/
.. _`GitLab support Kanban board`: https://github.com/repobee/repobee/projects/7
