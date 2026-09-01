import os
import hashlib
from pathlib import Path

import chromadb


DEFAULT_DB_PATH = "database/chroma_db"


class CodeVectorStore:
    """
    Persistent ChromaDB vector store for code chunks.
    """

    def __init__(
        self,
        persist_directory: str = DEFAULT_DB_PATH,
        collection_name: str = "code_chunks",
    ):
        self.persist_directory = Path(
            persist_directory
        )

        # Make sure the ChromaDB path is a directory.
        if self.persist_directory.exists():
            if not self.persist_directory.is_dir():
                raise ValueError(
                    f"ChromaDB path exists but is not a directory: "
                    f"{self.persist_directory}"
                )

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Initialize persistent ChromaDB.
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )

        # Create or load collection.
        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine"
                },
            )
        )

    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        repository_metadata: dict | None = None,
    ) -> None:
        """
        Add code chunks and embeddings to ChromaDB.

        Args:
            chunks:
                Parsed code chunks.

            embeddings:
                Gemini embeddings corresponding
                to each chunk.

            repository_metadata:
                Repository-level metadata generated
                by metadata.py.
        """

        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks must match "
                "number of embeddings."
            )

        ids = []
        documents = []
        metadatas = []

        repository_metadata = (
            repository_metadata or {}
        )

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):
            metadata = chunk["metadata"]

            chunk_id = (
                self._create_chunk_id(
                    metadata=metadata
                )
            )

            ids.append(chunk_id)
            documents.append(
                chunk["content"]
            )

            chunk_metadata = {
                # Repository metadata
                "repository_id": str(
                    repository_metadata.get(
                        "repository_id",
                        "",
                    )
                ),
                "repository_name": str(
                    repository_metadata.get(
                        "repository_name",
                        "",
                    )
                ),
                "repository_url": str(
                    repository_metadata.get(
                        "repository_url",
                        "",
                    )
                ),

                # Code metadata
                "file_name": str(
                    metadata["file_name"]
                ),
                "file_path": str(
                    metadata["file_path"]
                ),
                "language": str(
                    metadata["language"]
                ),
                "type": str(
                    metadata["type"]
                ),
                "name": str(
                    metadata["name"]
                ),
                "parent_class": str(
                    metadata["parent_class"]
                    or ""
                ),
                "parent_function": str(
                    metadata["parent_function"]
                    or ""
                ),
                "start_line": int(
                    metadata["start_line"]
                ),
                "end_line": int(
                    metadata["end_line"]
                ),
            }

            metadatas.append(
                chunk_metadata
            )

        # Upsert means existing IDs are updated
        # instead of duplicated.
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        repository_id: str | None = None,
    ) -> dict:
        """
        Search for the most relevant code chunks.

        Args:
            query_embedding:
                Gemini embedding of the user's question.

            top_k:
                Number of results to return.

            repository_id:
                Optional repository ID used to restrict
                retrieval to one repository.
        """

        if not query_embedding:
            raise ValueError(
                "Query embedding cannot be empty."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        query_kwargs = {
            "query_embeddings": [
                query_embedding
            ],
            "n_results": top_k,
        }

        # Restrict retrieval to the selected repository.
        if repository_id:
            query_kwargs["where"] = {
                "repository_id": repository_id
            }

        return self.collection.query(
            **query_kwargs
        )

    def count(self) -> int:
        """
        Return the number of stored code chunks.
        """

        return self.collection.count()

    def get_existing_chunk_ids(
        self,
        chunks: list[dict],
    ) -> set[str]:
        """
        Return IDs of chunks that already exist
        in ChromaDB.
        """

        if not chunks:
            return set()

        chunk_ids = [
            self._create_chunk_id(
                chunk["metadata"]
            )
            for chunk in chunks
        ]

        existing = self.collection.get(
            ids=chunk_ids
        )

        return set(
            existing["ids"]
        )

    def update_repository_metadata(
        self,
        repository_metadata: dict,
    ) -> int:
        """
        Update repository metadata for all existing
        ChromaDB records.

        This is primarily intended for migrating the
        existing database created before repository
        metadata was introduced.

        Returns:
            Number of records updated.
        """

        total = self.collection.count()

        if total == 0:
            return 0

        batch_size = 500
        updated = 0

        for offset in range(
            0,
            total,
            batch_size,
        ):
            result = self.collection.get(
                limit=batch_size,
                offset=offset,
                include=[
                    "metadatas"
                ],
            )

            ids = result["ids"]
            existing_metadatas = (
                result["metadatas"]
            )

            if not ids:
                continue

            new_metadatas = []

            for metadata in existing_metadatas:
                metadata = (
                    metadata or {}
                )

                metadata.update(
                    {
                        "repository_id": str(
                            repository_metadata[
                                "repository_id"
                            ]
                        ),
                        "repository_name": str(
                            repository_metadata[
                                "repository_name"
                            ]
                        ),
                        "repository_url": str(
                            repository_metadata[
                                "repository_url"
                            ]
                        ),
                    }
                )

                new_metadatas.append(
                    metadata
                )

            self.collection.update(
                ids=ids,
                metadatas=new_metadatas,
            )

            updated += len(ids)

        return updated

    def clear(self) -> None:
        """
        Delete all stored chunks from the collection.
        """

        collection_name = (
            self.collection.name
        )

        self.client.delete_collection(
            collection_name
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine"
                },
            )
        )

    @staticmethod
    def _create_chunk_id(
        metadata: dict,
    ) -> str:
        """
        Create a deterministic ID for a code chunk.

        The same file/location/name combination
        receives the same ID.
        """

        raw_id = (
            f"{metadata['file_path']}:"
            f"{metadata['start_line']}:"
            f"{metadata['end_line']}:"
            f"{metadata['name']}"
        )

        return hashlib.sha256(
            raw_id.encode("utf-8")
        ).hexdigest()


if __name__ == "__main__":

    store = CodeVectorStore()

    print(
        "ChromaDB initialized successfully."
    )

    print(
        f"Stored chunks: "
        f"{store.count()}"
    )

    print(
        "Database path: "
        f"{os.path.abspath(DEFAULT_DB_PATH)}"
    )