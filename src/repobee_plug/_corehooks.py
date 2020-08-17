"""Hookspecs for repobee core hooks.

Core hooks provide the basic functionality of repobee. These hooks all have
default implementations, but are overridden by any other implementation. All
hooks in this module should have the `firstresult=True` option to the hookspec
to allow for this dynamic override.

.. module:: corehooks
    :synopsis: Hookspecs for repobee core hooks.
"""

from typing import List, Tuple

from repobee_plug import localreps
from repobee_plug import _containers
from repobee_plug._containers import hookspec


class PeerReviewHook:
    """Hook functions related to allocating peer reviews."""

    @hookspec(firstresult=True)
    def generate_review_allocations(
        self, teams: List[localreps.StudentTeam], num_reviews: int
    ) -> List[_containers.ReviewAllocation]:
        """Generate :py:class:`~repobee_plug.containers.ReviewAllocation`
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
        :py:class:`~repobee_plug.containers.ReviewAllocation` tuple, here
        called ``allocation``, should be contained in the returned list.

        .. code-block:: python

            review_team = plug.StudentTeam(
                members=team_a.members + team_b.members
            )
            allocation = containers.ReviewAllocation(
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


class APIHook:
    """Hooks related to platform APIs."""

    @hookspec(firstresult=True)
    def get_api_class(self):
        """Return an API platform class. Must be a subclass of apimeta.API.

        Returns:
            An apimeta.API subclass.
        """

    @hookspec(firstresult=True)
    def api_init_requires(self) -> Tuple[str]:
        """Return which of the arguments to apimeta._APISpec.__init__ that the
        given API requires. For example, the GitHubAPI requires all, but the
        GitLabAPI does not require ``user``.

        Returns:
            Names of the required arguments.
        """
