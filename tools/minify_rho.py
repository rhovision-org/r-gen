#!/usr/bin/env python3
"""Conservative Rholang minifier used only for size measurement.

Removes `//` comments and collapses whitespace outside string literals. It does not
rename identifiers or restructure terms.
"""

from __future__ import annotations


def strip_line_comment(line: str) -> str:
    out = []
    in_string = False
    escaped = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
                out.append(ch)
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def minify(text: str) -> str:
    parts = []
    for line in text.splitlines():
        clean = strip_line_comment(line).strip()
        if clean:
            parts.append(clean)
    # Join tokens with a space; trailing whitespace is harmless, missing separation is not.
    return " ".join(parts).strip()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    for name in sys.argv[1:]:
        print(minify(Path(name).read_text()))
