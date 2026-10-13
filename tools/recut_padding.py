#!/usr/bin/env python3
"""Re-cut one book's line crops with padding proportional to line height.

The original cropper used a fixed 6px vertical pad. Surya's boxes hug the
x-height, so 6px does not clear a descender — and in Bashkort the descender is
the *only* thing distinguishing ҙ ҫ ҡ ғ ң from з с к г н. A clipped crop
therefore removes exactly the evidence the model exists to learn, while the
transcriber can still read the line from context and writes the correct letter.
The label then asserts a stroke the image does not contain.

Severity scaled with the book's typography: 6px is 11% of a 55px line but only
6% of a 94px one, which is why some books were barely affected and others lost
two thirds of their crops.

Padding here is a fraction of the page's median line height, so it adapts.

    python3 tools/recut_padding.py --book "Башҡорт халыҡ әкиәттәре"

New crops are added with a `-p` suffix. Old crops are moved to quarantine and
their rows marked `clipped` — transcriptions are preserved, not deleted, so the
decision about whether to trust them can be made later.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SURYA = ROOT / ".venv-ocr" / "bin" / "surya_detect"
MANIFEST = ROOT / "data" / "lines" / "human" / "manifest.json"
IMAGES = ROOT / "data" / "lines" / "human" / "images"
QUAR = ROOT / "data" / "lines" / "human" / "quarantine"
DPI = 300
PAD_X = 8
PAD_FRAC = 0.42          # of median line height
MIN_W, MIN_H, MAX_H = 60, 14, 400


def sh(cmd, timeout=900):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mine = [r for r in rows if args.book.lower() in r["book"].lower()]
    if not mine:
        sys.exit(f"no rows for {args.book}")
    book = mine[0]["book"]
    pdf = ROOT / "texts/source" / book
    if not pdf.exists():
        sys.exit(f"pdf not found: {pdf}")
    pages = sorted({r["page"] for r in mine})
    stem = mine[0]["image"].rsplit("_p", 1)[0]
    print(f"  {book}")
    print(f"  {len(mine)} existing crops across {len(pages)} pages")
    print(f"  transcribed: {sum(1 for r in mine if (r.get('text') or '').strip())}\n")
    if args.dry_run:
        return 0

    QUAR.mkdir(exist_ok=True)
    added = 0
    new_rows = []

    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        for page in pages:
            out = td / f"d{page}"
            sh([str(SURYA), str(pdf), "--page_range", str(page - 1),
                "--output_dir", str(out)])
            js = list(out.rglob("*.json"))
            if not js:
                continue
            data = json.loads(js[0].read_text(encoding="utf-8"))
            plist = list(data.values())[0]
            if not plist:
                continue
            p = plist[0]
            fw, fh = p["image_bbox"][2], p["image_bbox"][3]
            boxes = [b["bbox"] for b in p.get("bboxes", [])]
            if not boxes:
                continue

            sh(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI),
                "-gray", "-png", str(pdf), str(td / f"pg{page}")])
            imgs = sorted(td.glob(f"pg{page}*.png"))
            if not imgs:
                continue

            with Image.open(imgs[0]) as im:
                im = im.convert("L")
                W, H = im.size
                sx, sy = W / fw, H / fh
                scaled = [(b[0]*sx, b[1]*sy, b[2]*sx, b[3]*sy) for b in boxes]
                med = statistics.median([b[3]-b[1] for b in scaled]) or 40
                pad_y = max(10, int(med * PAD_FRAC))
                scaled.sort(key=lambda b: (round(b[1] / (med * 0.6)), b[0]))
                for i, b in enumerate(scaled):
                    L = max(0, int(b[0]) - PAD_X); T = max(0, int(b[1]) - pad_y)
                    R = min(W, int(b[2]) + PAD_X); B = min(H, int(b[3]) + pad_y)
                    if R - L < MIN_W or not (MIN_H <= B - T <= MAX_H):
                        continue
                    name = f"{stem}_p{page:04d}_l{i:03d}-p.png"
                    im.crop((L, T, R, B)).save(IMAGES / name)
                    new_rows.append({"image": name, "book": book, "page": page,
                                     "suggestion": "", "page_text": "",
                                     "text": None, "edited": None})
                    added += 1
            for f in td.glob(f"pg{page}*.png"):
                f.unlink(missing_ok=True)
            print(f"    p{page}: pad_y={pad_y}px (median line {med:.0f}px), "
                  f"{added} crops so far", flush=True)

    # retire the clipped originals, keeping their labels for reference
    retired = 0
    for r in rows:
        if args.book.lower() not in r["book"].lower():
            continue
        if r["image"].endswith("-p.png"):
            continue
        src = IMAGES / r["image"]
        if src.exists():
            shutil.move(str(src), QUAR / r["image"])
            retired += 1
        r["clipped"] = True

    MANIFEST.write_text(json.dumps(rows + new_rows, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n  added {added} re-cut crops")
    print(f"  retired {retired} clipped originals to quarantine (labels kept, marked clipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
