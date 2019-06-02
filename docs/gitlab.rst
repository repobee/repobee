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
migrate              WIP            June 2019
open-issues          Not started    June 2019
close-issues         Not started    June 2019
list-issues          Not started    June 2019
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
the value for option ``github_base_url``. That's really the only difference,
and of course, that you can only expect ``setup``, ``clone`` and ``update`` to
actually work.

.. important::
   
   Unlike when using GitHub, the URL provided for a GitLab instance should _not_
   be to the actual REST API, but to the landing page of the instance. For
   example, if you use gitlab.com, then you should provide ``github_base_url =
   https://gitlab.com`` in the config file (or analogously on the command line).


.. _`GitLab blog post`: https://about.gitlab.com/2017/09/11/comparing-confusing-terms-in-github-bitbucket-and-gitlab/
.. _`GitLab support Kanban board`: https://github.com/repobee/repobee/projects/7
