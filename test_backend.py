from backend.clone_repo import clone_repo
from backend.file_loader import get_code_files


REPO_URL = "https://github.com/pallets/flask.git"


def main():
    repo_path = clone_repo(REPO_URL)

    print("\nScanning repository...")

    code_files = get_code_files(repo_path)

    print(f"\nFound {len(code_files)} code files:\n")

    for file_path in code_files[:20]:
        print(file_path)

    if len(code_files) > 20:
        print(f"\n... and {len(code_files) - 20} more files.")


if __name__ == "__main__":
    main()