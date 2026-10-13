#!/usr/bin/env python3
"""Score models on the frozen held-out set, through the real tesseract pipeline.

Not lstmeval. lstmeval decodes the raw LSTM with no dictionary and has ranked
checkpoints wrongly here: it barely registers a word split, which costs one
character but two words, so a checkpoint that fragments `Гөлбәғиҙә` into
`Гөл бә ғи ҙ ә` can look fine to it and terrible to a user.

    python3 tools/eval_holdout.py bak_v3 bak_v4
    python3 tools/eval_holdout.py --per-book bak_v4

Reports CER, WER and recall for the nine non-Russian letters. ҫ is the one no
other Tesseract model can emit at all.
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VER = ROOT / "data" / "lines" / "verified"
EVAL = ROOT / "data" / "train" / "eval_fixed.list"
MANIFEST = ROOT / "data" / "lines" / "human" / "manifest.json"
LETTERS = "әөүңһҙҫҡғ"


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def ocr(model: str, img: Path) -> str:
    """psm 7 first, 13 as fallback: 7 returns nothing on crops with line bleed."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "o"
        for psm in ("7", "13"):
            subprocess.run(["tesseract", str(img), str(out), "-l", model,
                            "--psm", psm], capture_output=True)
            t = out.with_suffix(".txt")
            if t.exists():
                s = " ".join(unicodedata.normalize("NFC", t.read_text()).split())
                if s:
                    return s
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--per-book", action="store_true")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--list", default=None,
                    help="eval list to use (default eval_fixed.list)")
    args = ap.parse_args()

    book = {r["image"][:-4]: r["book"] for r in
            json.loads(MANIFEST.read_text(encoding="utf-8"))}
    pairs = []
    src = (ROOT / "data" / "train" / args.list) if args.list else EVAL
    for s in (l.strip() for l in src.read_text().splitlines()):
        img, gt = VER / f"{s}.png", VER / f"{s}.gt.txt"
        if img.exists() and gt.exists():
            pairs.append((img, unicodedata.normalize("NFC", gt.read_text()).strip(),
                          book.get(s, "?")))
    print(f"held-out lines: {len(pairs)}\n")

    for model in args.models:
        with ThreadPoolExecutor(args.jobs) as ex:
            got = list(ex.map(lambda p: ocr(model, p[0]), pairs))
        ce = ct = we = wt = 0
        hit = {c: [0, 0] for c in LETTERS}
        per = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
        for (img, truth, bk), pred in zip(pairs, got):
            c, t = lev(truth, pred), len(truth)
            tw, pw = truth.split(), pred.split()
            w, n = lev(tw, pw), len(tw)
            ce += c; ct += t; we += w; wt += n
            a = per[bk[:32]]
            a[0] += c; a[1] += t; a[2] += w; a[3] += n; a[4] += 1
            for ch in LETTERS:
                k = truth.count(ch)
                if k:
                    hit[ch][1] += k
                    hit[ch][0] += min(k, pred.count(ch))
        print(f"  {model}")
        print(f"    CER {100*ce/max(ct,1):5.2f}%   WER {100*we/max(wt,1):5.2f}%")
        print("    " + "  ".join(f"{c} {100*v[0]/v[1]:3.0f}%" if v[1] else f"{c}   -"
                                 for c, v in hit.items()))
        if args.per_book:
            print()
            for k, v in sorted(per.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
                print(f"      {k:<34}{v[4]:>4}{100*v[0]/max(v[1],1):>8.2f}%"
                      f"{100*v[2]/max(v[3],1):>8.2f}%")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
