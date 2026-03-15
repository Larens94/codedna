# Contributing to Beacon Framework

Thank you for your interest in contributing! Beacon is a language-agnostic standard, so contributions from any ecosystem are welcome.

## Ways to Contribute

- **Add examples** in a new language (`examples/<language>/`)
- **Improve the spec** — open an issue to discuss first
- **Run and share benchmarks** — submit your results
- **Report bugs** in the spec or examples

## Adding a Language Example

1. Create a folder: `examples/<language>/`
2. Add at least one file demonstrating a proper Beacon Header
3. Add a short `README.md` in that folder explaining the header style
4. Open a PR with the title: `feat(examples): add <language> example`

## Spec Changes

The spec (`SPEC.md`) is versioned. Any change to required fields or placement rules requires:
1. An issue discussing the change
2. A version bump
3. An update to the Changelog section in `SPEC.md`

## Code of Conduct

Be respectful. This project welcomes contributors of all backgrounds and experience levels.

## PR Checklist

- [ ] Example files have a valid Beacon Header
- [ ] `LAST_MODIFIED` is not left empty
- [ ] `FILE` field matches the actual filename
- [ ] A brief description of the change is included in the PR body
