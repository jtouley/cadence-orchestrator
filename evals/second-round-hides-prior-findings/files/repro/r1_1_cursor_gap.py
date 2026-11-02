"""Repro for R1-1. Usage: python repro/r1_1_cursor_gap.py <path to the repo clone>
Exit 1 and print REPRODUCES if paging through results skips or repeats a row; exit 0 otherwise."""
import sys

sys.path.insert(0, sys.argv[1])
from notes.store import connect, add_note  # noqa: E402
from notes.search import search  # noqa: E402

db = connect()
for i in range(7):
    add_note(db, f"note {i}", "", f"2026-10-0{i + 1}")
seen, token = [], None
while True:
    rows, token = search(db, "note", page_size=3, page_token=token)
    seen += [r["id"] for r in rows]
    if not token:
        break
if sorted(seen) != list(range(1, 8)):
    print(f"REPRODUCES: ids returned {seen}, expected each of 1..7 once")
    sys.exit(1)
print("does not reproduce")
