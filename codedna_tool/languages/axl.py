"""axl.py — Native CodeDNA frame adapter for AXL source files.

exports: _VERSION_RE | _FRAME_RE | _DECLARATION_RE | _KIND_ALIASES | class AxlAnnotation | parse_axl_annotations(source) | class AxlAdapter
used_by: codedna_tool/languages/__init__.py → AxlAdapter
         tests/test_language_adapters.py → parse_axl_annotations
related: codedna_tool/languages/base.py — defines native annotation extension points
rules:   AXL CodeDNA metadata is executable-grammar data, never a comment or sidecar.
Module frames must appear immediately after the numeric version line.
Refresh may replace only module export/used_by frames; symbol frames must remain byte-identical.
Frame values must be JSON-quoted when generated so pipes, quotes, and backslashes round-trip safely.
agent:   gpt-5 | openai | 2026-08-21 | s_20260821_axl | implemented native AXL CodeDNA frame parsing and injection
message: "AX-IR propagation remains a compiler responsibility because the AXL compiler is not present in this repository"
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .base import LangFileInfo, LanguageAdapter


_VERSION_RE = re.compile(r"^\s*\d+\s*;\s*$")
_FRAME_RE = re.compile(r"^\s*(8[0-6])\|(.*);\s*$")
_DECLARATION_RE = re.compile(r"^\s*40\|([^|;]+)\|")
_KIND_ALIASES = {
    "m": "module",
    "e": "export",
    "u": "used_by",
    "r": "related",
    "c": "rule",
}


@dataclass(frozen=True)
class AxlAnnotation:
    """Structured non-runtime AXL annotation frame.

    Rules:   fields exclude the numeric opcode and retain decoded field order.
             line is one-based so diagnostics can point to canonical source.
    """

    opcode: int
    kind: str
    fields: tuple[str, ...]
    line: int


def _decode_frame(line: str, line_number: int) -> AxlAnnotation | None:
    """Decode one opcode 80–86 frame without interpreting program frames.

    Rules:   Quoted pipes, quotes, and backslashes must survive parsing.
             Malformed or non-annotation lines return None instead of raising.
    """
    match = _FRAME_RE.match(line)
    if not match:
        return None
    try:
        values = next(csv.reader([match.group(2)], delimiter="|", quotechar='"', escapechar="\\"))
    except (csv.Error, StopIteration):
        return None
    if not values:
        return None
    kind = _KIND_ALIASES.get(values[0].strip(), values[0].strip())
    return AxlAnnotation(int(match.group(1)), kind, tuple(value.strip() for value in values[1:]), line_number)


def parse_axl_annotations(source: str) -> list[AxlAnnotation]:
    """Return every native CodeDNA frame while preserving source order.

    Rules:   Scan the full source because symbol annotations live beside declarations,
             not only in the module block after the version frame.
    """
    annotations = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        annotation = _decode_frame(line, line_number)
        if annotation is not None:
            annotations.append(annotation)
    return annotations


def _quoted(value: str) -> str:
    """Encode a frame value with deterministic JSON string escaping.

    Rules:   JSON quoting is a strict subset suitable for the proposed AXL frame grammar.
    """
    return json.dumps(value, ensure_ascii=False)


def _export_names(value: str) -> list[str]:
    """Extract stable symbol names from CodeDNA's formatted export list.

    Rules:   Ignore truncation markers and preserve first-seen order.
    """
    names = []
    for item in value.split(" | "):
        token = item.strip()
        if not token or token == "none" or token.startswith("(+"):
            continue
        name = re.split(r"[(:\s]", token, maxsplit=1)[0]
        if name and name not in names:
            names.append(name)
    return names


class AxlAdapter(LanguageAdapter):
    """CodeDNA adapter for native `.axl` annotation frames.

    Rules:   Never generate comments. Reject injection when no numeric version line exists.
             Opcode 40 is the only declaration form inferred here because it is the only
             public symbol frame specified by the supplied AXL proposal.
    """

    @property
    def comment_prefix(self) -> str:
        """Return an empty prefix because AXL annotations are native frames.

        Rules:   Callers must use parse_codedna_fields() before comment-based fallbacks.
        """
        return ""

    def has_codedna_header(self, source: str) -> bool:
        """Report whether the source contains a native module identity frame.

        Rules:   Symbol-only frames do not constitute the required module annotation block.
        """
        return any(annotation.opcode == 80 and annotation.kind == "module"
                   for annotation in parse_axl_annotations(source))

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Extract declared public symbols and native annotation state.

        Rules:   Must never raise. Opcode 40 declarations are structural truth when present;
                 otherwise existing opcode 81 export frames provide the best available result.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)
        if not any(_VERSION_RE.match(line) for line in source.splitlines()):
            return LangFileInfo(path=path, rel=rel, parseable=False)

        declarations = []
        for line in source.splitlines():
            match = _DECLARATION_RE.match(line)
            if match:
                name = match.group(1).strip()
                if name and name not in declarations:
                    declarations.append(name)
        framed_exports = [annotation.fields[0] for annotation in parse_axl_annotations(source)
                          if annotation.opcode == 81 and annotation.kind == "export" and annotation.fields]
        return LangFileInfo(
            path=path,
            rel=rel,
            exports=declarations or framed_exports,
            deps=[],
            has_codedna=self.has_codedna_header(source),
        )

    def parse_codedna_fields(self, source: str) -> dict[str, str] | None:
        """Map native frames to CodeDNA's canonical logical fields.

        Rules:   Module and symbol rules are both exposed; callers needing scope inspect
                 parse_axl_annotations() directly. Return None without an opcode 80 module frame.
        """
        annotations = parse_axl_annotations(source)
        if not any(item.opcode == 80 and item.kind == "module" for item in annotations):
            return None
        fields: dict[str, list[str]] = {
            "exports": [], "used_by": [], "related": [], "rules": [], "agent": [], "message": []
        }
        for item in annotations:
            if item.opcode == 81 and item.kind == "export" and item.fields:
                fields["exports"].append(item.fields[0])
            elif item.opcode == 82 and item.kind == "used_by" and item.fields:
                fields["used_by"].append(item.fields[-1])
            elif item.opcode == 83 and item.kind == "related" and item.fields:
                fields["related"].append(item.fields[-1])
            elif item.opcode == 84 and item.kind in {"rule", "constraint"} and item.fields:
                rule_value = (
                    item.fields[-2]
                    if item.fields[-1] in {"human", "agent", "derived"}
                    else item.fields[-1]
                )
                fields["rules"].append(rule_value)
            elif item.opcode == 85 and item.kind in {"agent", "message"} and item.fields:
                fields[item.kind].append(" | ".join(item.fields))
        return {key: " | ".join(values) if values else "none" for key, values in fields.items()}

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Insert native module frames immediately after the AXL version line.

        Rules:   Must be idempotent and must return malformed/versionless input unchanged.
                 Generated frames are non-runtime grammar nodes terminated by semicolons.
        """
        if self.has_codedna_header(source):
            return source
        lines = source.splitlines(keepends=True)
        version_index = next((index for index, line in enumerate(lines) if _VERSION_RE.match(line)), None)
        if version_index is None:
            return source
        module_name = str(Path(rel).with_suffix("")).replace("/", ".").replace("\\", ".")
        frames = [f"80|module|{module_name}|{_quoted(Path(rel).stem + ' module')};\n"]
        for name in _export_names(exports):
            frames.append(f"81|export|{name}|{_quoted(name)};\n")
        if used_by != "none":
            for caller in used_by.splitlines():
                frames.append(f"82|used_by|{_quoted(caller.strip())};\n")
        frames.append(f"84|rule|{_quoted(rules)}|derived;\n")
        provider = self._detect_provider(model_id)
        narrative = f"{model_id} | {provider} | {today} | codedna-cli | initial CodeDNA annotation pass"
        frames.append(f"85|agent|{_quoted(narrative)};\n")
        frames.append("\n")
        return "".join([*lines[:version_index + 1], *frames, *lines[version_index + 1:]])

    def refresh_header(self, source: str, exports: str, used_by: str) -> str | None:
        """Replace module export/used_by frames while preserving all other frames.

        Rules:   Only the contiguous annotation block after the version line is mutable.
                 Symbol-level frames elsewhere in the file must remain byte-identical.
        """
        lines = source.splitlines(keepends=True)
        version_index = next((index for index, line in enumerate(lines) if _VERSION_RE.match(line)), None)
        if version_index is None:
            return None
        block_start = version_index + 1
        block_end = block_start
        while block_end < len(lines):
            stripped = lines[block_end].strip()
            if not stripped:
                block_end += 1
                continue
            annotation = _decode_frame(lines[block_end], block_end + 1)
            if annotation is None:
                break
            block_end += 1
        block = lines[block_start:block_end]
        if not any((_decode_frame(line, 0) or AxlAnnotation(0, "", (), 0)).opcode == 80 for line in block):
            return None
        preserved = []
        for line in block:
            annotation = _decode_frame(line, 0)
            if annotation and annotation.opcode in {81, 82}:
                continue
            preserved.append(line)
        insertion_index = next(
            (index + 1 for index, line in enumerate(preserved)
             if (annotation := _decode_frame(line, 0)) and annotation.opcode == 80),
            0,
        )
        generated = [f"81|export|{name}|{_quoted(name)};\n" for name in _export_names(exports)]
        if used_by != "none":
            generated.extend(f"82|used_by|{_quoted(caller.strip())};\n" for caller in used_by.splitlines())
        refreshed = [*preserved[:insertion_index], *generated, *preserved[insertion_index:]]
        return "".join([*lines[:block_start], *refreshed, *lines[block_end:]])

    def inject_symbol_rule(self, source: str, target: str, rule: str, origin: str = "agent") -> str:
        """Insert a native rule frame directly before an opcode 40 declaration.

        Rules:   target must exist exactly once; origin is human, agent, or derived;
                 duplicate target/rule pairs are idempotent; unresolved targets leave source unchanged.
        """
        if origin not in {"human", "agent", "derived"}:
            raise ValueError("origin must be human, agent, or derived")
        existing = parse_axl_annotations(source)
        if any(item.opcode == 84 and target in item.fields and rule in item.fields for item in existing):
            return source
        lines = source.splitlines(keepends=True)
        matches = [index for index, line in enumerate(lines)
                   if (match := _DECLARATION_RE.match(line)) and match.group(1).strip() == target]
        if len(matches) != 1:
            return source
        frame = f"84|rule|{target}|{_quoted(rule)}|{origin};\n"
        lines.insert(matches[0], frame)
        return "".join(lines)
