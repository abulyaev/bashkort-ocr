#!/usr/bin/env python3
"""Turn line image + label pairs into the .lstmf files lstmtraining consumes.

Tesseract's `lstm.train` mode will not read a bare .gt.txt — it wants a .box
file giving a bounding box per character. For line images the convention is one
box per character spanning the whole line height, which is what tesstrain's own
helper produces; the recogniser only uses the text and the line extent.

Runs across all cores, since this is ~66,000 independent tesseract invocations.

    python3 tools/make_lstmf.py --src data/lines/auto  --out data/train/lstmf
    python3 tools/make_lstmf.py --src data/lines/verified --out data/train/eval
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def write_box(img: Path, text: str, box: Path) -> bool:
    try:
        with Image.open(img) as im:
            w, h = im.size
    except Exception:
        return False
    text = unicodedata.normalize("NFC", text).strip()
    if not text:
        return False
    lines = []
    # One box per character across the full line; lstmtraining reads the text,
    # not the individual coordinates, for line-level training.
    #
    # Spaces MUST be emitted. Skipping them — as this did originally — trains a
    # model on text containing no word breaks at all: it then runs words
    # together, producing 18% of the expected spaces and turning a model with
    # better character recognition than kaz (11.3% vs 14.1% CER ignoring
    # spaces) into a far worse one once spacing counts. Tesseract's box reader
    # parses coordinates from the end of the line, so a literal space in the
    # character field is unambiguous.
    step = max(w / max(len(text), 1), 1.0)
    for i, ch in enumerate(text):
        x0 = int(i * step)
        x1 = max(x0 + 1, int((i + 1) * step))
        lines.append(f"{ch} {x0} 0 {min(x1, w)} {h} 0")
    if not lines:
        return False
    lines.append(f"\t {w-1} 0 {w} {h} 0")     # end-of-line marker
    box.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def one(job):
    img_src, gt_src, stage = job
    stem = img_src.stem
    img = stage / f"{stem}.png"
    try:
        img.write_bytes(img_src.read_bytes())
        text = gt_src.read_text(encoding="utf-8")
        if not write_box(img, text, stage / f"{stem}.box"):
            return None
        # psm 7 assumes the image holds exactly one line and returns nothing
        # when it does not. The re-cut crops carry slivers of the neighbouring
        # lines on purpose — that is the cost of clearing the descenders — so
        # psm 7 silently dropped them. psm 13 reads the strip as raw text.
        out = stage / f"{stem}.lstmf"
        for psm in ("7", "13"):
            subprocess.run(["tesseract", str(img), str(stage / stem),
                            "--psm", psm, "lstm.train"],
                           capture_output=True, timeout=120)
            if out.exists() and out.stat().st_size > 0:
                break
        if out.exists() and out.stat().st_size > 0:
            for junk in (img, stage / f"{stem}.box"):
                junk.unlink(missing_ok=True)
            return str(out)
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=max(1, mp.cpu_count() - 1))
    args = ap.parse_args()

    src, out = ROOT / args.src, ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for gt in sorted(src.glob("*.gt.txt")):
        img = Path(str(gt)[:-7] + ".png")
        if img.exists():
            jobs.append((img, gt, out))
    if args.limit:
        jobs = jobs[:args.limit]
    print(f"  {len(jobs):,} pairs -> {out}  ({args.jobs} workers)", flush=True)

    done = 0
    with mp.Pool(args.jobs) as pool:
        for i, res in enumerate(pool.imap_unordered(one, jobs, chunksize=16), 1):
            if res:
                done += 1
            if i % 2000 == 0:
                print(f"    {i:,}/{len(jobs):,}  ({done:,} ok)", flush=True)

    print(f"\n  {done:,} lstmf files written")
    listfile = out.parent / f"{out.name}.list"
    listfile.write_text("\n".join(sorted(str(p) for p in out.glob("*.lstmf"))) + "\n",
                        encoding="utf-8")
    print(f"  list -> {listfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
