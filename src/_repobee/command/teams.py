from typing import Iterable
import repobee_plug as plug


def create_teams(
    teams: Iterable[plug.Team], permission: plug.TeamPermission, api: plug.API
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
        existing_team = existing_teams_dict.get(required_team.name)
        if existing_team:
            existing_members = set(existing_team.members)
            new_members = set(required_team.members) - existing_members
            api.assign_members(existing_team, new_members, permission)
            # TODO yield refreshed team
            yield existing_team
        else:
            new_team = api.create_team(
                required_team.name, required_team.members, permission
            )
            yield new_team
