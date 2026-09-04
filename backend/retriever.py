import time
from backend.embeddings import GeminiEmbedder
from backend.vector_store import CodeVectorStore


class CodeRetriever:
    """
    Retrieve relevant code chunks from ChromaDB
    using Gemini query embeddings.
    """

    def __init__(
        self,
        repository_id: str,
        top_k: int = 5,
    ):
        # The empty string check has been removed to match ChromaDB metadata
        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        self.repository_id = repository_id
        self.top_k = top_k

        self.embedder = GeminiEmbedder()
        self.vector_store = CodeVectorStore()

    def retrieve(
        self,
        question: str,
    ) -> list[dict]:
        """
        Retrieve the most relevant code chunks
        for a user question.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        # -----------------------------------------------------
        # Exponential Backoff Retry for API Rate Limits
        # -----------------------------------------------------
        max_retries = 3
        query_embedding = None

        for attempt in range(max_retries):
            try:
                query_embedding = (
                    self.embedder.embed_query(
                        question
                    )
                )
                break  # Success, exit the retry loop
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        print(f"Rate limit hit. Retrying query embedding in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise RuntimeError(
                            f"Embedding rate limit exceeded after {max_retries} retries. Please wait a minute and try again."
                        )
                else:
                    raise e  # If it's a different error, raise it immediately

        # -----------------------------------------------------

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=self.top_k,
            repository_id=self.repository_id,
        )

        return self._format_results(
            results
        )

    @staticmethod
    def _format_results(
        results: dict,
    ) -> list[dict]:
        """
        Convert ChromaDB's nested response into
        clean retrieval results.
        """

        if not results:
            return []

        ids = results.get(
            "ids",
            [[]],
        )[0]

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        formatted_results = []

        for index, document in enumerate(
            documents
        ):
            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            chunk_id = (
                ids[index]
                if index < len(ids)
                else None
            )

            relevance_score = None

            if distance is not None:
                relevance_score = max(
                    0.0,
                    min(
                        1.0,
                        1.0 - distance,
                    ),
                )

            formatted_results.append(
                {
                    "id": chunk_id,
                    "content": document,
                    "metadata": metadata,
                    "distance": distance,
                    "relevance_score": relevance_score,
                    "source": {
                        "repository": metadata.get(
                            "repository_name"
                        ),
                        "file_path": metadata.get(
                            "file_path"
                        ),
                        "name": metadata.get(
                            "name"
                        ),
                        "type": metadata.get(
                            "type"
                        ),
                        "start_line": metadata.get(
                            "start_line"
                        ),
                        "end_line": metadata.get(
                            "end_line"
                        ),
                    },
                }
            )

        return formatted_results

    def build_context(
        self,
        results: list[dict],
    ) -> str:
        """
        Build an LLM-ready context string from
        retrieved code chunks.
        """

        if not results:
            return (
                "No relevant code was found "
                "in the repository."
            )

        context_parts = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            metadata = result["metadata"]

            file_path = metadata.get(
                "file_path",
                "unknown",
            )

            name = metadata.get(
                "name",
                "unknown",
            )

            node_type = metadata.get(
                "type",
                "unknown",
            )

            start_line = metadata.get(
                "start_line",
                "?",
            )

            end_line = metadata.get(
                "end_line",
                "?",
            )

            parent_class = metadata.get(
                "parent_class",
                "",
            )

            parent_function = metadata.get(
                "parent_function",
                "",
            )

            location = (
                f"{file_path}:"
                f"{start_line}-"
                f"{end_line}"
            )

            context_parts.append(
                f"[SOURCE {index}]\n"
                f"File: {file_path}\n"
                f"Location: {location}\n"
                f"Type: {node_type}\n"
                f"Name: {name}\n"
                f"Parent class: "
                f"{parent_class or 'None'}\n"
                f"Parent function: "
                f"{parent_function or 'None'}\n"
                f"Code:\n"
                f"```python\n"
                f"{result['content']}\n"
                f"```"
            )

        return "\n\n".join(
            context_parts
        )