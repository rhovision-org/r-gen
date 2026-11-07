#!/usr/bin/env python3
"""Heuristic scanner for Rholang `if`/`match` control flow.

This is not a parser. It tracks brace depth, finds `match` blocks, extracts their arm
patterns, and classifies a catch-all arm (`_` or a lone identifier). The pinned-node
semantics are in `docs/src/reference/rholang-style.md`: an unmatched `match` is silent
success with no continuation, so a mutating match without a catch-all is a state-loss bug.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_ROOT = ROOT / "contracts" / "src"
FILES = sorted(CONTRACT_ROOT.rglob("*.rho"))

MATCH_RE = re.compile(r"\bmatch\b")
IF_RE = re.compile(r"\bif\s*\(")
ARM_RE = re.compile(r"^(.*?)=>(.*)$", re.S)
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
LITERAL_WORDS = {"true", "false", "Nil"}


def total_tuple_bind(pattern: str) -> bool:
    """A single tuple of plain binders matches every target of that arity, including Nil
    entries produced by `.get`. This is a total bind, not a business catch-all."""
    text = pattern.strip()
    if not (text.startswith("(") and text.endswith(")")):
        return False
    inner = text[1:-1].strip()
    if not inner:
        return True
    parts = [part.strip() for part in inner.split(",") if part.strip()]
    return bool(parts) and all(
        (part == "_" or IDENT_RE.match(part)) and part not in LITERAL_WORDS
        for part in parts
    )


@dataclass
class Construct:
    file: str
    line: int
    kind: str
    arm: str
    depth: int
    text: str
    patterns: list[str] = field(default_factory=list)
    catch_all: bool = False
    mutating: bool = False
    map_pattern_without_rest: bool = False


def strip_comment(line: str) -> str:
    # Rholang line comments. This is deliberately simple; strings containing // are rare in
    # the core and the scanner only needs the control-flow keywords.
    return line.split("//", 1)[0]


def brace_delta(line: str) -> int:
    # Ignore braces inside quoted strings for the common cases.
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    return text.count("{") - text.count("}")


def match_block(lines: list[str], start: int) -> tuple[int, str]:
    depth = 0
    seen = False
    block: list[str] = []
    for index in range(start, len(lines)):
        line = strip_comment(lines[index])
        block.append(line.rstrip())
        depth += brace_delta(line)
        if "{" in line:
            seen = True
        if seen and depth <= 0:
            return index, "\n".join(block)
    return len(lines) - 1, "\n".join(block)


def enclosing_arm(lines: list[str], line: int) -> str:
    for index in range(line, -1, -1):
        if "contract " in lines[index] or "def " in lines[index]:
            return lines[index].strip()
    return "?"


def mutating_before(lines: list[str], line: int) -> bool:
    start = max(0, line - 120)
    text = "\n".join(strip_comment(item) for item in lines[start:line])
    has_consume = bool(re.search(r"for\s*\([^)]*<-\s*", text)) and "<-" in text
    has_repost = "State!({" in text or "state!({" in text or re.search(r"\b\w+State!\(", text)
    return has_consume or bool(has_repost)


def line_labels(code: str) -> list[str]:
    """Label each opening brace on a line. Only if/match/for count toward lexical depth;
    new/contract/other are frames but not dispatch nesting."""
    opens = code.count("{")
    if opens == 0:
        return []
    first = "other"
    if MATCH_RE.search(code):
        first = "match"
    elif "for " in code and "(" in code:
        first = "for"
    elif IF_RE.search(code):
        first = "if"
    elif "contract " in code:
        first = "contract"
    elif "new " in code:
        first = "new"
    return [first] + ["other"] * (opens - 1)


def lexical_depth(stack: list[str]) -> int:
    """Depth of if/match/for inside the most recent contract body. A contract definition
    resets the count; nested contracts are common in these deploy terms."""
    start = 0
    for index, label in enumerate(stack):
        if label == "contract":
            start = index + 1
    return sum(1 for label in stack[start:] if label in ("if", "match", "for"))


def scan_file(path: Path) -> tuple[list[Construct], int, int]:
    rel = str(path.relative_to(ROOT))
    lines = path.read_text().splitlines()
    constructs: list[Construct] = []
    stack: list[str] = []
    if_count = 0
    match_count = 0
    index = 0
    while index < len(lines):
        raw = lines[index]
        code = strip_comment(raw)
        depth = lexical_depth(stack)
        if MATCH_RE.search(code):
            match_count += 1
            end, block = match_block(lines, index)
            arm_text = block.split("{", 1)[1] if "{" in block else block
            arm_entries: list[tuple[int, str]] = []
            for arm_line in arm_text.splitlines():
                stripped = arm_line.strip()
                if "=>" not in stripped:
                    continue
                pattern = stripped.split("=>", 1)[0].strip().rstrip(",").strip()
                if pattern and pattern not in ("{", "}"):
                    indent = len(arm_line) - len(arm_line.lstrip())
                    arm_entries.append((indent, pattern))
            # Only the outermost arms dispatch this match; nested match arms are deeper.
            min_indent = min((indent for indent, _ in arm_entries), default=0)
            patterns = [pattern for indent, pattern in arm_entries if indent == min_indent]
            catch_all = any(
                pattern == "_" or IDENT_RE.match(pattern) or total_tuple_bind(pattern)
                for pattern in patterns
            )
            map_without_rest = any(
                "{" in pattern and "..." not in pattern for pattern in patterns
            )
            constructs.append(Construct(
                file=rel,
                line=index + 1,
                kind="match",
                arm=enclosing_arm(lines, index),
                depth=depth,
                text=code.strip(),
                patterns=patterns,
                catch_all=catch_all,
                mutating=mutating_before(lines, index),
                map_pattern_without_rest=map_without_rest,
            ))
        for if_match in IF_RE.finditer(code):
            if_count += 1
            constructs.append(Construct(
                file=rel,
                line=index + 1,
                kind="if",
                arm=enclosing_arm(lines, index),
                depth=depth,
                text=code.strip(),
            ))
        for label in line_labels(code):
            stack.append(label)
        for _ in range(code.count("}")):
            if stack:
                stack.pop()
        index += 1
    return constructs, if_count, match_count


def scan() -> list[Construct]:
    constructs: list[Construct] = []
    for path in FILES:
        found, _, _ = scan_file(path)
        constructs.extend(found)
    return constructs


def scan_with_counts() -> list[tuple[Path, list[Construct], int, int]]:
    out = []
    for path in FILES:
        found, if_count, match_count = scan_file(path)
        out.append((path, found, if_count, match_count))
    return out
