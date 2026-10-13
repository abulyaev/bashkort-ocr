#!/usr/bin/env python3
"""Read a scanned Bashkort book: Surya OCR, then restore the letters it loses.

Surya recovers ә ө ү һ ғ but not ҙ ҫ ҡ, and returns ң unreliably. The corrector
puts those back. Neither half is much use alone.

    python3 tools/ocr.py "texts/source/Ҡара яу.pdf" --pages 40-44
    python3 tools/ocr.py page.png --raw          # skip correction, see what Surya gave
    python3 tools/ocr.py book.pdf --pages 10-12 --out read.txt

Needs the Surya environment:
    brew install llama.cpp
    uv venv --python 3.12 .venv-ocr
    VIRTUAL_ENV=.venv-ocr uv pip install surya-ocr
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SURYA = ROOT / ".venv-ocr" / "bin" / "surya_ocr"
MODEL = ROOT / "data" / "models" / "corrector.json"
TAGS = re.compile(r"<[^>]+>")

BASH_ONLY = set("ҙҫҡғҘҪҠҒ")
TURKIC = set("әөүңһӘӨҮҢҺ")


def harvest(obj, depth=0):
    """Pull every string out of Surya's JSON, whatever shape this version uses."""
    if depth > 8:
        return []
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, list):
        return [s for o in obj for s in harvest(o, depth + 1)]
    if isinstance(obj, dict):
        out = []
        for k in ("text", "html", "markdown", "text_lines", "blocks", "lines"):
            if k in obj:
                out += harvest(obj[k], depth + 1)
        if not out:                       # unknown shape: walk everything
            for v in obj.values():
                out += harvest(v, depth + 1)
        return out
    return []


def run_surya(path: Path, pages: str | None) -> str:
    if not SURYA.exists():
        sys.exit(f"Surya not installed at {SURYA}\nSee the header of this file.")
    with tempfile.TemporaryDirectory() as td:
        cmd = [str(SURYA), str(path), "--output_dir", td]
        if pages:
            cmd += ["--page_range", pages]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr.decode("utf-8", "ignore")[-1500:])
            sys.exit(f"surya_ocr failed ({proc.returncode})")
        texts = []
        for js in sorted(Path(td).rglob("*.json")):
            try:
                texts += harvest(json.loads(js.read_text(encoding="utf-8")))
            except Exception:
                pass
    return TAGS.sub(" ", "\n".join(texts))


def letter_stats(text: str, label: str) -> None:
    cyr = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    b = sum(1 for c in text if c in BASH_ONLY)
    t = sum(1 for c in text if c in TURKIC)
    sys.stderr.write(f"  {label:<12} {len(text):>7,} chars  {cyr:>6,} cyrillic  "
                     f"ҙҫҡғ={b:<5} әөүңһ={t}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="PDF or image")
    ap.add_argument("--pages", help="page range, e.g. 40-44 or 0,5-10 (0-based)")
    ap.add_argument("--raw", action="store_true", help="skip correction")
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--report", type=int, nargs="?", const=30, default=0,
                    metavar="N", help="list the first N corrections")
    args = ap.parse_args()

    raw = run_surya(Path(args.input), args.pages)
    if not raw.strip():
        sys.exit("Surya returned no text.")
    letter_stats(raw, "surya")

    text = raw
    if not args.raw:
        if not MODEL.exists():
            sys.exit(f"No corrector at {MODEL}. Build the corpus and train it first.")
        from bashlat.correct import Corrector
        text, changes = Corrector.load(MODEL).correct_verbose(raw)
        letter_stats(text, "corrected")
        sys.stderr.write(f"  {len(changes):,} correction(s)\n")
        for ch in changes[:args.report]:
            sys.stderr.write(f"     {ch}\n")

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        sys.stderr.write(f"  -> {args.out}\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
