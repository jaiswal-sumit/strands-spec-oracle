"""
Strands Decider 2B HTTP client.

Calls the running strands-decider server to score spec chunks for relevance.

Start the server before using this module:
    strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000

Reusable decision pattern (Context & Memory):
    Question type : score
    State         : "Question: {user_question}\\n\\nSpec chunk:\\n{chunk_text}"
    Question      : "How relevant is this spec chunk to answering the question above?
                     0 = completely irrelevant, 1 = directly answers it"
    Scale         : irrelevant → relevant
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

from .chunker import SpecChunk

# ── Config ────────────────────────────────────────────────────────────────────

DECIDER_URL = os.environ.get("DECIDER_SERVER_URL", "http://localhost:8000")
RELEVANCE_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.55"))
MAX_CONTEXT_CHUNKS = int(os.environ.get("MAX_CONTEXT_CHUNKS", "6"))

# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class ScoredChunk:
    chunk: SpecChunk
    relevance: float      # 0.0 – 1.0 from Decider 2B
    confidence: float     # calibrated confidence from Decider 2B
    latency_ms: float


@dataclass
class FilterResult:
    """Everything the agent needs to know about the filtering decision."""
    question: str
    total_chunks: int
    scored_chunks: list[ScoredChunk]   # all chunks with scores
    selected_chunks: list[ScoredChunk] # chunks that passed the threshold
    threshold: float
    total_tokens_available: int
    tokens_used: int
    tokens_saved: int
    total_decider_latency_ms: float

    @property
    def reduction_pct(self) -> float:
        if self.total_tokens_available == 0:
            return 0.0
        return 100.0 * self.tokens_saved / self.total_tokens_available


# ── Core scoring function ─────────────────────────────────────────────────────

def _score_chunk(question: str, chunk: SpecChunk, session: requests.Session) -> ScoredChunk:
    """
    Ask Decider 2B: how relevant is this chunk to the question?

    Uses a 'score' question with a 3-point rubric so the model has
    a clear semantic anchor at each end of the scale.
    """
    state = (
        f"Developer question: {question}\n\n"
        f"Spec file: {chunk.file}\n"
        f"Section: {chunk.heading}\n\n"
        f"{chunk.text}"
    )

    payload = {
        "state": state,
        "questions": {
            "relevance": {
                "type": "score",
                "instructions": (
                    "How relevant is this spec section to answering the developer question above?"
                ),
                # criteria is required: ordered list, index 0 = low end, last = high end
                "criteria": [
                    "Completely irrelevant — different domain or topic",
                    "Somewhat related — background context but not a direct answer",
                    "Directly answers or closely supports the question",
                ],
            }
        },
    }

    t0 = time.perf_counter()
    resp = session.post(f"{DECIDER_URL}/v1/systemone", json=payload, timeout=10)
    resp.raise_for_status()
    latency_ms = (time.perf_counter() - t0) * 1000

    data = resp.json()
    answer = data["answers"]["relevance"]

    # score is 0-2; normalise to 0-1
    raw_score: float = answer.get("score", 0.0)
    normalised = raw_score / 2.0
    confidence: float = answer.get("confidence", 0.0)

    return ScoredChunk(
        chunk=chunk,
        relevance=normalised,
        confidence=confidence,
        latency_ms=latency_ms,
    )


def score_and_filter(
    question: str,
    chunks: list[SpecChunk],
    threshold: float = RELEVANCE_THRESHOLD,
    max_chunks: int = MAX_CONTEXT_CHUNKS,
) -> FilterResult:
    """
    Score every chunk with Decider 2B, then keep only the most relevant ones.

    This is the core reusable decision pattern:
      - Each chunk is scored independently (all reads share the same server process)
      - Results are sorted by relevance descending
      - Only chunks above `threshold` AND within `max_chunks` are returned
    """
    from .chunker import total_tokens

    total_tok = total_tokens(chunks)
    scored: list[ScoredChunk] = []
    total_latency = 0.0

    workers = int(os.environ.get("DECIDER_WORKERS", "8"))

    def _score(chunk: SpecChunk) -> ScoredChunk:
        with requests.Session() as s:
            return _score_chunk(question, chunk, s)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_score, chunk): chunk for chunk in chunks}
        for future in as_completed(futures):
            sc = future.result()
            scored.append(sc)
            total_latency += sc.latency_ms

    # Sort by relevance descending
    scored.sort(key=lambda s: s.relevance, reverse=True)

    # Filter: above threshold, capped at max_chunks
    selected = [
        s for s in scored
        if s.relevance >= threshold
    ][:max_chunks]

    tokens_used = sum(s.chunk.token_estimate for s in selected)
    tokens_saved = total_tok - tokens_used

    return FilterResult(
        question=question,
        total_chunks=len(chunks),
        scored_chunks=scored,
        selected_chunks=selected,
        threshold=threshold,
        total_tokens_available=total_tok,
        tokens_used=tokens_used,
        tokens_saved=tokens_saved,
        total_decider_latency_ms=total_latency,
    )


def check_decider_server() -> bool:
    """Return True if the Decider server is reachable."""
    try:
        r = requests.get(f"{DECIDER_URL}/health", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False
