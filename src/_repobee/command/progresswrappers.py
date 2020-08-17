"""Wrapper functions around API functions that provide progress bars."""

from typing import Iterable, Any, Union

import repobee_plug as plug

__all__ = ["get_repos"]


def get_repos(
    repo_names: Iterable[str],
    api: plug.PlatformAPI,
    desc: str = "Fetching repos",
    **kwargs: Any,
) -> Iterable[plug.Repo]:
    """Wrapper around :py:meth:`repobee_plug.PlatformAPI.get_repos` that also
    provides an auto-updating progress bar to the CLI.

    Args:
        repo_names: An iterable of repo names.
        api: An instance of the platform API.
        desc: A description of the action.
        kwargs: Keyword arguments to the underlying implementation of the
            progress bar.
    Returns:
        An iterable of repos with an auto-updating CLI progress bar.
    """
    repo_names = list(repo_names)
    return plug.cli.io.progress_bar(
        api.get_repos(repo_names), desc=desc, total=len(repo_names), **kwargs
    )


def get_teams(
    teams: Iterable[Union[plug.StudentTeam, str]],
    api: plug.PlatformAPI,
    desc: str = "Fetching teams",
    **kwargs: Any,
) -> Iterable[plug.Team]:
    """Wrapper around :py:meth:`repobee_plug.PlatformAPI.get_teams` that also
    displays a progress bar.

    Args:
        teams: An iterable of teams or team names.
        api: An instance of the platform API.
        desc: Description of the action.
        args: Keyword arguments for the underlying implementation of the
            progress bar.
    Returns:
        An iterable of fetched teams that also updates a CLI progress bar.
    """
    teams = list(teams)
    fetched_teams = api.get_teams(str(t) for t in teams)
    return plug.cli.io.progress_bar(
        fetched_teams, desc=desc, total=len(teams), **kwargs
    )
