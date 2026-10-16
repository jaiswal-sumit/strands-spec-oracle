"""
Strands InterventionHandler: SpecContextInterventionHandler

Hooks into the agent loop BEFORE each model call to:
  1. Extract the latest developer question from the conversation
  2. Call Decider 2B to score all spec chunks for relevance
  3. Inject ONLY the relevant chunks via Guide (becomes a user message)

This is the reusable pattern for the hackathon. Drop it into any Strands agent
that has access to a directory of markdown files and a running Decider server.

Pattern: Context & Memory
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from strands import InterventionHandler
from strands.hooks.events import BeforeModelCallEvent
from strands.interventions import Guide, Proceed

from .chunker import load_spec_directory
from .decider_client import FilterResult, score_and_filter


class SpecContextInterventionHandler(InterventionHandler):
    """
    Before each Bedrock call, score all spec chunks with Decider 2B
    and inject only the relevant ones as a guided user message.

    Usage:
        handler = SpecContextInterventionHandler(spec_dir="./specs")
        agent = Agent(
            model=BedrockModel(...),
            tools=[...],
            interventions=[handler],
        )

    The handler exposes `last_filter_result` so the caller can inspect
    token savings after each query.
    """

    name = "spec-context-scorer"

    def __init__(self, spec_dir: str | Path) -> None:
        self.spec_dir = Path(spec_dir)
        self._chunks = load_spec_directory(self.spec_dir)
        self.last_filter_result: FilterResult | None = None
        self._last_question: str = ""

    def reload_specs(self) -> None:
        """Reload spec files from disk (call after editing specs)."""
        self._chunks = load_spec_directory(self.spec_dir)

    def before_model_call(
        self, event: BeforeModelCallEvent, **kwargs: Any
    ) -> Proceed | Guide:
        """
        Extract the latest user question, score chunks with Decider 2B,
        and inject only the relevant ones as a Guide message.

        Guide on before_model_call injects the feedback as a user message
        that the model sees before generating its response.
        """
        question = _extract_last_user_text(event)
        if not question or question == self._last_question:
            return Proceed()

        self._last_question = question

        # Score chunks with Decider 2B
        result = score_and_filter(question, self._chunks)
        self.last_filter_result = result

        if not result.selected_chunks:
            return Proceed()

        context_block = _build_context_block(result)
        return Guide(feedback=context_block)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_last_user_text(event: BeforeModelCallEvent) -> str:
    """Return the text of the most recent user message from agent.messages."""
    try:
        messages = event.agent.messages
        for msg in reversed(messages):
            if msg.get("role") == "user":
                for block in msg.get("content", []):
                    if isinstance(block, dict) and "text" in block:
                        return block["text"]
    except Exception:
        pass
    return ""


def _build_context_block(result: FilterResult) -> str:
    """
    Format the selected spec chunks as a context block for the LLM.
    Includes a provenance header so the model can cite sources.
    """
    lines = [
        "## Relevant Specification Sections",
        f"(Decider 2B selected {len(result.selected_chunks)} of "
        f"{result.total_chunks} spec chunks · "
        f"threshold={result.threshold:.2f} · "
        f"~{result.tokens_saved:,} tokens saved)",
        "",
    ]

    for sc in result.selected_chunks:
        lines.append(
            f"### [{sc.chunk.file}] {sc.chunk.heading} "
            f"(relevance={sc.relevance:.2f}, confidence={sc.confidence:.2f})"
        )
        lines.append(sc.chunk.text)
        lines.append("")

    lines.append(
        "Use ONLY the specification sections above to answer the developer's question. "
        "Cite the file and section heading when you reference a spec detail."
    )

    return "\n".join(lines)
