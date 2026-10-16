"""
display.py — Rich terminal display helpers for Spec Oracle.

Kept in a separate module so both agent.py and handlers.py can import
print_filter_result without creating a circular dependency.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .decider_client import FilterResult

console = Console()


def print_filter_result(result: FilterResult) -> None:
    """Print a Rich table showing Decider 2B scoring results."""
    table = Table(
        title="[bold cyan]Decider 2B — Spec Relevance Scoring[/bold cyan]",
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

    savings_pct = result.reduction_pct
    console.print(
        Panel(
            f"[bold]Chunks:[/bold] {len(result.selected_chunks)} used / {result.total_chunks} total  "
            f"  [bold]Tokens:[/bold] ~{result.tokens_used:,} used / ~{result.total_tokens_available:,} available  "
            f"  [bold green]Saved ~{result.tokens_saved:,} tokens ({savings_pct:.0f}%)[/bold green]\n"
            f"  [dim]Decider 2B latency: {result.total_decider_latency_ms:.0f}ms total "
            f"({result.total_decider_latency_ms / max(result.total_chunks, 1):.0f}ms/chunk avg)[/dim]",
            title="[bold]Context Efficiency[/bold]",
            border_style="green",
        )
    )
