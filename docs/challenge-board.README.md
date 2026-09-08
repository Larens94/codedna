# Updating the public challenge board

The live board is [`docs/challenge.html`](../docs/challenge.html).  
It reads [`docs/challenge-board.json`](../docs/challenge-board.json) (static — no backend).

## When a metrics PR is accepted

1. Merge the PR (`challenge/<handle>/metrics.json`).
2. Append a row to `docs/challenge-board.json` → `submissions` using fields from that JSON:

```json
{
  "handle": "alice",
  "pr_url": "https://github.com/Larens94/codedna/pull/123",
  "pr_number": 123,
  "languages": ["TypeScript"],
  "frameworks": ["NestJS"],
  "approx_source_files": 180,
  "size_band": "M",
  "mode": "parity",
  "tasks_total": 10,
  "control_passed": 7,
  "codedna_passed": 9,
  "favors": "codedna",
  "merged": true
}
```

3. Bump `updated_at` (ISO date).
4. Commit + push `main` so GitHub Pages refreshes.

Enrollment does **not** require an issue — the metrics PR is enough.
