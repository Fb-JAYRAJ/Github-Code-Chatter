import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


class GeminiEmbedder:
    """
    Generate embeddings using Google's Gemini Embedding model.
    """

    def __init__(
        self,
        model: str = "gemini-embedding-001",
    ):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in the environment."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = model

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for a single document.
        """

        if not text or not text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
            ),
        )

        return result.embeddings[0].values

    def embed_texts(
        self,
        texts: list[str],
        max_retries: int = 3,
        retry_delay: int = 65,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.

        Automatically retries Gemini 429 quota errors.
        """

        if not texts:
            return []

        if any(
            not text or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Embedding input contains empty text."
            )

        for attempt in range(max_retries + 1):
            try:
                result = self.client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                    ),
                )

                return [
                    embedding.values
                    for embedding in result.embeddings
                ]

            except Exception as exc:

                error_message = str(exc)

                is_quota_error = (
                    "429" in error_message
                    or "RESOURCE_EXHAUSTED"
                    in error_message
                )

                if not is_quota_error:
                    raise

                if attempt >= max_retries:
                    raise RuntimeError(
                        "Gemini embedding quota remained "
                        "exhausted after multiple retries."
                    ) from exc

                print(
                    "\nGemini embedding quota reached."
                )
                print(
                    f"Waiting {retry_delay} seconds "
                    f"before retry "
                    f"({attempt + 1}/{max_retries})..."
                )

                time.sleep(retry_delay)

        raise RuntimeError(
            "Embedding generation failed."
        )

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """
        Generate an embedding for a user query.

        Uses the code-retrieval query task type.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        result = self.client.models.embed_content(
            model=self.model,
            contents=query,
            config=types.EmbedContentConfig(
                task_type="CODE_RETRIEVAL_QUERY",
            ),
        )

        return result.embeddings[0].values


if __name__ == "__main__":

    embedder = GeminiEmbedder()

    test_text = """
    def authenticate_user(username, password):
        return verify_credentials(username, password)
    """

    vector = embedder.embed_text(
        test_text
    )

    print(
        "Embedding generated successfully."
    )
    print(
        f"Dimensions: {len(vector)}"
    )
    print(
        f"First 5 values: {vector[:5]}"
    )

    query_vector = embedder.embed_query(
        "How does authentication work?"
    )

    print(
        "\nQuery embedding generated successfully."
    )
    print(
        f"Query dimensions: "
        f"{len(query_vector)}"
    )