import pathlib
import json
import github

gh = github.Github(base_url="https://api.github.com")


plugins = {}
for repo_name in [
    "repobee-junit4",
    "repobee-feedback",
    "repobee-csvgrades",
    "repobee-sanitizer",
]:
    repo = gh.get_repo(f"repobee/{repo_name}")
    description = repo.description
    url = repo.html_url
    versions = {release.tag_name: {} for release in repo.get_releases()}

    plugins[repo_name[len("repobee-") :]] = dict(
        description=description, url=url, versions=versions
    )


pathlib.Path("plugins.json").write_text(json.dumps(plugins, indent=4))
