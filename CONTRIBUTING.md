# Contributing to CodeDNA

Thank you for your interest in contributing! CodeDNA is a language-adaptable in-source communication protocol, so contributions from any ecosystem are welcome.

## Ways to Contribute

- **Add examples** in a new language (`examples/<language>/`)
- **Improve the spec** — open an issue to discuss first
- **Run and share benchmarks** — submit your results
- **Report bugs** in the spec or examples

## Adding a Language Example

1. Create a folder: `examples/<language>/`
2. Add at least one file demonstrating proper CodeDNA annotations (v0.9 format)
3. Add a short `README.md` in that folder explaining the annotation style
4. Open a PR with the title: `feat(examples): add <language> example`

## Spec Changes

The spec (`SPEC.md`) is versioned. Any change to required fields or placement rules requires:
1. An issue discussing the change
2. A version bump
3. An update to `CHANGELOG.md`

## Code of Conduct

Be respectful. This project welcomes contributors of all backgrounds and experience levels.

## PR Checklist

- [ ] Example files use valid CodeDNA v0.9 annotations (module docstring format)
- [ ] Annotations are accurate and consistent with the code
- [ ] A brief description of the change is included in the PR body
