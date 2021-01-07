"""Gitea compatibility plugin.

This plugin allows RepoBee to be used with Gitea.

.. warning::

    This plugin is in very early stages of development. It should only be used
    for development purposes at this time.
"""
import pathlib
import json
import re
import os
import urllib.parse
from typing import Optional, List, Iterable

import repobee_plug as plug
import requests

_TEAM_PERMISSION_MAPPING = {
    plug.TeamPermission.PULL: "read",
    plug.TeamPermission.PUSH: "write",
}

PLUGIN_DESCRIPTION = """
Gitea compatibility plugin (WARNING: This plugin is in very early development,
use at your own risk)
""".replace(
    "\n", " "
).strip()


class GiteaAPI(plug.PlatformAPI):
    def __init__(self, base_url: str, user: str, token: str, org_name: str):
        plug.log.warning(
            "The Gitea plugin is in very early development, "
            "use at your own risk!"
        )

        if not self._ssl_verify():
            plug.log.warning("SSL verification turned off, only for testing")

        self._base_url = base_url.rstrip("/")
        self._user = user
        self._token = token
        self._org_name = org_name
        self._headers = {"Authorization": f"token {token}"}

    def _request(
        self,
        requests_func,
        endpoint,
        error_msg: Optional[str] = None,
        **kwargs,
    ):
        """Wrapper for using requests with the Gitea API.

        Args:
            requests_func: A requests function, e.g. :py:func:`requests.get`.
            endpoint: The endpoint to hit.
            error_msg: If provided, any response that is not 200 (OK) or 201
                (OK created) will result in a platform error with the provided
                message.
            kwargs: Keyword arguments to the requests function.
        Returns:
            The response.
        """
        url = f"{self._base_url}{endpoint}"

        data: Optional[str]
        if "data" in kwargs:
            data = json.dumps(kwargs["data"])
            headers = {"Content-Type": "application/json", **self._headers}
        else:
            data = None
            headers = self._headers

        authed_kwargs = dict(kwargs)
        authed_kwargs["data"] = data
        authed_kwargs["headers"] = headers
        authed_kwargs["verify"] = self._ssl_verify()

        plug.log.debug(
            f"Sending {requests_func.__name__} request to '{url}' "
            f"with kwargs {authed_kwargs}"
        )

        response = requests_func(url, **authed_kwargs)
        plug.log.debug(
            f"Received {response}: {response.content.decode('utf8')}"
        )

        if response.status_code not in [200, 201] and error_msg:
            raise plug.PlatformError(error_msg, response.status_code)

        return response

    @staticmethod
    def _ssl_verify():
        ssl_verify = not os.getenv("REPOBEE_NO_VERIFY_SSL") == "true"
        return ssl_verify

    def create_team(
        self,
        name: str,
        members: Optional[List[str]] = None,
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> plug.Team:
        """See :py:meth:`repobee_plug.PlatformAPI.create_team`."""
        team_data = dict(
            description=name,
            includes_all_repositories=False,
            name=name,
            permission=_TEAM_PERMISSION_MAPPING[permission],
            units=[
                "repo.code",
                "repo.issues",
                "repo.ext_issues",
                "repo.wiki",
                "repo.pulls",
                "repo.releases",
                "repo.ext_wiki",
            ],
        )
        endpoint = f"/orgs/{self._org_name}/teams"

        response = self._request(requests.post, endpoint, data=team_data)
        team_id = response.json()["id"]

        team = plug.Team(
            name=name,
            members=members or [],
            id=team_id,
            implementation=response.json(),
        )
        self.assign_members(team, members or [])
        return team

    def get_teams(
        self, team_names: Optional[Iterable[str]] = None
    ) -> Iterable[plug.Team]:
        """See :py:meth:`repobee_plug.PlatformAPI.get_teams`."""
        team_names = set(team_names or {})

        endpoint = f"/orgs/{self._org_name}/teams"
        response = self._request(requests.get, endpoint)
        for team_dict in response.json():
            team_name = team_dict["name"]
            if team_names and team_name not in team_names:
                continue

            members_endpoint = f"/teams/{team_dict['id']}/members"
            members = [
                d["login"]
                for d in self._request(requests.get, members_endpoint).json()
            ]
            yield plug.Team(
                name=team_name,
                members=members,
                id=team_dict["id"],
                implementation=team_dict,
            )

    def assign_members(
        self,
        team: plug.Team,
        members: Iterable[str],
        permission: plug.TeamPermission = plug.TeamPermission.PUSH,
    ) -> None:
        """See :py:meth:`repobee_plug.PlatformAPI.assign_members`."""
        for member in members:
            endpoint = f"/teams/{team.id}/members/{member}"
            self._request(requests.put, endpoint)

    def create_repo(
        self,
        name: str,
        description: str,
        private: bool,
        team: Optional[plug.Team] = None,
    ) -> plug.Repo:
        """See :py:meth:`repobee_plug.PlatformAPI.create_repo`."""
        endpoint = f"/orgs/{self._org_name}/repos"
        data = dict(
            name=name,
            description=description,
            auto_init=False,
            private=private,
            default_branch="master",
        )
        response = self._request(requests.post, endpoint, data=data)

        if response.status_code == 409:
            raise plug.PlatformError(
                f"repository {self._org_name}/{name} already exists",
                status=response.status_code,
            )

        resp_data = response.json()
        return plug.Repo(
            name=name,
            description=description,
            private=private,
            url=resp_data["clone_url"],
            implementation=resp_data,
        )

    def get_repo(self, repo_name: str, team_name: Optional[str]) -> plug.Repo:
        """See :py:meth:`repobee_plug.PlatformAPI.get_repo`."""
        endpoint = f"/repos/{self._org_name}/{repo_name}"
        response = self._request(
            requests.get,
            endpoint,
            error_msg=f"could not fetch repo {self._org_name}/{repo_name}",
        )
        return self._wrap_repo(response.json())

    def get_repos(
        self, repo_urls: Optional[List[str]] = None
    ) -> Iterable[plug.Repo]:
        """See :py:meth:`repobee_plug.PlatformAPI.get_repos`."""
        if repo_urls:
            return map(self._get_repo_by_url, repo_urls)

        endpoint = f"/orgs/{self._org_name}/repos"
        response = self._request(
            requests.get,
            endpoint,
            error_msg=f"could not fetch repos from {self._org_name}",
        )

        return (self._wrap_repo(repo_data) for repo_data in response.json())

    def _get_repo_by_url(self, url: str) -> plug.Repo:
        endpoint = f"/repos/{self._org_name}/{self.extract_repo_name(url)}"
        response = self._request(
            requests.get, endpoint, error_msg=f"failed to fetch repo at {url}"
        )
        return self._wrap_repo(response.json())

    def assign_repo(
        self, team: plug.Team, repo: plug.Repo, permission: plug.TeamPermission
    ) -> None:
        """See :py:meth:`repobee_plug.PlatformAPI.assign_repo`."""
        endpoint = f"/teams/{team.id}/repos/{self._org_name}/{repo.name}"
        self._request(requests.put, endpoint)

    def get_team_repos(self, team: plug.Team) -> Iterable[plug.Repo]:
        """See :py:meth:`repobee_plug.PlatformAPI.get_team_repos`."""
        endpoint = f"/teams/{team.id}/repos"
        response = self._request(
            requests.get,
            endpoint,
            error_msg=f"could not fetch repos for team {team.name}",
        )
        return (self._wrap_repo(repo_data) for repo_data in response.json())

    def _wrap_repo(self, repo_data: dict) -> plug.Repo:
        return plug.Repo(
            name=repo_data["name"],
            description=repo_data["description"],
            private=repo_data["private"],
            url=repo_data["clone_url"],
            implementation=repo_data,
        )

    def get_repo_urls(
        self,
        assignment_names: Iterable[str],
        org_name: Optional[str] = None,
        team_names: Optional[List[str]] = None,
        insert_auth: bool = False,
    ) -> List[str]:
        """See :py:meth:`repobee_plug.PlatformAPI.get_repo_urls`."""
        org_html_url = self._org_base_url(org_name or self._org_name)
        repo_names = (
            assignment_names
            if not team_names
            else plug.generate_repo_names(team_names, assignment_names)
        )
        return [
            self.insert_auth(url) if insert_auth else url
            for url in (
                f"{org_html_url}/{repo_name}.git"
                for repo_name in list(repo_names)
            )
        ]

    def insert_auth(self, url: str) -> str:
        """See :py:meth:`repobee_plug.PlatformAPI.insert_auth`."""
        scheme, netloc, *rest = urllib.parse.urlsplit(url)
        auth = f"{self._user}:{self._token}"
        authed_netloc = f"{auth}@{netloc}"
        return urllib.parse.urlunsplit((scheme, authed_netloc, *rest))

    def create_issue(
        self,
        title: str,
        body: str,
        repo: plug.Repo,
        assignees: Optional[Iterable[str]] = None,
    ) -> plug.Issue:
        """See :py:meth:`repobee_plug.PlatformAPI.create_issue`."""
        owner = repo.implementation["owner"]["login"]
        endpoint = f"/repos/{owner}/{repo.name}/issues"
        response = self._request(
            requests.post,
            endpoint,
            error_msg=f"could not open issue in {owner}/{repo.name}",
            data=dict(title=title, body=body),
        )
        return self._wrap_issue(response.json())

    def close_issue(self, issue: plug.Issue) -> None:
        """See :py:meth:`repobee_plug.PlatformAPI.close_issue`."""

    def get_repo_issues(self, repo: plug.Repo) -> Iterable[plug.Issue]:
        """See :py:meth:`repobee_plug.PlatformAPI.get_repo_issues`."""
        owner = repo.implementation["owner"]["login"]
        endpoint = f"/repos/{owner}/{repo.name}/issues"
        response = self._request(
            requests.get,
            endpoint,
            error_msg="could not fetch issues from {owner}/{repo.name}",
        )
        return (self._wrap_issue(issue_data) for issue_data in response.json())

    def _wrap_issue(self, issue_data: dict) -> plug.Issue:
        return plug.Issue(
            title=issue_data["title"],
            body=issue_data["body"],
            number=issue_data["number"],
            author=issue_data["user"]["login"],
            created_at=issue_data["created_at"],
            state=plug.IssueState(issue_data["state"]),
        )

    def _org_base_url(self, org_name) -> str:
        scheme, netloc, *_ = urllib.parse.urlsplit(self._base_url)
        return urllib.parse.urlunsplit((scheme, netloc, org_name, "", ""))

    def extract_repo_name(self, repo_url: str) -> str:
        """See :py:meth:`repobee_plug.PlatformAPI.extract_repo_name`."""
        repo_html_url = re.sub(r"\.git$", "", repo_url)
        return pathlib.Path(repo_html_url).stem


class GiteaAPIHook(plug.Plugin):
    def api_init_requires(self):
        return ("base_url", "user", "token", "org_name")

    def get_api_class(self):
        return GiteaAPI
