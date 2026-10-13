#!/usr/bin/env python3
"""Pre-fill candidate transcriptions using the trained bak model.

Measured at 5.9% character error on Драматургия — about two characters to fix
per line, with roughly a third of lines already exact. Far better than a blank
box, and it runs over thousands of lines in minutes.

    python3 tools/autofill.py --book ДРАМАТУРГИЯ
    python3 tools/autofill.py --all --model bak_v3

Only touches lines that are unanswered and have no candidate. Never overwrites
saved text.
"""
import argparse, json, subprocess, sys, unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
M = ROOT/"data/lines/human/manifest.json"
IM = ROOT/"data/lines/human/images"

ap = argparse.ArgumentParser()
ap.add_argument("--book", default="")
ap.add_argument("--model", default="bak_v4")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--no-correct", action="store_true")
a = ap.parse_args()

rows = json.loads(M.read_text(encoding="utf-8"))
todo = [r for r in rows
        if r.get("text") is None and not (r.get("suggestion") or "").strip()
        and a.book.lower() in r["book"].lower() and (IM/r["image"]).exists()]
if a.limit: todo = todo[:a.limit]
print(f"  {len(todo):,} lines to fill with {a.model}", flush=True)

corr = None
if not a.no_correct:
    from bashlat.correct import Corrector
    p = ROOT/"data/models/corrector.json"
    if p.exists(): corr = Corrector.load(p)

for n, r in enumerate(todo, 1):
    # psm 7 assumes one clean baseline and returns nothing when a crop carries
    # bleed from the neighbouring line; psm 13 skips that analysis and reads
    # anyway. Falling back recovers lines that otherwise get no candidate.
    text = ""
    for psm in ("7", "13"):
        out = subprocess.run(["tesseract", str(IM/r["image"]), "stdout",
                              "-l", a.model, "--psm", psm],
                             capture_output=True).stdout.decode("utf-8", "ignore")
        text = " ".join(unicodedata.normalize("NFC", out).split())
        if text:
            break
    if corr and text: text = corr.correct(text)
    r["suggestion"] = text
    if n % 50 == 0 or n == len(todo):
        # Re-read before writing: the transcription server writes this same
        # file on every save. Writing back a copy loaded minutes ago silently
        # discards whatever was typed meanwhile — and discards our own work if
        # the server writes last.
        cur = json.loads(M.read_text(encoding="utf-8"))
        idx = {x["image"]: k for k, x in enumerate(cur)}
        for done_row in todo[:n]:
            k = idx.get(done_row["image"])
            if k is None:
                continue
            if cur[k].get("text") is None and not (cur[k].get("suggestion") or "").strip():
                cur[k]["suggestion"] = done_row["suggestion"]
        M.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"    {n:,}/{len(todo):,}", flush=True)
print(f"  done — {len(todo):,} candidates written")
