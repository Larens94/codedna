# cli.py — deep dive

## Why this file exists

`cli.py` is the protocol translator: it reads source files, builds the structural graph (`used_by`), and writes CodeDNA docstrings back. Everything else (language adapters, validators, runners) depends on its parse/rebuild invariants.

## Key invariants

- `_parse_existing_docstring` MUST recognize every optional field (`related:`, `wiki:`, `message:`) — missing a field means `refresh` strips it silently.
- `_rebuild_docstring` preserves field ORDER: `exports → used_by → related → wiki → rules → agent → message`. Reviewers have called out order inversions as bugs.
- `--no-llm` is a first-class mode: EVERY code path must be callable without API keys. Tests run with `--no-llm`.

## Extension points

- New optional field → add to tuple in `_parse_existing_docstring` AND `_rebuild_docstring` AND `_parse_lang_header` AND `_rebuild_lang_header`. Four places. No shortcuts — tried to unify them and broke Blade.
- New language → write `languages/<lang>.py` adapter, register in `languages/__init__.py`. Do NOT add language-specific branches in `cli.py`.

## History notes for the next agent

The parser currently treats unknown fields as continuation lines of the previous field. If you add `wiki:` but forget to register it, its path will end up appended to `related:`, silently.
