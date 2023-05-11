# -*- coding: utf-8 -*-
"""
General-purpose functions for the API.
"""
import base64
from pathlib import Path
import string
from typing import List, Union

from django.conf import settings
from github import Github, InputGitTreeElement
from github.GithubException import GithubException
from github.Repository import Repository


def check_snake_case(name: str) -> bool:
    """
    Check if a string is in snake_case.
    """
    allowed_chars = set(string.ascii_lowercase + string.digits + "_")
    return set(name).issubset(allowed_chars) and name[0] != "_"


def check_kebab_case(name: str) -> bool:
    """
    Check if a string is in kebab-case.
    """
    allowed_chars = set(string.ascii_lowercase + string.digits + "-")
    return set(name).issubset(allowed_chars) and name[0] != "-"


def create_pull_request(
    repo: Repository,
    title: str,
    head: str,
    base: str,
    element_list: List[InputGitTreeElement],
    body: str = None,
    commit_message: str = None,
):
    """
    Create a new branch, commit to it and create a pull request.

    Args:
        title (str): Title of the pull request.
        head (str): Name of the branch where the changes will be implemented.
        base (str): Name of the branch you want the changes pulled into.
        element_list (List[InputGitTreeElement]): List of InputGitTreeElement objects.
        body (str, optional): Description of the pull request. Defaults to None.
        commit_message (str, optional): Commit message. Defaults to None.
    """
    # Create new branch. If it already exists, delete it and create a new one.
    try:
        print("Creating new branch...")
        repo.create_git_ref(
            f"refs/heads/{head}", repo.get_git_ref(f"heads/{base}").object.sha
        )
    except GithubException as exc:
        if exc.status == 422:
            print("Branch already exists. Deleting and creating a new one...")
            repo.get_git_ref(f"heads/{head}").delete()
            repo.create_git_ref(
                f"refs/heads/{head}", repo.get_git_ref(f"heads/{base}").object.sha
            )
        else:
            raise exc
    # Create new commit to the new branch.
    print("Creating new commit...")
    tree = repo.create_git_tree(element_list)
    parent = repo.get_git_commit(repo.get_git_ref(f"heads/{head}").object.sha)
    commit = repo.create_git_commit(commit_message, tree, [parent])
    # Update the reference of the new branch.
    print("Updating branch reference...")
    repo.get_git_ref(f"heads/{head}").edit(commit.sha)
    # Create a pull request.
    print("Creating pull request...")
    repo.create_pull(title=title, body=body, head=head, base=base)


def get_element_list(directory: Union[Path, str]) -> List[InputGitTreeElement]:
    """
    Create an element list for a directory.

    Args:
        directory (Union[Path, str]): Directory to create element list for.

    Returns:
        List[InputGitTreeElement]: List of InputGitTreeElement objects.
    """
    directory = Path(directory)
    all_files = [f for f in directory.glob("**/*") if f.is_file()]
    file_list = [str(f) for f in all_files]
    file_names = [f.name for f in all_files]
    element_list = list()
    for i, entry in enumerate(file_list):
        # Check if file is binary
        if is_binary(entry):
            with open(entry, "rb") as input_file:
                data = base64.b64encode(input_file.read())
        else:
            with open(entry, "r") as input_file:
                data = input_file.read()
        element = InputGitTreeElement(file_names[i], "100644", "blob", data)
        element_list.append(element)
    return element_list


def get_github_client() -> Github:
    """
    Get a Github client with the appropriate credentials.
    """
    return Github(settings.GITHUB_TOKEN)


def get_github_repo(repository_name: str, organization_name: str = None) -> Repository:
    """
    Get the Github repository where the data is stored.
    """
    client = get_github_client()
    if organization_name:
        return client.get_organization(organization_name).get_repo(repository_name)
    return client.get_user().get_repo(repository_name)


def is_binary(filename: str) -> bool:
    """
    Checks whether a file is binary or not.
    """
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    return bool(open(filename, "rb").read(1024).translate(None, textchars))
