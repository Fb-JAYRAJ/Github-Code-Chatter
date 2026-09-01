from backend.metadata import (
    get_repository_metadata,
)

from backend.vector_store import (
    CodeVectorStore,
)


REPOSITORY_URL = (
    "https://github.com/pallets/flask.git"
)


def main():

    repository_metadata = (
        get_repository_metadata(
            REPOSITORY_URL
        )
    )

    store = CodeVectorStore()

    print(
        "Repository:"
    )

    print(
        repository_metadata
    )

    print(
        f"\nExisting ChromaDB chunks: "
        f"{store.count()}"
    )

    updated = (
        store.update_repository_metadata(
            repository_metadata
        )
    )

    print(
        f"Updated metadata for "
        f"{updated} chunks."
    )

    print(
        f"ChromaDB chunks now: "
        f"{store.count()}"
    )


if __name__ == "__main__":
    main()