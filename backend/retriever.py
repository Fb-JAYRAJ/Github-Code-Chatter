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
        if not repository_id:
            raise ValueError(
                "repository_id cannot be empty."
            )

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

        query_embedding = (
            self.embedder.embed_query(
                question
            )
        )

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

            # Convert cosine distance into a
            # simple relevance score.
            #
            # Lower cosine distance means
            # higher similarity.
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


if __name__ == "__main__":

    TEST_REPOSITORY_ID = (
        "bb69cc12b4b06266"
    )

    retriever = CodeRetriever(
        repository_id=TEST_REPOSITORY_ID,
        top_k=5,
    )

    question = (
        "How does Flask handle HTTP exceptions?"
    )

    print(
        "\nSearching repository..."
    )

    results = retriever.retrieve(
        question
    )

    print(
        f"\nRetrieved {len(results)} chunks.\n"
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        source = result["source"]

        print(
            f"--- Result {index} ---"
        )

        print(
            f"File: "
            f"{source['file_path']}"
        )

        print(
            f"Name: "
            f"{source['name']}"
        )

        print(
            f"Lines: "
            f"{source['start_line']}-"
            f"{source['end_line']}"
        )

        print(
            f"Distance: "
            f"{result['distance']}"
        )

        print(
            f"Relevance: "
            f"{result['relevance_score']:.4f}"
        )

        print()

    print(
        "\n" + "=" * 60
    )

    print(
        "LLM CONTEXT"
    )

    print(
        "=" * 60
    )

    print(
        retriever.build_context(
            results
        )
    )