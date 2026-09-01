import time
from pathlib import Path

from backend.clone_repo import clone_repo
from backend.file_loader import get_code_files
from backend.parser import parse_python_file
from backend.embeddings import GeminiEmbedder
from backend.vector_store import CodeVectorStore


DEFAULT_BATCH_SIZE = 50

# Stay below the observed free-tier limit of 100
# embedding requests per minute.
SAFE_REQUESTS_PER_MINUTE = 90

RATE_LIMIT_WINDOW = 60


def ingest_repository(
    repo_url: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Clone and index a GitHub repository.

    Currently supports Python files.

    The ingestion process is resumable:
    chunks already present in ChromaDB are skipped.
    """

    print("=" * 60)
    print("GitHub Code Chatter - Repository Ingestion")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Clone repository
    # ---------------------------------------------------------

    print("\n[1/4] Cloning repository...")

    repo_path = clone_repo(
        repo_url
    )

    print(
        f"Repository path: {repo_path}"
    )

    # ---------------------------------------------------------
    # 2. Find source files
    # ---------------------------------------------------------

    print("\n[2/4] Scanning repository...")

    code_files = get_code_files(
        repo_path
    )

    print(
        f"Found {len(code_files)} "
        f"supported source files."
    )

    if not code_files:
        raise ValueError(
            "No supported source-code files "
            "were found."
        )

    # ---------------------------------------------------------
    # 3. Parse source files
    # ---------------------------------------------------------

    print("\n[3/4] Parsing source files...")

    all_chunks = []

    python_files = 0
    failed_files = 0

    for index, file_path in enumerate(
        code_files,
        start=1,
    ):

        path = Path(file_path)

        if path.suffix.lower() != ".py":
            continue

        python_files += 1

        try:
            chunks = parse_python_file(
                file_path=file_path,
                repo_path=repo_path,
            )

            all_chunks.extend(
                chunks
            )

        except Exception as exc:
            failed_files += 1

            print(
                f"Warning: failed to parse "
                f"{path}: {exc}"
            )

        if index % 10 == 0:
            print(
                f"Processed "
                f"{index}/{len(code_files)} "
                f"files..."
            )

    print(
        f"Python files parsed: "
        f"{python_files}"
    )

    print(
        f"Code chunks extracted: "
        f"{len(all_chunks)}"
    )

    if not all_chunks:
        raise ValueError(
            "No code chunks were extracted "
            "from the repository."
        )

    # ---------------------------------------------------------
    # 4. Embeddings + ChromaDB
    # ---------------------------------------------------------

    print(
        "\n[4/4] Preparing vector database..."
    )

    embedder = GeminiEmbedder()
    vector_store = CodeVectorStore()

    # ---------------------------------------------------------
    # Find chunks already indexed
    # ---------------------------------------------------------

    existing_ids = (
        vector_store.get_existing_chunk_ids(
            all_chunks
        )
    )

    remaining_chunks = [
        chunk
        for chunk in all_chunks
        if vector_store._create_chunk_id(
            chunk["metadata"]
        )
        not in existing_ids
    ]

    print(
        f"Already indexed: "
        f"{len(existing_ids)} chunks"
    )

    print(
        f"Remaining: "
        f"{len(remaining_chunks)} chunks"
    )

    if not remaining_chunks:
        print(
            "\nRepository is already fully indexed."
        )

        return {
            "repo_path": repo_path,
            "files_found": len(code_files),
            "python_files": python_files,
            "failed_files": failed_files,
            "chunks": len(all_chunks),
            "embeddings": 0,
            "stored_chunks": vector_store.count(),
        }

    # ---------------------------------------------------------
    # Rate-limited embedding
    # ---------------------------------------------------------

    print(
        "\nGenerating Gemini embeddings..."
    )

    total_embedded = 0

    window_start = time.monotonic()
    requests_in_window = 0

    for start in range(
        0,
        len(remaining_chunks),
        batch_size,
    ):

        batch = remaining_chunks[
            start:start + batch_size
        ]

        batch_size_actual = len(batch)

        # -----------------------------------------------------
        # Rate limiter
        # -----------------------------------------------------

        elapsed = (
            time.monotonic()
            - window_start
        )

        if (
            elapsed >= RATE_LIMIT_WINDOW
        ):
            window_start = time.monotonic()
            requests_in_window = 0

        if (
            requests_in_window
            + batch_size_actual
            > SAFE_REQUESTS_PER_MINUTE
        ):

            wait_time = (
                RATE_LIMIT_WINDOW
                - elapsed
                + 2
            )

            print(
                "\nRate-limit protection:"
            )

            print(
                f"Waiting "
                f"{wait_time:.1f} seconds..."
            )

            time.sleep(
                max(wait_time, 0)
            )

            window_start = time.monotonic()
            requests_in_window = 0

        # -----------------------------------------------------
        # Generate embeddings
        # -----------------------------------------------------

        texts = [
            chunk["content"]
            for chunk in batch
        ]

        embeddings = (
            embedder.embed_texts(
                texts
            )
        )

        requests_in_window += (
            batch_size_actual
        )

        # -----------------------------------------------------
        # Store immediately
        # -----------------------------------------------------

        vector_store.add_chunks(
            chunks=batch,
            embeddings=embeddings,
        )

        total_embedded += (
            len(embeddings)
        )

        print(
            f"Embedded and stored "
            f"{total_embedded}/"
            f"{len(remaining_chunks)} "
            f"remaining chunks..."
        )

    # ---------------------------------------------------------
    # Final statistics
    # ---------------------------------------------------------

    stored_chunks = (
        vector_store.count()
    )

    print(
        "\n" + "=" * 60
    )
    print(
        "Repository indexing complete"
    )
    print(
        "=" * 60
    )

    print(
        f"Source files found : "
        f"{len(code_files)}"
    )

    print(
        f"Python files       : "
        f"{python_files}"
    )

    print(
        f"Failed files       : "
        f"{failed_files}"
    )

    print(
        f"Total code chunks  : "
        f"{len(all_chunks)}"
    )

    print(
        f"New embeddings     : "
        f"{total_embedded}"
    )

    print(
        f"Chunks in ChromaDB : "
        f"{stored_chunks}"
    )

    print(
        "=" * 60
    )

    return {
        "repo_path": repo_path,
        "files_found": len(code_files),
        "python_files": python_files,
        "failed_files": failed_files,
        "chunks": len(all_chunks),
        "embeddings": total_embedded,
        "stored_chunks": stored_chunks,
    }


if __name__ == "__main__":

    TEST_REPO_URL = (
        "https://github.com/pallets/flask.git"
    )

    try:

        result = ingest_repository(
            repo_url=TEST_REPO_URL,
            batch_size=50,
        )

        print("\nResult:")
        print(result)

    except Exception as exc:

        print(
            f"\nIngestion failed: {exc}"
        )