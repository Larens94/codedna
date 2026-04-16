"""dashboard.py — Real-time TUI dashboard for the controlled experiment.

exports: _HERE | RUNS_ROOT | COLOUR_A | COLOUR_B | COLOUR_OK | COLOUR_ERR | COLOUR_DIM | run_dashboard(run_dir, interval)
used_by: none
rules:   read-only — never writes any file;
polls the run directory every <interval> seconds;
gracefully handles missing directories (run not started yet);
requires: rich>=13.0
agent:   claude-sonnet-4-6 | anthropic | 2026-03-29 | s_20260329_002 | Initial design
claude-sonnet-4-6 | anthropic | 2026-03-30 | s_20260330_001 | Added interactive run picker (_pick_run); added --latest flag; imported rich.prompt.Prompt
USAGE:
# Interactive run picker (default):
python visualizer/dashboard.py
# Watch a specific run directly:
python visualizer/dashboard.py --run run_20260329_153000
# Auto-select latest run (skip picker):
python visualizer/dashboard.py --latest
# Change poll interval (default 2s):
python visualizer/dashboard.py --interval 3
# Exit: Ctrl-C
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# ── rich imports ─────────────────────────────────────────────────────────────
try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: 'rich' is required.  Install with:  pip install rich")
    sys.exit(1)

# ── local parser ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from parser import (
    ConditionSnapshot,
    RunSnapshot,
    find_latest_run,
    scan_run,
)

RUNS_ROOT = Path(__file__).parent.parent / "runs"

console = Console()

# Colour scheme
COLOUR_A   = "cyan"
COLOUR_B   = "yellow"
COLOUR_OK  = "green"
COLOUR_ERR = "red"
COLOUR_DIM = "dim"


# ─────────────────────────────────────────────────────────────────────────────
# PANEL BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _stats_bar(snap: RunSnapshot) -> Panel:
    """Top stats bar — one row per condition."""
    table = Table(box=box.SIMPLE_HEAD, expand=True, show_header=True,
                  header_style="bold white")
    table.add_column("Condition",   style="bold", width=22)
    table.add_column("Files (.py)", justify="right", width=12)
    table.add_column("LOC",         justify="right", width=8)
    table.add_column("Annotated",   justify="right", width=12)
    table.add_column("Coverage",    justify="right", width=10)
    table.add_column("Agents seen", width=30)

    colours = {"a": COLOUR_A, "b": COLOUR_B}
    labels  = {"a": "[A] Annotation Protocol", "b": "[B] Standard Practices"}

    for cond in ("a", "b"):
        cs = snap.conditions.get(cond)
        col = colours[cond]
        if cs is None or cs.py_file_count == 0:
            table.add_row(
                Text(labels[cond], style=f"bold {col}"),
                Text("—", style=COLOUR_DIM),
                Text("—", style=COLOUR_DIM),
                Text("—", style=COLOUR_DIM),
                Text("—", style=COLOUR_DIM),
                Text("(waiting…)", style=COLOUR_DIM),
            )
        else:
            agents_str = ", ".join(cs.unique_agents[:5]) or "—"
            cov_colour = COLOUR_OK if cs.coverage_pct > 80 else (
                "yellow" if cs.coverage_pct > 40 else COLOUR_ERR
            )
            table.add_row(
                Text(labels[cond], style=f"bold {col}"),
                str(cs.py_file_count),
                str(cs.total_loc),
                str(cs.annotated_count),
                Text(f"{cs.coverage_pct:.1f}%", style=cov_colour),
                Text(agents_str, style=COLOUR_DIM),
            )

    return Panel(table, title=f"[bold]{snap.run_id}[/]  —  refreshed {datetime.now().strftime('%H:%M:%S')}",
                 border_style="white")


def _file_panel(cs: ConditionSnapshot, colour: str) -> Panel:
    """File list with annotation status for one condition."""
    table = Table(box=box.MINIMAL, expand=True, show_header=False)
    table.add_column("icon", width=2)
    table.add_column("file", no_wrap=True)
    table.add_column("exports", style=COLOUR_DIM, no_wrap=True)

    if not cs.files:
        table.add_row("", Text("(no files yet)", style=COLOUR_DIM), "")
    else:
        for fa in sorted(cs.files, key=lambda f: f.relative_path):
            icon  = Text("✓", style=COLOUR_OK) if fa.has_annotation_header else Text("·", style=COLOUR_DIM)
            fname = Text(fa.relative_path, style=colour if fa.has_annotation_header else COLOUR_DIM)
            exp   = (fa.exports or "")[:40]
            table.add_row(icon, fname, exp)

    label = f"[bold {colour}][{cs.condition.upper()}] {cs.label}[/]  files"
    return Panel(table, title=label, border_style=colour)


def _agent_activity_panel(cs: ConditionSnapshot, colour: str) -> Panel:
    """agent: entries timeline for one condition."""
    table = Table(box=box.MINIMAL, expand=True, show_header=True,
                  header_style=f"bold {colour}")
    table.add_column("Date",  width=11, style=COLOUR_DIM)
    table.add_column("Agent", width=18)
    table.add_column("Note",  no_wrap=False)

    entries = cs.all_agent_entries
    if not entries:
        table.add_row("", Text("(no agent: entries yet)", style=COLOUR_DIM), "")
    else:
        for ae in entries[-20:]:      # last 20
            table.add_row(
                ae.date[:10],
                Text(ae.name, style=f"bold {colour}"),
                ae.note[:80],
            )

    label = f"[bold {colour}]agent: activity[/]"
    return Panel(table, title=label, border_style=colour)


def _message_panel(cs: ConditionSnapshot, colour: str) -> Panel:
    """message: inter-agent threads for one condition."""
    table = Table(box=box.MINIMAL, expand=True, show_header=True,
                  header_style=f"bold {colour}")
    table.add_column("Location", width=24, style=COLOUR_DIM, no_wrap=True)
    table.add_column("Agent",    width=16)
    table.add_column("Message",  no_wrap=False)

    messages = cs.all_messages
    if not messages:
        table.add_row("", Text("(no message: annotations yet)", style=COLOUR_DIM), "")
    else:
        for loc, ae in messages[-15:]:
            table.add_row(
                loc[:24],
                Text(ae.name, style=f"bold {colour}"),
                ae.message[:90] if ae.message else "",
            )

    label = f"[bold {colour}]message: channel[/]"
    return Panel(table, title=label, border_style=colour)


def _events_panel(cs: ConditionSnapshot, colour: str) -> Panel:
    """Session log events for one condition."""
    table = Table(box=box.MINIMAL, expand=True, show_header=False)
    table.add_column("time",  width=8, style=COLOUR_DIM)
    table.add_column("agent", width=14)
    table.add_column("type",  width=16, style=COLOUR_DIM)
    table.add_column("summary", no_wrap=False)

    events = cs.events
    if not events:
        table.add_row("", Text("(no session events yet)", style=COLOUR_DIM), "", "")
    else:
        for ev in events[-12:]:
            ts = ev.timestamp[11:19] if len(ev.timestamp) >= 19 else ev.timestamp[:8]
            table.add_row(
                ts,
                Text(ev.agent[:14], style=f"{colour}"),
                ev.event_type[:16],
                ev.summary[:80],
            )

    label = f"[bold {colour}]session events[/]"
    return Panel(table, title=label, border_style=colour)


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_layout(snap: RunSnapshot) -> Layout:
    root = Layout()

    # Top: stats bar
    root.split_column(
        Layout(name="stats",   size=7),
        Layout(name="main"),
        Layout(name="footer",  size=1),
    )

    root["stats"].update(_stats_bar(snap))

    # Main: two columns (A left, B right)
    root["main"].split_row(
        Layout(name="col_a"),
        Layout(name="col_b"),
    )

    cs_a = snap.conditions.get("a", ConditionSnapshot("a", "Annotation Protocol", Path()))
    cs_b = snap.conditions.get("b", ConditionSnapshot("b", "Standard Practices",  Path()))

    # Each column: files / agents / messages / events
    root["col_a"].split_column(
        Layout(_file_panel(cs_a, COLOUR_A),           name="a_files",   ratio=3),
        Layout(_agent_activity_panel(cs_a, COLOUR_A), name="a_agents",  ratio=3),
        Layout(_message_panel(cs_a, COLOUR_A),        name="a_msgs",    ratio=3),
        Layout(_events_panel(cs_a, COLOUR_A),         name="a_events",  ratio=2),
    )
    root["col_b"].split_column(
        Layout(_file_panel(cs_b, COLOUR_B),           name="b_files",   ratio=3),
        Layout(_agent_activity_panel(cs_b, COLOUR_B), name="b_agents",  ratio=3),
        Layout(_message_panel(cs_b, COLOUR_B),        name="b_msgs",    ratio=3),
        Layout(_events_panel(cs_b, COLOUR_B),         name="b_events",  ratio=2),
    )

    root["footer"].update(
        Text(
            "  [A] cyan = annotation protocol   [B] yellow = standard practices"
            "   │   Ctrl-C to quit",
            style=COLOUR_DIM,
        )
    )
    return root


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_dashboard(run_dir: Path, interval: float = 2.0) -> None:
    """Poll run_dir every interval seconds and update the live display.

    Rules:   Never writes anything; exits cleanly on KeyboardInterrupt.
    """
    console.print(f"\n[bold]Dashboard starting[/] — watching [cyan]{run_dir}[/]")
    console.print(f"  Poll interval: {interval}s   │   Ctrl-C to quit\n")

    with Live(console=console, refresh_per_second=0.5, screen=True) as live:
        try:
            while True:
                snap = scan_run(run_dir)
                live.update(_build_layout(snap))
                time.sleep(interval)
        except KeyboardInterrupt:
            pass

    console.print("\n[dim]Dashboard stopped.[/]")


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE RUN PICKER
# ─────────────────────────────────────────────────────────────────────────────

def _pick_run(runs_root: Path) -> Path | None:
    """Display available runs and let the user choose one interactively.

    Rules:   Returns None if no runs exist; never raises on empty directory.
    """
    list_path_runs = sorted(
        [d for d in runs_root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    if not list_path_runs:
        return None

    table = Table(box=box.SIMPLE_HEAD, expand=False, show_header=True,
                  header_style="bold white")
    table.add_column("#",    width=4,  justify="right", style="bold cyan")
    table.add_column("Run ID", style="white")
    table.add_column("Size",   justify="right", style="dim")

    for idx, run_dir in enumerate(list_path_runs, start=1):
        list_path_py = list(run_dir.rglob("*.py"))
        str_size = f"{len(list_path_py)} .py" if list_path_py else "—"
        str_marker_latest = "  [green]← latest[/]" if idx == 1 else ""
        table.add_row(str(idx), run_dir.name + str_marker_latest, str_size)

    console.print()
    console.print(Panel(table, title="[bold]Available runs[/]", border_style="white"))

    str_choice = Prompt.ask(
        "Select run",
        default="1",
        console=console,
    )
    try:
        int_choice = int(str_choice)
        if 1 <= int_choice <= len(list_path_runs):
            return list_path_runs[int_choice - 1]
    except ValueError:
        # user typed a run ID directly
        path_direct = runs_root / str_choice
        if path_direct.exists():
            return path_direct

    console.print(f"[red]Invalid selection:[/] {str_choice!r}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Real-time TUI dashboard for the CodeDNA experiment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualizer/dashboard.py                        # interactive run picker
  python visualizer/dashboard.py --run run_20260329_153000
  python visualizer/dashboard.py --latest               # skip picker, use latest
  python visualizer/dashboard.py --interval 5           # slower polling
        """
    )
    cli.add_argument("--run", metavar="RUN_ID",
                     help="Run ID to watch directly (skips picker)")
    cli.add_argument("--latest", action="store_true",
                     help="Auto-select the latest run without prompting")
    cli.add_argument("--interval", type=float, default=2.0,
                     help="Poll interval in seconds (default: 2)")
    args = cli.parse_args()

    if args.run:
        target = RUNS_ROOT / args.run
        if not target.exists():
            console.print(f"[red]Run not found:[/] {target}")
            sys.exit(1)
    elif args.latest:
        target = find_latest_run(RUNS_ROOT)
        if target is None:
            console.print(f"[yellow]No runs found in[/] {RUNS_ROOT}")
            sys.exit(1)
        console.print(f"[dim]Latest run:[/] {target.name}")
    else:
        target = _pick_run(RUNS_ROOT)
        if target is None:
            console.print(
                f"[yellow]No runs found in[/] {RUNS_ROOT}\n"
                "Start an experiment first:\n"
                "  [bold]python run_experiment.py[/]"
            )
            sys.exit(1)

    run_dashboard(target, interval=args.interval)
