"""Hookspecs for repobee core hooks.

Core hooks provide the basic functionality of repobee. These hooks all have
default implementations, but are overridden by any other implementation. All
hooks in this module should have the `firstresult=True` option to the hookspec
to allow for this dynamic override.

.. module:: corehooks
    :synopsis: Hookspecs for repobee core hooks.
"""

from typing import List, Tuple, Union

from repobee_plug import localreps, hook, reviews, platform


#####################
# Hooks for reviews #
#####################


@hook.hookspec(firstresult=True)
def generate_review_allocations(
    teams: List[localreps.StudentTeam], num_reviews: int
) -> List[reviews.ReviewAllocation]:
    """Generate :py:class:`~repobee_plug.ReviewAllocation`
    tuples from the provided teams, given that this concerns reviews for a
    single master repo.

    The provided teams of students should be treated as units. That is to
    say, if there are multiple members in a team, they should always be
    assigned to the same review team. The best way to merge two teams
    ``team_a`` and ``team_b`` into one review team is to simply do:

    .. code-block:: python

        team_c = plug.StudentTeam(members=team_a.members + team_b.members)

    This can be scaled to however many teams you would like to merge. As a
    practical example, if teams ``team_a`` and ``team_b`` are to review
    ``team_c``, then the following
    :py:class:`~repobee_plug.ReviewAllocation` tuple, here
    called ``allocation``, should be contained in the returned list.

    .. code-block:: python

        review_team = plug.StudentTeam(
            members=team_a.members + team_b.members
        )
        allocation = plug.ReviewAllocation(
            review_team=review_team,
            reviewed_team=team_c,
        )

    .. note::

        Respecting the ``num_reviews`` argument is optional: only do it if
        it makes sense. It's good practice to issue a warning if
        num_reviews is ignored, however.

    Args:
        team: A list of student teams.
        num_reviews: Amount of reviews each student should perform (and
            consequently amount of reviewers per repo)
    Returns:
        A list of review allocations tuples.
    """


##############################
# Hooks for the platform API #
##############################


@hook.hookspec(firstresult=True)
def get_api_class():
    """Return an API platform class. Must be a subclass of apimeta.API.

    Returns:
        An apimeta.API subclass.
    """


@hook.hookspec(firstresult=True)
def api_init_requires() -> Tuple[str]:
    """Return which of the arguments to apimeta._APISpec.__init__ that the
    given API requires. For example, the GitHubAPI requires all, but the
    GitLabAPI does not require ``user``.

    Returns:
        Names of the required arguments.
    """


############################
# Hooks for naming schemes #
############################


@hook.hookspec(firstresult=True)
def generate_repo_name(
    team_name: Union[str, localreps.StudentTeam, platform.Team],
    assignment_name: str,
) -> str:
    """This hook allows for overriding the behavior of
    :py:func:`repobee_plug.name.generate_repo_name`.

    .. danger::

        The implementations of this hook should never be invoked other than in
        :py:func:`repobee_plug.name.generate_repo_name`.

    Args:
        team_name: Name of the associated team.
        assignment_name: Name of an assignment.
    """
