#!/usr/bin/env python3
"""
benchmark.py — Measure token savings from Decider 2B context gating

Runs a fixed set of queries against your spec corpus and reports:
  - Total chunks in corpus
  - Chunks selected per query
  - Tokens used vs. tokens available
  - Token savings (absolute and %)
  - Decider 2B latency per chunk

Usage:
    python benchmark.py --specs ./demo/specs
    python benchmark.py --specs /path/to/your/specs --threshold 0.5

Requires the Decider 2B server running on DECIDER_SERVER_URL (default: http://localhost:8000).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

load_dotenv()

console = Console()

DEMO_QUERIES = [
    "What is the retry strategy for failed payments?",
    "How should I handle a card decline?",
    "What is the payment status state machine?",
    "How do I set up webhooks and verify their signatures?",
    "What are the rate limits for write endpoints?",
    "How do I handle a customer dispute (chargeback)?",
    "How do I set up Apple Pay?",
    "What scopes does an API key need to process refunds?",
    "How does subscription dunning work when a payment fails?",
    "What is the difference between presentment and settlement currency?",
]


def run_benchmark(spec_dir: Path, threshold: float, max_chunks: int) -> None:
    # Local import so this script can be run from any directory
    sys.path.insert(0, str(Path(__file__).parent))
    from spec_oracle.chunker import load_spec_directory, total_tokens
    from spec_oracle.decider_client import check_decider_server, score_and_filter

    chunks = load_spec_directory(spec_dir)
    if not chunks:
        console.print(f"[red]No spec files found in {spec_dir}[/red]")
        sys.exit(1)

    total_tok = total_tokens(chunks)
    n_chunks = len(chunks)
    n_files = len(set(c.file for c in chunks))

    console.print(
        Panel(
            f"[bold cyan]Decider 2B Benchmark[/bold cyan]\n\n"
            f"Spec directory: {spec_dir}\n"
            f"Files: {n_files}  |  Chunks: {n_chunks}  |  Total tokens: ~{total_tok:,}\n"
            f"Threshold: {threshold:.2f}  |  Max chunks: {max_chunks}\n",
            border_style="cyan",
        )
    )

    if not check_decider_server():
        console.print(
            "[red]Decider 2B server not reachable. "
            f"Start it with: strands-decider serve <model> --port 8000[/red]"
        )
        sys.exit(1)

    results_table = Table(
        title="[bold]Per-Query Results[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    results_table.add_column("Query", style="white", max_width=50)
    results_table.add_column("Chunks\nused", justify="right")
    results_table.add_column("Tokens\nused", justify="right")
    results_table.add_column("Tokens\nsaved", justify="right")
    results_table.add_column("Saved\n%", justify="right")
    results_table.add_column("Decider total\n(all chunks)", justify="right")

    total_savings = 0
    total_used = 0
    total_latency = 0.0
    rows_added = 0

    for query in DEMO_QUERIES:
        t0 = time.perf_counter()
        try:
            result = score_and_filter(query, chunks, threshold=threshold, max_chunks=max_chunks)
        except Exception as e:
            console.print(f"[yellow]Skipping '{query[:40]}': {e}[/yellow]")
            continue
        elapsed_ms = (time.perf_counter() - t0) * 1000

        savings_pct = result.reduction_pct
        results_table.add_row(
            query[:50],
            str(len(result.selected_chunks)),
            f"~{result.tokens_used:,}",
            f"~{result.tokens_saved:,}",
            f"{savings_pct:.0f}%",
            f"{elapsed_ms:.0f}ms",
        )
        total_savings += result.tokens_saved
        total_used += result.tokens_used
        total_latency += elapsed_ms
        rows_added += 1

    console.print(results_table)

    if rows_added > 0:
        avg_savings_pct = (total_savings / (total_savings + total_used)) * 100 if (total_savings + total_used) > 0 else 0
        avg_latency = total_latency / rows_added
        console.print(
            Panel(
                f"Queries run: {rows_added}\n"
                f"Average tokens used: ~{total_used // rows_added:,} per query\n"
                f"Average tokens saved: ~{total_savings // rows_added:,} per query\n"
                f"Average savings: [bold green]{avg_savings_pct:.1f}%[/bold green]\n"
                f"Average Decider 2B latency: {avg_latency:.0f}ms per query\n"
                f"  ({avg_latency / n_chunks:.0f}ms per chunk)\n"
                f"\n[dim]Corpus size: {n_chunks} chunks · ~{total_tok:,} tokens across {n_files} files[/dim]",
                title="[bold]Summary[/bold]",
                border_style="green",
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Decider 2B token savings on a spec corpus"
    )
    parser.add_argument(
        "--specs",
        type=Path,
        default=Path("./demo/specs"),
        help="Path to spec directory (default: ./demo/specs)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.environ.get("RELEVANCE_THRESHOLD", "0.55")),
        help="Relevance score threshold 0–1 (default: 0.55)",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=int(os.environ.get("MAX_CHUNKS", "6")),
        help="Maximum chunks to inject per query (default: 6)",
    )
    args = parser.parse_args()

    spec_dir = args.specs.resolve()
    if not spec_dir.exists():
        console.print(f"[red]Spec directory not found: {spec_dir}[/red]")
        sys.exit(1)

    run_benchmark(spec_dir, args.threshold, args.max_chunks)


if __name__ == "__main__":
    main()
