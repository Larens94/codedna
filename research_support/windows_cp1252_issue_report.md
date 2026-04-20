# Bug Report Draft: Windows cp1252 UnicodeEncodeError in benchmark setup

## Summary

On Windows terminals using cp1252 encoding, `labs/benchmark/setup_benchmark.py` can crash with:

`UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`

This blocks `--annotate` flow and makes onboarding harder for Windows contributors.

## Reproduction

Environment:
- OS: Windows
- Python: 3.11
- Terminal encoding: cp1252 default

Command:

```bash
python labs/benchmark/setup_benchmark.py --repo django/django --n-tasks 1 --multi-file-first --annotate --no-llm
```

Observed traceback (key part):

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
```

## Likely cause

The script prints Unicode symbols (example: arrow `\u2192`) to stdout.
When stdout encoding is cp1252, those characters cannot be encoded.

## Impact

- Interrupts benchmark preparation on Windows.
- Reduces cross-platform reproducibility.
- Affects non-expert contributors first (high friction in onboarding).

## Minimal fix options

1. Replace non-ASCII symbols in log strings with ASCII equivalents (`->`).
2. Guard prints with safe fallback:
   - detect stdout encoding
   - fallback to ASCII-safe strings when needed
3. Document recommended env vars for Windows:
   - `PYTHONUTF8=1`
   - `PYTHONIOENCODING=utf-8`

## Suggested acceptance criteria

- Same command succeeds on Windows default terminal without manual encoding setup.
- No behavior change in Linux/macOS output quality.
