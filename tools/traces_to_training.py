"""
tools/traces_to_training.py — Converts benchmark results to LLM training formats.

exports: main() → writes sft.jsonl, dpo.jsonl, prm.jsonl
used_by: none — standalone CLI tool
rules:   reads from runs/*/results.json and projects_swebench/ — never modifies them.
         supports both old format (files_read list) and new format (trace field).
         tool result content is truncated to CONTENT_LIMIT chars to keep examples manageable.
         DPO pairs require F1 delta >= DPO_MIN_DELTA — do not lower without good reason.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-20 | s_20260320_004 | created
         message: "reasoning_log field found in existing results — contains intermediate model
                  outputs, not chain-of-thought. Not usable as thinking trace for PRM.
                  When extended thinking is captured, add trace[n].thinking field and
                  include in prm.jsonl as thinking_before_step"

Usage:
    python tools/traces_to_training.py                        # all formats, default output
    python tools/traces_to_training.py --format sft           # only SFT
    python tools/traces_to_training.py --format dpo           # only DPO
    python tools/traces_to_training.py --format prm           # only PRM
    python tools/traces_to_training.py --f1-threshold 0.7     # stricter SFT quality gate
    python tools/traces_to_training.py --output-dir ./training_data
    python tools/traces_to_training.py --stats                # show dataset statistics only
"""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

RUNS_DIR = Path(__file__).parent.parent / "benchmark_agent" / "runs"
PROJECTS_DIR = Path(__file__).parent.parent / "benchmark_agent" / "projects_swebench"
TASKS_FILE = Path(__file__).parent.parent / "benchmark_agent" / "swebench" / "tasks.json"

CONTENT_LIMIT = 2000  # chars per tool result in training examples
DPO_MIN_DELTA = 0.15  # minimum F1 difference to form a DPO pair
SFT_MIN_F1 = 0.60  # minimum F1 to include in SFT

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class RunRecord:
    model: str
    provider: str
    task: str
    condition: str  # "control" or "codedna"
    f1: float
    files_read: list[str]  # ordered navigation sequence
    greps: list[str]
    ground_truth: list[str]
    final_answer: str
    session_id: str = ""
    trace: list[dict] = field(default_factory=list)  # new format


# ── Loaders ───────────────────────────────────────────────────────────────────


def _provider_for(model: str) -> str:
    if "gemini" in model:
        return "google"
    if "claude" in model:
        return "anthropic"
    if "deepseek" in model:
        return "deepseek"
    if "gpt" in model or "o1" in model or "o3" in model:
        return "openai"
    return "unknown"


def load_all_runs() -> list[RunRecord]:
    """Rules: loads from results.json — supports both old and new schema."""
    list_run_all = []

    for path_results in sorted(RUNS_DIR.glob("*/results.json")):
        str_model = path_results.parent.name
        str_provider = _provider_for(str_model)

        with open(path_results) as f:
            list_task_entry = json.load(f)

        for dict_entry in list_task_entry:
            str_task = dict_entry["instance_id"]
            list_gt = dict_entry.get("ground_truth_files", [])

            for str_cond in ("control", "codedna"):
                dict_run = dict_entry.get(str_cond)
                if not dict_run:
                    continue

                list_run_all.append(
                    RunRecord(
                        model=str_model,
                        provider=str_provider,
                        task=str_task,
                        condition=str_cond,
                        f1=dict_run.get("metrics_read", {}).get("f1", 0.0),
                        files_read=dict_run.get("files_read", []),
                        greps=dict_run.get("greps", []),
                        ground_truth=list_gt,
                        final_answer=dict_run.get("final_response", ""),
                        session_id=dict_run.get("session_id", ""),
                        trace=dict_run.get("trace", []),
                    )
                )

    return list_run_all


def _read_file_content(task: str, condition: str, path: str) -> str:
    """Reconstruct tool result content from filesystem. Returns truncated content."""
    target = PROJECTS_DIR / task / condition / path
    if not target.exists():
        return f"(file not found: {path})"
    try:
        return target.read_text(encoding="utf-8", errors="replace")[:CONTENT_LIMIT]
    except Exception:
        return f"(error reading: {path})"


