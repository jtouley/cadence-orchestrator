"""Repro for R1-2. Usage: python repro/r1_2_like_wildcard.py <path to the repo clone>
Exit 1 and print REPRODUCES if a search for "100%" matches a title without a literal "100%"; exit 0 otherwise."""

import sys

sys.path.insert(0, sys.argv[1])
from notes.search import search  # noqa: E402
from notes.store import add_note, connect  # noqa: E402

db = connect()
add_note(db, "100% done", "", "2026-10-01")
add_note(db, "1000 done", "", "2026-10-02")
rows, _ = search(db, "100%")
titles = [r["title"] for r in rows]
if titles != ["100% done"]:
    print(f"REPRODUCES: search('100%') returned {titles}")
    sys.exit(1)
print("does not reproduce")
