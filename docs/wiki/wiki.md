# wiki.py — deep dive

## Why this file exists

`wiki.py` turns CodeDNA annotations into two different artifacts:

- **Per-file Obsidian vault** under `docs/wiki/` — one markdown page per source file, with `[[wikilinks]]` derived from the `used_by:` and `related:` graphs
- **Project-level narrative wiki** at `docs/codedna-wiki.md` — a single file following the Karpathy LLM-wiki 7-section template (originally contributed by @workingfm in PR #2)

The two artifacts are complementary: the per-file vault is for navigation (humans in Obsidian, agents via the `wiki:` opt-in field), the project wiki is for onboarding (anyone entering the repo cold).

## Key invariants

- **Vault pages must NEVER be edited by hand above the `<!-- AGENT NOTES -->` marker**. Everything above is regenerated at each `codedna wiki bootstrap`. Durable notes go below the marker.
- **Obsidian wikilinks resolve by folder-relative path**: the vault mirrors the source tree (`codedna_tool/cli.py` → `docs/wiki/codedna_tool/cli.md`) and links use `[[codedna_tool/cli|cli.py]]`. Do NOT switch to a flat layout — duplicate basenames (multiple `__init__.py`) would collide.
- **Hashtags with numeric values (e.g. `#1072-1077`) MUST be wrapped in backticks** before rendering. Obsidian parses `#<digits>` as a tag and creates spurious nodes in the graph. `_escape_obsidian_hashtags` handles this.
- **The `wiki:` opt-in field is a signal, not a dump**. Generating a page for every file violates the "semantic model, not dump" principle from Karpathy's gist. The per-file vault is for humans; agents read wiki content only when the docstring explicitly points there via the `wiki:` field.

## Extension points

- **New renderer section** (e.g. "Summary", "Last touched") → add in `_page_markdown` between existing sections. Keep the order stable — agents rely on section positions for merges.
- **Custom vault layout** → modify `_slug_for_rel` and the `out_path` computation in `build_wiki_vault`. Update `_wikilink` to match.
- **New project-wiki sections** → edit `render_project_wiki` inline. Don't introduce a template engine; the 7 sections are load-bearing, not an abstraction seam.
- **LLM summaries** (not yet implemented) → add a `--summarize=topN` flag, select top-N files by importance heuristic (`len(used_by)` + `rules:` presence + agent history depth), call Haiku per file, inject a "Summary" section above "Exports".

## History notes for the next agent

- The original design was flat vault (all files at root, slug-based names). Switched to nested after realizing Obsidian's "relative path to file" link format handles duplicate basenames cleanly.
- The project-level `codedna-wiki.md` started as a root-level file (@workingfm's PR #2). Moved to `docs/` to keep the repo root clean. All relative paths inside need to be updated by one level (`.codedna` → `../.codedna`).
- Skill / sub-agent scaffolding from the original PR was removed — the project already has pre/post-commit hooks which are hard-enforced. Instructions in markdown files rely on the agent remembering to read them; hooks don't.

## Why wiki: appears here

The `wiki:` field in `wiki.py`'s own docstring points to this file. That's the pattern in action: *"if you're editing wiki.py, read this first"*. Future edits to the file should update this page (and vice versa).
