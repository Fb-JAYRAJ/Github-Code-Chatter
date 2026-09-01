import os

from dotenv import load_dotenv
from google import genai

from backend.retriever import CodeRetriever


load_dotenv()


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for
    GitHub repository code.
    """

    def __init__(
        self,
        repository_id: str,
        top_k: int = 5,
        model: str = "gemini-3.7-flash",
    ):
        """
        Initialize the RAG pipeline.

        Args:
            repository_id:
                ID of the repository to search.

            top_k:
                Number of code chunks to retrieve.

            model:
                Gemini generation model.
        """

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = model

        self.retriever = CodeRetriever(
            repository_id=repository_id,
            top_k=top_k,
        )

    def ask(
        self,
        question: str,
    ) -> dict:
        """
        Ask a question about the repository.

        Returns:
            Dictionary containing:
            - answer
            - sources
            - retrieved_chunks
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        # -----------------------------------------------------
        # 1. Retrieve relevant code
        # -----------------------------------------------------

        results = self.retriever.retrieve(
            question
        )

        # -----------------------------------------------------
        # 2. Handle no results
        # -----------------------------------------------------

        if not results:
            return {
                "answer": (
                    "I couldn't find relevant code "
                    "in the repository to answer "
                    "that question."
                ),
                "sources": [],
                "retrieved_chunks": [],
            }

        # -----------------------------------------------------
        # 3. Build LLM context
        # -----------------------------------------------------

        context = (
            self.retriever.build_context(
                results
            )
        )

        # -----------------------------------------------------
        # 4. Build grounded prompt
        # -----------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            context=context,
        )

        # -----------------------------------------------------
        # 5. Generate answer
        # -----------------------------------------------------

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        )

        answer = (
            response.text
            if response.text
            else (
                "The model did not return "
                "an answer."
            )
        )

        # -----------------------------------------------------
        # 6. Extract source information
        # -----------------------------------------------------

        sources = self._extract_sources(
            results
        )

        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": results,
        }

    @staticmethod
    def _build_prompt(
        question: str,
        context: str,
    ) -> str:
        """
        Build the grounded RAG prompt.
        """

        return f"""
You are GitHub Code Chatter, an AI assistant
that answers questions about a software repository.

Your job is to answer the user's question using
ONLY the repository code provided in the CONTEXT.

STRICT RULES:

1. Use the provided repository context as your
   primary and authoritative source.

2. Do NOT invent functions, classes, files,
   variables, behavior, or implementation details
   that are not supported by the context.

3. If the context does not contain enough
   information to answer the question, explicitly
   say that the available repository context is
   insufficient.

4. Do not pretend that a test, example, or comment
   is the actual implementation.

5. When explaining implementation behavior,
   prioritize actual source-code implementation
   over tests.

6. Cite relevant source files using their exact
   file paths.

7. When line numbers are available, include them
   in the citation.

8. If multiple files contribute to the answer,
   cite each relevant file.

9. Keep the explanation technically accurate
   and concise.

10. You may use normal programming knowledge to
    explain what the retrieved code is doing, but
    do not introduce repository-specific facts
    that are not supported by the provided context.

RESPONSE FORMAT:

Give a clear explanation first.

Then provide a "Sources" section containing
the relevant repository files.

Example:

The request is handled by ...

The main logic is ...

Sources:
- src/example.py:10-35
- src/handler.py:80-120

--------------------------------------------------
CONTEXT
--------------------------------------------------

{context}

--------------------------------------------------
USER QUESTION
--------------------------------------------------

{question}
"""

    @staticmethod
    def _extract_sources(
        results: list[dict],
    ) -> list[dict]:
        """
        Extract clean source information from
        retrieval results.
        """

        sources = []

        seen = set()

        for result in results:

            source = result.get(
                "source",
                {},
            )

            file_path = source.get(
                "file_path"
            )

            if not file_path:
                continue

            start_line = source.get(
                "start_line"
            )

            end_line = source.get(
                "end_line"
            )

            source_key = (
                file_path,
                start_line,
                end_line,
            )

            if source_key in seen:
                continue

            seen.add(
                source_key
            )

            sources.append(
                {
                    "file_path": file_path,
                    "name": source.get(
                        "name"
                    ),
                    "type": source.get(
                        "type"
                    ),
                    "start_line": start_line,
                    "end_line": end_line,
                    "repository": source.get(
                        "repository"
                    ),
                }
            )

        return sources


if __name__ == "__main__":

    TEST_REPOSITORY_ID = (
        "bb69cc12b4b06266"
    )

    pipeline = RAGPipeline(
        repository_id=TEST_REPOSITORY_ID,
        top_k=5,
    )

    question = "Where is Flask's HTTP exception handling implemented?"

    print(
        "\nGenerating answer..."
    )

    result = pipeline.ask(
        question
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "ANSWER"
    )

    print(
        "=" * 60
    )

    print(
        result["answer"]
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "SOURCES"
    )

    print(
        "=" * 60
    )

    for source in result["sources"]:

        print(
            f"{source['file_path']}:"
            f"{source['start_line']}-"
            f"{source['end_line']}"
        )