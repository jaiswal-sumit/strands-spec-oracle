"""
Markdown spec file chunker.

Splits .md files into semantically meaningful chunks (by heading sections)
so Decider 2B can score each chunk independently for relevance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpecChunk:
    """A single chunk from a spec file."""
    file: str          # relative path of the source file
    heading: str       # section heading (or filename if no headings)
    text: str          # full text of the chunk including heading
    token_estimate: int  # rough token count (chars / 4)

    def __str__(self) -> str:
        return f"[{self.file} › {self.heading}]\n{self.text}"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def chunk_file(path: Path, root: Path) -> list[SpecChunk]:
    """
    Split a markdown file into heading-level chunks.

    Each H1/H2/H3 section becomes its own chunk. If a file has no headings
    the whole file is one chunk.
    """
    relative = str(path.relative_to(root))
    raw = path.read_text(encoding="utf-8", errors="replace")

    # Split on H1 / H2 / H3 headings
    pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    parts = pattern.split(raw)

    chunks: list[SpecChunk] = []

    if len(parts) == 1:
        # No headings — whole file is one chunk
        text = raw.strip()
        if text:
            chunks.append(SpecChunk(
                file=relative,
                heading=path.stem,
                text=text,
                token_estimate=_estimate_tokens(text),
            ))
        return chunks

    # parts = [pre-heading text, heading1, body1, heading2, body2, ...]
    i = 0
    # Skip any preamble before the first heading
    i = 1  # first element is text before any heading — often empty
    while i + 1 < len(parts):
        heading_line = parts[i].strip()
        # Remove markdown # prefix for display
        heading_text = re.sub(r"^#+\s*", "", heading_line)
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        text = f"{heading_line}\n\n{body}" if body else heading_line
        if text.strip():
            chunks.append(SpecChunk(
                file=relative,
                heading=heading_text,
                text=text,
                token_estimate=_estimate_tokens(text),
            ))
        i += 2

    return chunks


def load_spec_directory(spec_dir: str | Path) -> list[SpecChunk]:
    """
    Recursively load all .md files from a directory and return all chunks.

    Returns chunks sorted by file path then heading order.
    """
    root = Path(spec_dir).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Spec directory not found: {root}")

    all_chunks: list[SpecChunk] = []
    for md_file in sorted(root.rglob("*.md")):
        all_chunks.extend(chunk_file(md_file, root))

    return all_chunks


def total_tokens(chunks: list[SpecChunk]) -> int:
    return sum(c.token_estimate for c in chunks)
