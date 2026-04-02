"""Document parsers for PDF, Markdown, and code files."""

import re
from pathlib import Path


def parse_pdf(path: str) -> str:
    """Extract plain text from a PDF file using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def parse_markdown(path: str) -> str:
    """Extract plain text from a Markdown file (strip syntax markers)."""
    text = Path(path).read_text(encoding="utf-8")
    # Remove code fences
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_code(path: str) -> str:
    """
    Parse a source code file by splitting on top-level function/class definitions.
    Returns the full file text; chunking at function/class boundaries is handled
    by the semantic chunker which will split on blank lines (paragraph breaks).
    """
    return Path(path).read_text(encoding="utf-8")


# Supported extensions → parser mapping
_PARSERS: dict[str, callable] = {
    ".pdf": parse_pdf,
    ".md": parse_markdown,
    ".markdown": parse_markdown,
    ".py": parse_code,
    ".ts": parse_code,
    ".js": parse_code,
    ".cpp": parse_code,
    ".c": parse_code,
    ".h": parse_code,
    ".hpp": parse_code,
    ".java": parse_code,
    ".go": parse_code,
    ".rs": parse_code,
    ".txt": parse_markdown,  # plain text — same light cleaning
}


def parse_document(path: str) -> tuple[str, str]:
    """
    Parse a document file and return (text, doc_type).

    Parameters
    ----------
    path : str
        Absolute or relative path to the document.

    Returns
    -------
    tuple[str, str]
        (extracted_text, document_type) where document_type is one of
        'pdf', 'markdown', 'code', 'text'.

    Raises
    ------
    ValueError
        If the file extension is not supported.
    """
    suffix = Path(path).suffix.lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {sorted(_PARSERS.keys())}"
        )

    text = parser(path)

    if suffix == ".pdf":
        doc_type = "pdf"
    elif suffix in {".md", ".markdown", ".txt"}:
        doc_type = "markdown"
    else:
        doc_type = "code"

    return text, doc_type
