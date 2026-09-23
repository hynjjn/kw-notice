"""PDF 텍스트 추출."""

from __future__ import annotations

import pymupdf


def extract(path: str) -> str:
    with pymupdf.open(path) as doc:
        pages = [page.get_text("text") for page in doc]
    text = "\n".join(pages)
    return "\n".join(ln.strip() for ln in text.split("\n") if ln.strip())
