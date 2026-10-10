#!/usr/bin/env python3
"""Cut line images from the books that have no text layer, ready for a human.

These are the books ABBYY could not read, which is exactly why they matter:
they are the hard cases, and they are where the evaluation set has to come
from. `tools/align_lines.py` handles everything with a text layer for free;
this handles what is left.

Each line is pre-filled with the Surya+corrector reading so the job is checking
rather than typing. The manifest records that suggestion separately from
whatever you end up saving, so the fraction you had to change is measurable —
if the pre-fill is dragging answers toward its own mistakes, that shows up in
the data instead of hiding in it.

    python3 tools/prepare_transcription.py                  # all reserved books
    python3 tools/prepare_transcription.py --pages-per-book 3
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SURYA_DIR = ROOT / ".venv-ocr" / "bin"
DPI = 300
PAD = 6
MIN_W, MIN_H, MAX_H = 60, 14, 260


def sh(cmd, timeout=1800) -> bytes:
    return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout


def page_count(pdf: Path) -> int:
    out = sh(["pdfinfo", str(pdf)], 120).decode("utf-8", "ignore")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def detect_lines(pdf: Path, page: int, td: Path):
    """Line boxes from surya_detect, rescaled to a 300 dpi render."""
    out = td / f"det{page}"
    sh([str(SURYA_DIR / "surya_detect"), str(pdf),
        "--page_range", str(page - 1), "--output_dir", str(out)])
    js = list(out.rglob("*.json"))
    if not js:
        return []
    data = json.loads(js[0].read_text(encoding="utf-8"))
    pages = list(data.values())[0]
    if not pages:
        return []
    p = pages[0]
    fw, fh = p["image_bbox"][2], p["image_bbox"][3]
    return [(b["bbox"], b.get("confidence", 0.0)) for b in p.get("bboxes", [])], (fw, fh)


def render(pdf: Path, page: int, td: Path):
    pre = td / f"pg{page}"
    sh(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI),
        "-gray", "-png", str(pdf), str(pre)], 600)
    got = sorted(td.glob(f"pg{page}*.png"))
    return got[0] if got else None


def slug(name: str) -> str:
    from bashlat import Transliterator
    import hashlib
    latin = Transliterator().convert(name)
    s = re.sub(r"[^A-Za-z0-9]+", "-", unicodedata.normalize("NFKD", latin))
    s = re.sub(r"-+", "-", s).strip("-")[:30]
    return f"{s}-{hashlib.sha1(name.encode()).hexdigest()[:6]}"


def _read_batch(paths, workdir: Path) -> dict:
    """One surya_ocr invocation over a handful of line images."""
    stage = workdir / "stage"
    if stage.exists():
        for f in stage.iterdir():
            f.unlink()
    stage.mkdir(parents=True, exist_ok=True)
    for p in paths:
        (stage / p.name).write_bytes(p.read_bytes())

    out = workdir / "out"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    # Output goes to DEVNULL, never to a pipe. surya_ocr spawns llama-server as
    # a child which inherits stdout/stderr; capture_output makes subprocess.run
    # wait for EOF on those pipes, and the server holds them open, so the call
    # blocks forever while the model sits there working. Also not --keep_server,
    # which leaves the server alive deliberately and deadlocks the same way.
    subprocess.run([str(SURYA_DIR / "surya_ocr"), str(stage), "--output_dir", str(out)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=1800)

    readings = {}
    for js in out.rglob("*.json"):
        try:
            data = json.loads(js.read_text(encoding="utf-8"))
        except Exception:
            continue
        for name, pages in data.items():
            txt = []
            for pg in pages or []:
                for b in pg.get("blocks", []):
                    txt.append(re.sub(r"<[^>]+>", " ", b.get("html") or ""))
            readings[Path(name).stem] = re.sub(r"\s+", " ", " ".join(txt)).strip()
    return readings


def fill_suggestions(manifest_path: Path, batch: int = 60) -> None:
    """Add a Surya+corrector reading to every line, saving after each batch.

    Done in batches because a single call over ~1000 line images runs for the
    better part of an hour and takes everything with it if it stops. Batching
    makes the pass resumable: rerun and it picks up where it left off.
    """
    from bashlat.correct import Corrector
    model = ROOT / "data" / "models" / "corrector.json"
    corrector = Corrector.load(model) if model.exists() else None

    images = manifest_path.parent / "images"
    rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    todo = [r for r in rows if not r.get("suggestion")]
    if not todo:
        print("  all lines already have a suggestion")
        return
    print(f"  {len(todo):,} of {len(rows):,} lines need a reading", flush=True)

    with tempfile.TemporaryDirectory() as tds:
        work = Path(tds)
        for start in range(0, len(todo), batch):
            chunk = todo[start:start + batch]
            paths = [images / r["image"] for r in chunk]
            try:
                readings = _read_batch([p for p in paths if p.exists()], work)
            except Exception as e:
                print(f"    batch {start//batch + 1} failed ({type(e).__name__}), skipping")
                continue
            # Re-read before writing. A human may be transcribing in the
            # browser right now, and their saves land in this same file; writing
            # back our minutes-old copy would erase their work. Only the
            # `suggestion` field is ours to set, and never on a line already
            # answered.
            current = json.loads(manifest_path.read_text(encoding="utf-8"))
            index = {r["image"]: i for i, r in enumerate(current)}
            for r in chunk:
                text = readings.get(Path(r["image"]).stem, "")
                value = corrector.correct(text) if (corrector and text) else text
                i = index.get(r["image"])
                if i is not None and not current[i].get("suggestion") \
                        and current[i].get("text") is None:
                    current[i]["suggestion"] = value
            manifest_path.write_text(
                json.dumps(current, ensure_ascii=False, indent=1), encoding="utf-8")
            rows = current
            done = sum(1 for r in current if r.get("suggestion"))
            print(f"    {done:,}/{len(current):,} read", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages-per-book", type=int, default=2)
    ap.add_argument("--out", default="data/lines/human")
    ap.add_argument("--no-suggest", action="store_true",
                    help="skip the Surya pre-fill (slow); start from blank")
    args = ap.parse_args()

    from bashlat.corpus import ocr_books, load_book_config
    cfg = load_book_config()
    books = ocr_books(ROOT / "texts/source", cfg)
    if not books:
        sys.exit("No books marked role:'ocr' in data/books.json")

    out = ROOT / args.out
    imgs = out / "images"
    imgs.mkdir(parents=True, exist_ok=True)
    manifest = []

    print(f"  {len(books)} reserved books, {args.pages_per_book} page(s) each\n")
    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        for pdf in books:
            n = page_count(pdf)
            if not n:
                print(f"    {pdf.name[:44]:<46} unreadable"); continue
            lo, hi = max(1, n // 6), max(2, n - n // 8)
            step = max(1, (hi - lo) // args.pages_per_book)
            pages = list(range(lo, hi, step))[:args.pages_per_book]
            stem = slug(pdf.stem)
            made = 0
            for page in pages:
                got = detect_lines(pdf, page, td)
                if not got:
                    continue
                boxes, (fw, fh) = got
                img = render(pdf, page, td)
                if not img:
                    continue
                with Image.open(img) as im:
                    im = im.convert("L")
                    W, H = im.size
                    sx, sy = W / fw, H / fh
                    boxes.sort(key=lambda b: (round(b[0][1] * sy / 8), b[0][0]))
                    for i, (bb, conf) in enumerate(boxes):
                        L = max(0, int(bb[0] * sx) - PAD)
                        T = max(0, int(bb[1] * sy) - PAD)
                        R = min(W, int(bb[2] * sx) + PAD)
                        B = min(H, int(bb[3] * sy) + PAD)
                        if R - L < MIN_W or not (MIN_H <= B - T <= MAX_H):
                            continue
                        name = f"{stem}_p{page:04d}_l{i:03d}.png"
                        im.crop((L, T, R, B)).save(imgs / name)
                        manifest.append({"image": name, "book": pdf.name,
                                         "page": page, "suggestion": "",
                                         "text": None, "edited": None})
                        made += 1
                img.unlink(missing_ok=True)
            print(f"    {pdf.name[:44]:<46}{made:>6} lines", flush=True)

    # Written before the readings are attempted: a slow or failed OCR pass must
    # never cost us the crops, which are the expensive part to regenerate.
    mpath = out / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"\n  {len(manifest):,} lines -> {out}")

    if not args.no_suggest and manifest:
        print(f"\n  reading lines with Surya for pre-fill (resumable)...", flush=True)
        fill_suggestions(mpath)

    print(f"\n  next:  python3 tools/transcribe.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
