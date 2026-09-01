import hashlib
from urllib.parse import urlparse


def normalize_repo_url(repo_url: str) -> str:
    """
    Normalize a GitHub repository URL.

    Examples:

        https://github.com/user/project
        https://github.com/user/project.git

    become:

        https://github.com/user/project
    """

    repo_url = repo_url.strip()

    if repo_url.endswith("/"):
        repo_url = repo_url[:-1]

    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]

    return repo_url


def get_repository_name(repo_url: str) -> str:
    """
    Extract the repository name from a GitHub URL.
    """

    normalized_url = normalize_repo_url(
        repo_url
    )

    parsed = urlparse(
        normalized_url
    )

    repository_name = (
        parsed.path
        .strip("/")
        .split("/")[-1]
    )

    if not repository_name:
        raise ValueError(
            f"Could not determine repository name "
            f"from URL: {repo_url}"
        )

    return repository_name


def get_repository_id(repo_url: str) -> str:
    """
    Generate a stable identifier for a GitHub repository.

    The same repository URL always produces
    the same repository ID.
    """

    normalized_url = normalize_repo_url(
        repo_url
    )

    return hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()[:16]


def get_repository_metadata(
    repo_url: str,
) -> dict:
    """
    Generate standardized repository metadata.
    """

    normalized_url = normalize_repo_url(
        repo_url
    )

    return {
        "repository_url": normalized_url,
        "repository_name": get_repository_name(
            normalized_url
        ),
        "repository_id": get_repository_id(
            normalized_url
        ),
    }


if __name__ == "__main__":

    test_url = (
        "https://github.com/pallets/flask.git"
    )

    metadata = get_repository_metadata(
        test_url
    )

    print("Repository metadata:")
    print(
        f"URL: "
        f"{metadata['repository_url']}"
    )
    print(
        f"Name: "
        f"{metadata['repository_name']}"
    )
    print(
        f"ID: "
        f"{metadata['repository_id']}"
    )