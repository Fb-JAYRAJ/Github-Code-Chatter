
import os
import shutil
import tempfile
from urllib.parse import urlparse

from git import Repo, GitCommandError


def clone_repo(repo_url: str) -> str:
    """
    Clone a GitHub repository into a temporary directory.

    Args:
        repo_url: Public GitHub repository URL.

    Returns:
        Absolute path to the cloned repository.

    Raises:
        ValueError: If the URL is invalid or not a GitHub URL.
        RuntimeError: If cloning fails.
    """

    # Validate URL
    parsed_url = urlparse(repo_url)

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError("Repository URL must start with http:// or https://")

    if parsed_url.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("Only GitHub repository URLs are supported.")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="github_code_chatter_")

    try:
        print(f"Cloning repository: {repo_url}")
        print(f"Destination: {temp_dir}")

        Repo.clone_from(repo_url, temp_dir)

        print("Repository cloned successfully.")

        return os.path.abspath(temp_dir)

    except GitCommandError as e:
        # Remove incomplete clone if cloning fails
        shutil.rmtree(temp_dir, ignore_errors=True)

        raise RuntimeError(
            f"Failed to clone repository.\nGit error: {e}"
        ) from e


if __name__ == "__main__":
    test_url = "https://github.com/octocat/Hello-World.git"

    try:
        path = clone_repo(test_url)

        print("\nRepository location:")
        print(path)

        print("\nFiles:")
        for item in os.listdir(path):
            print(item)

    except Exception as e:
        print(f"\nError: {e}")