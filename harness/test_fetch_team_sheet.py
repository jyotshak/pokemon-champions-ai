"""Regression test for harness/fetch_team_sheet.py::_normalize_line_endings
(2026-07-19 CRLF-doubling bug: a naive .replace("\r\n","\n").replace("\r","\n")
chain turns an already-doubled "\r\r\n" into a blank line instead of
collapsing it, corrupting every scraped team paste into 50+ bogus
fragments). Pure function, no network needed.

Run from the project root: python -m harness.test_fetch_team_sheet
"""

from harness.fetch_team_sheet import _normalize_line_endings

failures = []


def check(name: str, actual, expected):
    ok = actual == expected
    print(f"  {name}: {actual!r} expected {expected!r} [{'ok' if ok else 'MISMATCH'}]")
    if not ok:
        failures.append(name)


print("normal single CRLF collapses to a bare newline")
check("single CRLF", _normalize_line_endings("a\r\nb\r\n"), "a\nb\n")

print("\nalready-doubled CRLF (the exact corruption found live) collapses to ONE newline, not two")
check("doubled CRLF", _normalize_line_endings("a\r\r\nb\r\r\n"), "a\nb\n")

print("\nlone CR (old Mac style) also collapses correctly")
check("lone CR", _normalize_line_endings("a\rb\r"), "a\nb\n")

print("\nalready-clean LF-only text is left untouched")
check("already clean", _normalize_line_endings("a\nb\n"), "a\nb\n")

print("\nmixed content (blank-line mon separators must survive as exactly one blank line)")
check("blank line preserved", _normalize_line_endings("a\r\n\r\nb\r\n"), "a\n\nb\n")

print(f"\n{'PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
