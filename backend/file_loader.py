import os
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".go",
    ".rs",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}


def get_code_files(repo_path: str) -> list[str]:
    """
    Recursively find supported source-code files in a repository.

    Args:
        repo_path: Path to the cloned repository.

    Returns:
        List of absolute paths to supported source-code files.

    Raises:
        ValueError: If the repository path does not exist.
    """

    repo = Path(repo_path)

    if not repo.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    if not repo.is_dir():
        raise ValueError(f"Repository path is not a directory: {repo_path}")

    code_files = []

    for root, directories, files in os.walk(repo):
        # Prevent os.walk from entering ignored directories
        directories[:] = [
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        ]

        for filename in files:
            file_path = Path(root) / filename

            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                code_files.append(str(file_path.resolve()))

    return sorted(code_files)


if __name__ == "__main__":
    test_repo = r"C:\Users\PAWANS~1\AppData\Local\Temp\github_code_chatter_ei1wvti_"

    try:
        files = get_code_files(test_repo)

        print(f"Found {len(files)} code files:\n")

        for file in files:
            print(file)

    except Exception as e:
        print(f"Error: {e}")