"""
Strands Spec Oracle — main agent entry point.

Usage:
    # 1. Start Decider 2B server (one-time, in a separate terminal):
    strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000

    # 2. Run the agent:
    python -m spec_oracle.agent --specs ./demo/specs

    # Or install and use the CLI:
    pip install -e .
    spec-oracle --specs ./demo/specs
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from strands import Agent, tool
from strands.models import BedrockModel

from .chunker import load_spec_directory, total_tokens
from .decider_client import check_decider_server, score_and_filter, FilterResult
from .handlers import SpecContextInterventionHandler

console = Console()

# ── Bedrock model config ──────────────────────────────────────────────────────

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
)

SYSTEM_PROMPT = """\
You are Spec Oracle, an expert assistant for Spec-Driven Development (SDD) teams.
You answer questions about software specifications accurately and precisely.

Rules:
- Answer ONLY from the specification sections provided in your context.
- Always cite the spec file and section (e.g. "per [api-contract.md › Auth Endpoints]").
- If the answer is not in the provided specs, say so clearly — do not guess.
- Keep answers concise and developer-focused.
"""

# ── Rich display helpers ──────────────────────────────────────────────────────

def print_filter_result(result: FilterResult) -> None:
    """Print a Rich table showing Decider 2B scoring results."""
    table = Table(
        title=f"[bold cyan]Decider 2B — Spec Relevance Scoring[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("File", style="dim", no_wrap=True)
    table.add_column("Section", style="white")
    table.add_column("Relevance", justify="right")
    table.add_column("Conf.", justify="right")
    table.add_column("Selected", justify="center")

    selected_files = {id(s.chunk) for s in result.selected_chunks}

    for sc in result.scored_chunks:
        is_selected = id(sc.chunk) in selected_files
        rel_color = "green" if is_selected else ("yellow" if sc.relevance >= 0.35 else "red")
        table.add_row(
            sc.chunk.file,
            sc.chunk.heading[:60],
            f"[{rel_color}]{sc.relevance:.2f}[/{rel_color}]",
            f"{sc.confidence:.2f}",
            "[bold green]✓[/bold green]" if is_selected else "[dim]–[/dim]",
        )

    console.print(table)

    # Token savings summary
    savings_pct = result.reduction_pct
    console.print(
        Panel(
            f"[bold]Chunks:[/bold] {len(result.selected_chunks)} used / {result.total_chunks} total  "
            f"  [bold]Tokens:[/bold] ~{result.tokens_used:,} used / ~{result.total_tokens_available:,} available  "
            f"  [bold green]Saved ~{result.tokens_saved:,} tokens ({savings_pct:.0f}%)[/bold green]\n"
            f"  [dim]Decider 2B latency: {result.total_decider_latency_ms:.0f}ms total "
            f"({result.total_decider_latency_ms / result.total_chunks:.0f}ms/chunk avg)[/dim]",
            title="[bold]Context Efficiency[/bold]",
            border_style="green",
        )
    )


# ── Strands tool ──────────────────────────────────────────────────────────────

# The spec_dir is injected at runtime via a closure
_spec_dir: Path = Path(".")

@tool
def query_specs(question: str) -> str:
    """
    Search the project's specification files for information relevant to the
    given question. Uses Decider 2B to score each spec chunk for relevance
    before passing only the top-scoring chunks to the language model.

    Args:
        question: The developer question to answer from the specs.

    Returns:
        A formatted string containing the relevant spec sections, with
        token-savings metadata for transparency.
    """
    chunks = load_spec_directory(_spec_dir)
    if not chunks:
        return "No spec files found in the spec directory."

    result = score_and_filter(question, chunks)
    print_filter_result(result)

    if not result.selected_chunks:
        return (
            f"Decider 2B found no spec chunks above the relevance threshold "
            f"({result.threshold:.2f}) for this question. "
            f"Try rephrasing or lowering RELEVANCE_THRESHOLD."
        )

    lines = [
        f"Found {len(result.selected_chunks)} relevant spec sections "
        f"(from {result.total_chunks} total, "
        f"saved ~{result.tokens_saved:,} tokens):\n"
    ]
    for sc in result.selected_chunks:
        lines.append(
            f"### [{sc.chunk.file}] {sc.chunk.heading} "
            f"(relevance={sc.relevance:.2f})"
        )
        lines.append(sc.chunk.text)
        lines.append("")

    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────────────

def build_agent(spec_dir: Path, tool_mode: bool = False) -> Agent:
    """Construct and return the Spec Oracle Strands agent.

    Args:
        tool_mode: If True, expose query_specs as an explicit tool the model
                   calls visibly (great for demos). If False (default), the
                   InterventionHandler transparently scores and injects context.
    """
    global _spec_dir
    _spec_dir = spec_dir

    model = BedrockModel(model_id=BEDROCK_MODEL_ID)

    if tool_mode:
        # Demo mode: model explicitly calls query_specs — scoring table visible
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=[query_specs],
            interventions=[],
        )
    else:
        # Default: InterventionHandler scores + injects context transparently
        handler = SpecContextInterventionHandler(spec_dir=spec_dir)
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            tools=[],
            interventions=[handler],
        )
    return agent


def interactive_loop(agent: Agent, spec_dir: Path, tool_mode: bool = False) -> None:
    """Run the interactive Q&A loop."""
    chunks = load_spec_directory(spec_dir)
    tok = total_tokens(chunks)

    console.print(
        Panel(
            f"[bold cyan]Strands Spec Oracle[/bold cyan] — powered by Decider 2B + Amazon Bedrock\n\n"
            f"[dim]Spec directory:[/dim] {spec_dir}\n"
            f"[dim]Spec files:[/dim] {len(set(c.file for c in chunks))} files · "
            f"{len(chunks)} chunks · ~{tok:,} tokens total\n"
            f"[dim]Bedrock model:[/dim] {BEDROCK_MODEL_ID}\n\n"
            f"Mode: [bold]{'tool (explicit query_specs)' if tool_mode else 'handler (transparent injection)'}[/bold]\n\n"
            f"Type your question and press Enter. Type [bold]exit[/bold] to quit.",
            border_style="cyan",
        )
    )

    while True:
        console.print()
        try:
            question = console.input("[bold yellow]❯ Question:[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not question or question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()
        t0 = time.perf_counter()
        try:
            console.print("[bold green]Answer:[/bold green]")
            response = agent(question)
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            continue

        elapsed = time.perf_counter() - t0
        console.print(f"[dim]({elapsed:.1f}s total · Decider 2B + Bedrock)[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strands Spec Oracle — query SDD specs with Decider 2B + Bedrock"
    )
    parser.add_argument(
        "--specs",
        type=Path,
        default=Path("./demo/specs"),
        help="Path to directory containing .md spec files (default: ./demo/specs)",
    )
    parser.add_argument(
        "--tool-mode",
        action="store_true",
        default=False,
        help=(
            "Demo mode: expose query_specs as an explicit tool so the model calls it visibly. "
            "Default: InterventionHandler injects context transparently."
        ),
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        default=None,
        help="Ask a single question non-interactively and exit",
    )
    args = parser.parse_args()

    spec_dir = args.specs.resolve()
    if not spec_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Spec directory not found: {spec_dir}")
        sys.exit(1)

    # Check Decider server
    if not check_decider_server():
        console.print(
            "[bold yellow]Warning:[/bold yellow] Decider 2B server not reachable at "
            f"{os.environ.get('DECIDER_SERVER_URL', 'http://localhost:8000')}.\n"
            "Start it with:\n"
            "  [bold]strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000[/bold]\n"
            "Continuing in degraded mode (no context scoring)."
        )

    agent = build_agent(spec_dir, tool_mode=args.tool_mode)

    if args.question:
        # Single-shot mode
        chunks = load_spec_directory(spec_dir)
        result = score_and_filter(args.question, chunks)
        print_filter_result(result)
        console.print("[bold green]Answer:[/bold green]")
        agent(args.question)
    else:
        interactive_loop(agent, spec_dir, tool_mode=args.tool_mode)


if __name__ == "__main__":
    main()
