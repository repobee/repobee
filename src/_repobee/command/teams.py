from typing import Iterable
import repobee_plug as plug


def create_teams(
    teams: Iterable[plug.StudentTeam],
    permission: plug.TeamPermission,
    api: plug.PlatformAPI,
) -> Iterable[plug.Team]:
    """Create teams.

    Args:
        teams: An iterable of teams to create.
        permission: The permission to assign to the team with respect to its
            repositories.
        api: A platform API instance.
    Returns:
        An iterable of wrappers around created teams.
    """
    teams = list(teams)
    existing_teams_dict = {
        existing.name: existing
        for existing in api.get_teams({t.name for t in teams})
    }
    for required_team in teams:
        team = existing_teams_dict.get(required_team.name) or api.create_team(
            required_team.name,
            members=required_team.members,
            permission=permission,
        )
        existing_members = set(team.members)
        new_members = set(required_team.members) - existing_members
        api.assign_members(team, new_members, permission)

        # FIXME the returned team won't have the correct members if any new
        # ones are added. This should be fixed by disconnecting members
        # from teams, and having an api call "get_team_members"

        yield team
