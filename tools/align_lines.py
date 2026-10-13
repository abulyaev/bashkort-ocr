#!/usr/bin/env python3
"""Generate line-image / text pairs from PDFs that already carry a text layer.

Tesseract training needs cropped line images paired with their exact text. Most
projects get those by paying humans to type. We can avoid most of that: 64 of
these books were scanned and OCR'd by ABBYY FineReader, and `pdftotext
-bbox-layout` hands back every line's text together with its bounding box. Crop
the box, pair it with the text, and a page yields ~30 training pairs for free.

    python3 tools/align_lines.py "texts/source/Юрғашты.pdf" --pages 60-64
    python3 tools/align_lines.py --all --limit 400        # sweep the corpus

**These pairs are ABBYY's output, not verified truth.** They are excellent bulk
training data — the model learns letterforms from real scans — but they inherit
whatever ABBYY got wrong, which for Bashkort is exactly the letters we care
about. They must never be used as the evaluation set. Evaluation needs the
human-transcribed lines from `tools/transcribe.py`, drawn from the books that
have no text layer at all.

Output is tesstrain's expected layout: `<name>.png` beside `<name>.gt.txt`.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DPI = 300
SCALE = DPI / 72.0          # PDF points -> pixels
PAD = 4                     # px of breathing room around each line
MIN_H, MAX_H = 12, 220      # plausible line heights in px
MIN_CHARS = 6

BASHKORT = re.compile(r"[а-яёәөүңһҙҫҡғА-ЯЁӘӨҮҢҺҘҪҠҒ]")


def page_lines(pdf: Path, page: int):
    """Yield (text, (x0, y0, x1, y1)) for each line on `page`, in PDF points."""
    out = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(page), "-l", str(page), "-q",
         str(pdf), "-"], capture_output=True, timeout=120).stdout
    if not out:
        return
    try:
        root = ET.fromstring(out.decode("utf-8", "ignore"))
    except ET.ParseError:
        return
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    for line in root.iter():
        if not line.tag.endswith("line"):
            continue
        words = [w.text or "" for w in line if w.tag.endswith("word")]
        text = unicodedata.normalize("NFC", " ".join(words)).strip()
        if not text:
            continue
        try:
            box = (float(line.get("xMin")), float(line.get("yMin")),
                   float(line.get("xMax")), float(line.get("yMax")))
        except (TypeError, ValueError):
            continue
        yield text, box


def usable(text: str) -> bool:
    if len(text) < MIN_CHARS:
        return False
    letters = BASHKORT.findall(text)
    if len(letters) < 0.5 * len(text.replace(" ", "")):
        return False        # mostly digits or punctuation — page furniture
    return True


def render(pdf: Path, page: int, td: Path) -> Path | None:
    pre = td / f"p{page}"
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI),
                    "-gray", "-png", str(pdf), str(pre)],
                   capture_output=True, timeout=300)
    got = sorted(td.glob(f"p{page}*.png"))
    return got[0] if got else None


def harvest(pdf: Path, pages, out: Path, prefix: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    made = 0
    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        for page in pages:
            lines = list(page_lines(pdf, page))
            if not lines:
                continue
            img_path = render(pdf, page, td)
            if not img_path:
                continue
            with Image.open(img_path) as im:
                im = im.convert("L")
                W, H = im.size
                for i, (text, (x0, y0, x1, y1)) in enumerate(lines):
                    if not usable(text):
                        continue
                    L = max(0, int(x0 * SCALE) - PAD)
                    T = max(0, int(y0 * SCALE) - PAD)
                    R = min(W, int(x1 * SCALE) + PAD)
                    B = min(H, int(y1 * SCALE) + PAD)
                    if R - L < 40 or not (MIN_H <= B - T <= MAX_H):
                        continue
                    stem = f"{prefix}_p{page:04d}_l{i:03d}"
                    im.crop((L, T, R, B)).save(out / f"{stem}.png")
                    (out / f"{stem}.gt.txt").write_text(text + "\n", encoding="utf-8")
                    made += 1
            img_path.unlink(missing_ok=True)
    return made


def slug(name: str) -> str:
    """ASCII filename stem, unique per book.

    NFKD leaves Cyrillic alone, so stripping non-ASCII collapsed every
    Cyrillic-titled book to the same stem and they silently overwrote each
    other — 15,600 pairs lost on the first sweep. Transliterating first gives
    readable, distinct stems; a hash suffix guarantees uniqueness even when two
    titles transliterate alike.
    """
    from bashlat import Transliterator
    latin = Transliterator().convert(name)
    s = re.sub(r"[^A-Za-z0-9]+", "-", unicodedata.normalize("NFKD", latin))
    s = re.sub(r"-+", "-", s).strip("-")[:36]
    h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
    return f"{s}-{h}" if s else h


def parse_pages(spec: str):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="?", help="a single PDF")
    ap.add_argument("--pages", help="e.g. 60-64 or 10,20,30 (1-based)")
    ap.add_argument("--all", action="store_true", help="sweep every book with a text layer")
    ap.add_argument("--limit", type=int, default=40, help="pages per book when sweeping")
    ap.add_argument("--out", default="data/lines/auto", help="output directory")
    args = ap.parse_args()

    out = ROOT / args.out
    total = 0

    if args.all:
        import json
        man = json.loads((ROOT / "texts/corpus/_manifest.json").read_text(encoding="utf-8"))
        books = [r for r in man if r["source"] == "text" and r["role"] == "corpus"
                 and r["pages"] and r["kept_chars"] > 50000]
        print(f"  {len(books)} books with a usable text layer")
        for r in books:
            pdf = ROOT / "texts/source" / r["file"]
            if pdf.suffix.lower() != ".pdf" or not pdf.exists():
                continue
            n = r["pages"]
            lo, hi = max(1, n // 10), max(2, n - n // 20)
            step = max(1, (hi - lo) // args.limit)
            pages = list(range(lo, hi, step))[:args.limit]
            made = harvest(pdf, pages, out, slug(pdf.stem))
            total += made
            print(f"    {r['file'][:44]:<46}{made:>6} lines", flush=True)
    else:
        if not args.pdf:
            ap.error("give a PDF or --all")
        pdf = Path(args.pdf)
        n = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True).stdout
                .decode("utf-8", "ignore").split("Pages:")[1].split()[0])
        pages = parse_pages(args.pages) if args.pages else list(range(1, min(n, 20) + 1))
        total = harvest(pdf, pages, out, slug(pdf.stem))

    print(f"\n  {total:,} line pairs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