def _load_task_problem(task: str) -> str:
    if not TASKS_FILE.exists():
        return f"(problem statement not found for {task})"
    with open(TASKS_FILE) as f:
        list_tasks = json.load(f)
    for dict_t in list_tasks:
        if dict_t["instance_id"] == task:
            return dict_t["problem_statement"]
    return f"(task {task} not found)"


# ── Navigation sequence reconstruction ───────────────────────────────────────


def _build_nav_sequence(run: RunRecord) -> list[dict]:
    """
    Rules: if trace field exists (new format), use it directly.
           Otherwise reconstruct from files_read (ordered) — greps cannot be
           interleaved accurately without trace, so they are appended at end.
           Mark each step with is_gt_file for downstream reward computation.
    """
    set_gt = set(run.ground_truth)

    if run.trace:
        # New format — exact sequence with timestamps
        list_step = []
        for dict_step in run.trace:
            str_path = dict_step.get("args", {}).get("path", "")
            list_step.append(
                {
                    "tool": dict_step["tool"],
                    "args": dict_step["args"],
                    "t": dict_step.get("t", 0.0),
                    "is_gt_file": str_path in set_gt,
                }
            )
        return list_step

    # Old format — reconstruct from files_read + greps
    list_step = []
    for str_path in run.files_read:
        list_step.append(
            {
                "tool": "read_file",
                "args": {"path": str_path},
                "t": None,
                "is_gt_file": str_path in set_gt,
            }
        )
    for str_pattern in run.greps:
        list_step.append(
            {
                "tool": "grep",
                "args": {"pattern": str_pattern},
                "t": None,
                "is_gt_file": False,
            }
        )
    return list_step


# ── SFT format ────────────────────────────────────────────────────────────────


def build_sft(list_run: list[RunRecord], float_min_f1: float) -> list[dict]:
    """
    Conversation JSONL — OpenAI fine-tuning format with tool calls.
    Includes only runs with F1 >= float_min_f1.

    Rules: system prompt varies by condition (control vs codedna).
           tool result content is reconstructed from filesystem and truncated.
    """
    # Import prompts from run_agent_multi — avoid duplication
    sys.path.insert(0, str(Path(__file__).parent.parent / "benchmark_agent" / "swebench"))
    try:
        from run_agent_multi import SYSTEM_PROMPT, CODEDNA_PROMPT
    except ImportError:
        SYSTEM_PROMPT = "You are an expert software engineer debugging a Python codebase."
        CODEDNA_PROMPT = SYSTEM_PROMPT

    list_sft_example = []

    for run in list_run:
        if run.f1 < float_min_f1:
            continue

        str_system = CODEDNA_PROMPT if run.condition == "codedna" else SYSTEM_PROMPT
        str_problem = _load_task_problem(run.task)
        list_nav = _build_nav_sequence(run)

        list_messages = [
            {"role": "system", "content": str_system},
            {"role": "user", "content": f"Problem:\n\n{str_problem}"},
        ]

        for dict_step in list_nav:
            str_tool = dict_step["tool"]
            dict_args = dict_step["args"]

            # assistant: tool call
            list_messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"type": "function", "function": {"name": str_tool, "arguments": json.dumps(dict_args)}}
                    ],
                }
            )

            # tool: result
            if str_tool == "read_file":
                str_result = _read_file_content(run.task, run.condition, dict_args["path"])
            elif str_tool == "grep":
                str_result = f"(grep result for pattern: {dict_args.get('pattern', '')})"
            else:
                str_result = f"(list_files result for: {dict_args.get('directory', '.')})"

            list_messages.append({"role": "tool", "content": str_result})

        # final assistant message
        list_messages.append(
            {
                "role": "assistant",
                "content": run.final_answer[:3000],  # truncate very long answers
            }
        )

        list_sft_example.append(
            {
                "messages": list_messages,
                "metadata": {
                    "session_id": run.session_id,
                    "model": run.model,
                    "task": run.task,
                    "condition": run.condition,
                    "f1": round(run.f1, 4),
                    "ground_truth": run.ground_truth,
                },
            }
        )

    return list_sft_example


# ── DPO format ────────────────────────────────────────────────────────────────


