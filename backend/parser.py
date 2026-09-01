import ast
from pathlib import Path


FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def parse_python_file(
    file_path: str,
    repo_path: str | None = None,
) -> list[dict]:
    """
    Parse a Python file using the Python AST.

    Functions and methods are returned as primary RAG chunks.
    Classes are recorded as structural metadata but are not returned
    as large embedding chunks.

    Args:
        file_path: Path to the Python source file.
        repo_path: Optional repository root used to create a relative path.

    Returns:
        List of structured code chunks.
    """

    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.suffix.lower() != ".py":
        raise ValueError(f"Expected a Python file, got: {path.suffix}")

    source_code = _read_source(path)

    try:
        tree = ast.parse(
            source_code,
            filename=str(path),
        )
    except SyntaxError as exc:
        print(f"Skipping file with syntax error: {path}")
        print(f"  {exc}")
        return []

    source_lines = source_code.splitlines()

    relative_path = _get_relative_path(
        path=path,
        repo_path=repo_path,
    )

    chunks = []

    for node in tree.body:
        _extract_nodes(
            node=node,
            source_lines=source_lines,
            relative_path=relative_path,
            chunks=chunks,
            parent_class=None,
            parent_function=None,
        )

    return chunks


def _extract_nodes(
    node: ast.AST,
    source_lines: list[str],
    relative_path: str,
    chunks: list[dict],
    parent_class: str | None,
    parent_function: str | None,
) -> None:
    """
    Recursively extract functions and methods from an AST node.
    """



    if isinstance(node, FUNCTION_NODES):
        node_type = "method" if parent_class else "function"

        chunk = _create_chunk(
            node=node,
            source_lines=source_lines,
            relative_path=relative_path,
            node_type=node_type,
            parent_class=parent_class,
            parent_function=parent_function,
        )

        chunks.append(chunk)

        # Continue recursively so nested functions are also captured.
        for child in node.body:
            _extract_nodes(
                node=child,
                source_lines=source_lines,
                relative_path=relative_path,
                chunks=chunks,
                parent_class=parent_class,
                parent_function=node.name,
            )

        return

    # Handle nested classes.
    if isinstance(node, ast.ClassDef):
        for child in node.body:
            _extract_nodes(
                node=child,
                source_lines=source_lines,
                relative_path=relative_path,
                chunks=chunks,
                parent_class=node.name,
                parent_function=parent_function,
            )


def _create_chunk(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
    relative_path: str,
    node_type: str,
    parent_class: str | None,
    parent_function: str | None,
) -> dict:
    """
    Convert a function/method AST node into a RAG chunk.
    """

    start_line = node.lineno
    end_line = getattr(node, "end_lineno", start_line)

    source = "\n".join(
        source_lines[start_line - 1:end_line]
    )

    return {
        "content": source,
        "metadata": {
            "file_name": Path(relative_path).name,
            "file_path": relative_path,
            "language": "python",
            "type": node_type,
            "name": node.name,
            "parent_class": parent_class,
            "parent_function": parent_function,
            "start_line": start_line,
            "end_line": end_line,
        },
    }


def _read_source(path: Path) -> str:
    """
    Read source code while handling common encoding problems.
    """

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )


def _get_relative_path(
    path: Path,
    repo_path: str | None,
) -> str:
    """
    Return a repository-relative file path when repo_path is supplied.
    """

    if repo_path is not None:
        repo = Path(repo_path).resolve()

        try:
            return path.resolve().relative_to(repo).as_posix()
        except ValueError:
            pass

    return path.name


if __name__ == "__main__":
    test_file = (
        r"C:\Users\Pawan S\AppData\Local\Temp"
        r"\github_code_chatter_400d0niu"
        r"\src\flask\app.py"
    )

    test_repo = (
        r"C:\Users\Pawan S\AppData\Local\Temp"
        r"\github_code_chatter_400d0niu"
    )

    try:
        chunks = parse_python_file(
            file_path=test_file,
            repo_path=test_repo,
        )

        print(f"Found {len(chunks)} code chunks:\n")

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]

            print(f"--- Chunk {index} ---")
            print(f"Type: {metadata['type']}")
            print(f"Name: {metadata['name']}")
            print(f"File: {metadata['file_path']}")
            print(
                f"Lines: "
                f"{metadata['start_line']}-"
                f"{metadata['end_line']}"
            )
            print(f"Parent class: {metadata['parent_class']}")
            print(
                f"Parent function: "
                f"{metadata['parent_function']}"
            )
            print("Code:")
            print(chunk["content"][:300])
            print()

    except Exception as exc:
        print(f"Error: {exc}")