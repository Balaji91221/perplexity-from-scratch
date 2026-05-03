"""PDF parsing + paragraph-aware chunking with page tracking."""

import io
import re

from pypdf import PdfReader

from config import CHUNK_OVERLAP_CHARS, CHUNK_TARGET_CHARS


def extract_pdf_text(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Returns [(page_number, text)] for each non-empty page."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    out: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        if t:
            out.append((i + 1, t))
    return out


def chunk_pages(
    pages: list[tuple[int, str]],
    target: int = CHUNK_TARGET_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[dict]:
    """Split pages into ~target-char chunks (paragraph-aware), keeping page numbers."""
    chunks: list[dict] = []
    for page_num, text in pages:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = ""
        for p in paragraphs:
            if len(p) > target * 2:
                # Hard split very long paragraphs by sentences.
                pieces = re.split(r"(?<=[.!?])\s+", p)
                for piece in pieces:
                    if len(current) + len(piece) + 1 > target and current:
                        chunks.append({"page": page_num, "content": current.strip()})
                        current = (current[-overlap:] + " " if overlap else "") + piece
                    else:
                        current = (current + " " + piece) if current else piece
                continue
            if len(current) + len(p) + 2 > target and current:
                chunks.append({"page": page_num, "content": current.strip()})
                tail = current[-overlap:] if overlap else ""
                current = (tail + "\n\n" + p) if tail else p
            else:
                current = (current + "\n\n" + p) if current else p
        if current.strip():
            chunks.append({"page": page_num, "content": current.strip()})
    return chunks