def build_dpo(list_run: list[RunRecord], float_min_delta: float) -> list[dict]:
    """
    Preference pairs: chosen (high F1) vs rejected (low F1) for same task.

    Pairing strategy (in priority order):
      1. codedna (chosen) vs control (rejected) — same task, same model
      2. any high-F1 run vs any low-F1 run — same task, cross-model

    Rules: delta must be >= float_min_delta to ensure meaningful contrast.
           prompt is the task description only (before any tool calls).
    """
    # Index by (task, model)
    dict_by_task_model: dict[tuple, dict[str, RunRecord]] = defaultdict(dict)
    for run in list_run:
        dict_by_task_model[(run.task, run.model)][run.condition] = run

    list_dpo_pair = []

    # Strategy 1: codedna vs control, same task + model
    for (str_task, str_model), dict_cond in dict_by_task_model.items():
        run_codedna = dict_cond.get("codedna")
        run_control = dict_cond.get("control")
        if not (run_codedna and run_control):
            continue

        float_delta = run_codedna.f1 - run_control.f1
        if float_delta < float_min_delta:
            continue

        str_problem = _load_task_problem(str_task)

        list_dpo_pair.append(
            {
                "prompt": [
                    {"role": "system", "content": "You are an expert software engineer."},
                    {"role": "user", "content": f"Problem:\n\n{str_problem}"},
                ],
                "chosen": _trajectory_to_messages(run_codedna),
                "rejected": _trajectory_to_messages(run_control),
                "metadata": {
                    "task": str_task,
                    "model": str_model,
                    "f1_chosen": round(run_codedna.f1, 4),
                    "f1_rejected": round(run_control.f1, 4),
                    "delta": round(float_delta, 4),
                    "pair_type": "codedna_vs_control",
                },
            }
        )

    # Strategy 2: high-F1 vs low-F1, cross-model, same task
    dict_by_task: dict[str, list[RunRecord]] = defaultdict(list)
    for run in list_run:
        dict_by_task[run.task].append(run)

    for str_task, list_task_run in dict_by_task.items():
        list_sorted = sorted(list_task_run, key=lambda r: r.f1, reverse=True)
        run_best = list_sorted[0]
        run_worst = list_sorted[-1]

        if run_best.model == run_worst.model:
            continue  # same model already covered by strategy 1
        if run_best.f1 - run_worst.f1 < float_min_delta:
            continue

        str_problem = _load_task_problem(str_task)

        list_dpo_pair.append(
            {
                "prompt": [
                    {"role": "system", "content": "You are an expert software engineer."},
                    {"role": "user", "content": f"Problem:\n\n{str_problem}"},
                ],
                "chosen": _trajectory_to_messages(run_best),
                "rejected": _trajectory_to_messages(run_worst),
                "metadata": {
                    "task": str_task,
                    "model_chosen": run_best.model,
                    "model_rejected": run_worst.model,
                    "f1_chosen": round(run_best.f1, 4),
                    "f1_rejected": round(run_worst.f1, 4),
                    "delta": round(run_best.f1 - run_worst.f1, 4),
                    "pair_type": "cross_model",
                },
            }
        )

    return list_dpo_pair


def _trajectory_to_messages(run: RunRecord) -> list[dict]:
    """Convert a run's navigation trace to a flat message list (assistant + tool turns)."""
    list_nav = _build_nav_sequence(run)
    list_messages = []

    for dict_step in list_nav:
        str_tool = dict_step["tool"]
        dict_args = dict_step["args"]

        list_messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"type": "function", "function": {"name": str_tool, "arguments": json.dumps(dict_args)}}
                ],
            }
        )

        if str_tool == "read_file":
            str_result = _read_file_content(run.task, run.condition, dict_args["path"])
        else:
            str_result = f"({str_tool} result)"

        list_messages.append({"role": "tool", "content": str_result})

    list_messages.append({"role": "assistant", "content": run.final_answer[:3000]})
    return list_messages


# ── PRM format ────────────────────────────────────────────────────────────────


