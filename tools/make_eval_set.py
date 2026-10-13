#!/usr/bin/env python3
"""Pick a held-out evaluation set and freeze it.

Sampled from the lines the transcriber *edited*. That is the opposite of what
it looks like it should be, and the reason is label provenance: every line was
prefilled by the previous model, so on a line accepted verbatim the ground
truth is that model's own output. Scoring a model against its own output is
circular, and it flatters whichever model did the prefilling.

An edited line is the only kind whose label we know a human wrote. The cost is
that edited lines are by construction the ones the model got wrong, so absolute
error on this set reads worse than error on real pages — it is a conservative
floor, and it is sound for comparing models.

The easy half of the distribution is measured separately with --verbatim, whose
labels carry the bias above and should be read as an optimistic bound.

    python3 tools/make_eval_set.py --per-book 60

Writes data/train/eval_fixed.list. Training must hold these out, so changing
this set means retraining before any comparison means anything.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "data" / "train"
VER = ROOT / "data" / "lines" / "verified"
MANIFEST = ROOT / "data" / "lines" / "human" / "manifest.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-book", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--verbatim", action="store_true",
                    help="sample accepted-verbatim lines instead (optimistic bound)")
    ap.add_argument("--out", default="eval_fixed.list")
    args = ap.parse_args()

    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    edited = {r["image"][:-4]: bool(r.get("edited")) for r in rows}
    book = {r["image"][:-4]: r["book"] for r in rows}
    pool = {p.name[:-7] for p in VER.glob("*.gt.txt")}

    want = (not args.verbatim)
    by = collections.defaultdict(list)
    for s in pool:
        if edited.get(s, False) == want:
            by[book.get(s, "?")].append(s)

    rng = random.Random(args.seed)
    picked: list[str] = []
    for b in sorted(by):
        lines = sorted(by[b])
        rng.shuffle(lines)
        take = lines[:args.per_book]
        picked += take
        flag = "  <- short" if len(take) < args.per_book else ""
        print(f"  {len(take):>4} of {len(lines):>5}   {b[:40]}{flag}")

    out = W / args.out
    out.write_text("\n".join(sorted(picked)) + "\n", encoding="utf-8")
    kind = "verbatim" if args.verbatim else "edited"
    print(f"\n  {len(picked)} held-out {kind} lines -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
