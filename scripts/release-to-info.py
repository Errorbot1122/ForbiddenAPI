import subprocess
import argparse
import sys
import re

import requests


def extract_repo_path(repo: str) -> str:
    # Regex to capture owner and repo name
    match = re.search(r"(?:github\.com[:/])?([^/:\s]+?)/([^/:\s]+?)(?:\.git)?$", repo)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def parse_release(release_data) -> str:
    ## FORMATTING CODE GOES HERE ##
    no_headings = re.sub(r"#+\s+", "", release_data["body"])
    use_arrow_bullets = re.sub(r"\- ", "> ", no_headings)
    tab_body = "\n".join(["\t" + line for line in use_arrow_bullets.splitlines()])

    # MANDATORY FOR SED COMMAND
    final = f"""UPDATE {release["name"]}

    {tab_body}"""
    return "\n".join([line + "\\" for line in final.splitlines()])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="release-to-info.py",
        description="Converts github release into a simple text file",
    )
    parser.add_argument("tag", metavar="RELEASE_TAG")
    parser.add_argument("-r", "--repo", metavar="REPO_URL")
    parser.add_argument("-t", "--token", metavar="GITHUB_TOKEN")

    args = parser.parse_args()

    # Set defaults
    tag = args.tag

    token = args.token
    repo = args.repo
    if repo is None:
        repo_process = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
        )

        repo = repo_process.stdout
    repo = extract_repo_path(repo)

    # Get release data
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token is not None:
        headers["Authorization"] = "Bearer " + token

    release_response = requests.get(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}", headers=headers
    )

    status_code = release_response.status_code
    if status_code == 404:
        raise requests.HTTPError(
            f"Could not find release for tag '{tag}' on repository '{repo}'! "
            + f"Status code: {status_code}"
        )
    elif status_code == 401:
        raise requests.HTTPError(
            "Invalid or unauthorized token! Repo may be private, "
            + "if so please input a token with `repo_read` in in the --token flag "
            + f"Status code: {status_code}"
        )
    elif not release_response.ok:
        requests.HTTPError(release_response.reason + f" Status code: {status_code}")

    release = release_response.json()

    # Format release
    sys.stdout.write(parse_release(release))