def build_prm(list_run: list[RunRecord]) -> list[dict]:
    """
    Process Reward Model format — step-level reward annotation.

    Reward function:
      read_file(GT file)     → +1.0  (found a file that needs changing)
      read_file(non-GT file) → -0.1  (wasted a read)
      grep                   → +0.2  (exploratory, neutral-positive)
      list_files             → 0.0   (navigation overhead)
      trajectory_reward      → f1    (final outcome — Verifiable Reward for GRPO)

    Rules: reward function is intentionally simple — do not add domain-specific
           heuristics without benchmark validation. The F1-based trajectory reward
           is the ground truth; step rewards are soft signals.
    """
    list_prm_example = []

    for run in list_run:
        list_nav = _build_nav_sequence(run)
        if not list_nav:
            continue

        list_step_annotated = []
        for dict_step in list_nav:
            str_tool = dict_step["tool"]

            if str_tool == "read_file":
                float_reward = 1.0 if dict_step["is_gt_file"] else -0.1
            elif str_tool == "grep":
                float_reward = 0.2
            else:
                float_reward = 0.0

            list_step_annotated.append(
                {
                    "tool": str_tool,
                    "args": dict_step["args"],
                    "t": dict_step.get("t"),
                    "is_gt_file": dict_step["is_gt_file"],
                    "reward": float_reward,
                }
            )

        list_prm_example.append(
            {
                "session_id": run.session_id,
                "model": run.model,
                "task": run.task,
                "condition": run.condition,
                "ground_truth": run.ground_truth,
                "steps": list_step_annotated,
                "trajectory_reward": round(run.f1, 4),  # verifiable reward for GRPO
                "note_missing": (
                    "thinking/reasoning not captured — step rewards are tool-call-level only. "
                    "Add trace[n].thinking when extended thinking is available."
                ),
            }
        )

    return list_prm_example


# ── Stats ─────────────────────────────────────────────────────────────────────


def print_stats(list_run: list[RunRecord], list_sft: list, list_dpo: list, list_prm: list) -> None:
    print(f"\n  runs loaded:      {len(list_run)}")
    print(f"  models:           {sorted(set(r.model for r in list_run))}")
    print(f"  tasks:            {sorted(set(r.task for r in list_run))}")
    print(f"\n  SFT examples:     {len(list_sft)}  (F1 >= {SFT_MIN_F1})")
    print(f"  DPO pairs:        {len(list_dpo)}  (delta >= {DPO_MIN_DELTA})")
    print(f"  PRM examples:     {len(list_prm)}")

    if list_dpo:
        print(f"\n  DPO pair types:")
        from collections import Counter

        counter = Counter(p["metadata"]["pair_type"] for p in list_dpo)
        for str_ptype, int_n in counter.items():
            print(f"    {str_ptype}: {int_n}")

    print(f"\n  F1 distribution:")
    for run in sorted(list_run, key=lambda r: r.f1, reverse=True):
        str_bar = "█" * int(run.f1 * 20)
        print(f"    {str_bar:<20} {run.f1:.2f}  {run.model} / {run.task.split('-')[-1]} / {run.condition}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Convert benchmark results to training formats")
    parser.add_argument("--format", choices=["sft", "dpo", "prm", "all"], default="all")
    parser.add_argument("--f1-threshold", type=float, default=SFT_MIN_F1)
    parser.add_argument("--dpo-delta", type=float, default=DPO_MIN_DELTA)
    parser.add_argument("--output-dir", type=str, default="./training_data")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    list_run_all = load_all_runs()
    if not list_run_all:
        print("No results found. Run the benchmark first.")
        return

    list_sft = build_sft(list_run_all, args.f1_threshold)
    list_dpo = build_dpo(list_run_all, args.dpo_delta)
    list_prm = build_prm(list_run_all)

    if args.stats:
        print_stats(list_run_all, list_sft, list_dpo, list_prm)
        return

    path_out = Path(args.output_dir)
    path_out.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(path: Path, list_data: list) -> None:
        with open(path, "w") as f:
            for dict_item in list_data:
                f.write(json.dumps(dict_item, ensure_ascii=False) + "\n")
        print(f"  wrote {len(list_data):>4} examples → {path}")

    print(f"\nWriting training data to {path_out}/\n")

    if args.format in ("sft", "all"):
        _write_jsonl(path_out / "sft.jsonl", list_sft)
    if args.format in ("dpo", "all"):
        _write_jsonl(path_out / "dpo.jsonl", list_dpo)
    if args.format in ("prm", "all"):
        _write_jsonl(path_out / "prm.jsonl", list_prm)

    print_stats(list_run_all, list_sft, list_dpo, list_prm)


if __name__ == "__main__":
    main()
