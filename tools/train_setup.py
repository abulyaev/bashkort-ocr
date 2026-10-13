#!/usr/bin/env python3
"""Stage 1 of training bak.traineddata: unicharset and starter model.

Fine-tunes from `kaz`, which measurement showed is the strongest available base:
52.5% CER on the verified set, recovering 74-99% of eight of Bashkort's nine
letters. It is missing exactly one — ҫ (U+04AB), which exists in no Tesseract
charset at all — so this is the "add a character to the output layer" path
rather than training from scratch.

    python3 tools/train_setup.py
"""

from __future__ import annotations

import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

WORK = ROOT / "data" / "train"
TESSDATA = Path("/opt/homebrew/share/tessdata")
BASE = "kaz"
LANG = "bak"


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"    ! {' '.join(str(c) for c in cmd[:3])}: {r.stderr.strip()[:300]}")
    return r


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    auto = ROOT / "data" / "lines" / "auto"
    verified = ROOT / "data" / "lines" / "verified"

    # ---- 1. gather all label text -------------------------------------
    gts = sorted(auto.glob("*.gt.txt"))
    texts = [g.read_text(encoding="utf-8").strip() for g in gts]
    all_text = "\n".join(t for t in texts if t)
    train_txt = WORK / "bak.training_text"
    train_txt.write_text(all_text + "\n", encoding="utf-8")
    print(f"  training text : {len(gts):,} lines, {len(all_text):,} chars")

    # ---- 2. what characters must the model know? -----------------------
    chars = sorted({c for c in all_text if not c.isspace()})
    need = "ҙҫҡғәөүңһҘҪҠҒӘӨҮҢҺ"
    present = "".join(c for c in need if c in chars)
    print(f"  distinct chars: {len(chars)}")
    print(f"  Bashkort set  : {present}")
    missing = [c for c in need if c not in chars]
    if missing:
        print(f"  absent from labels: {''.join(missing)}")

    # ---- 3. unicharset from the labels ---------------------------------
    box = WORK / "bak.unicharset"
    sh(["unicharset_extractor", "--output_unicharset", str(box),
        "--norm_mode", "2", str(train_txt)], cwd=WORK)
    if not box.exists():
        sys.exit("  unicharset_extractor produced nothing")
    n = int(box.read_text(encoding="utf-8").split("\n")[0])
    print(f"  unicharset    : {n} entries -> {box.name}")

    # ---- 4. does it contain ҫ, the letter no model has? -----------------
    uc_chars = set()
    for i, line in enumerate(box.read_text(encoding="utf-8").split("\n")):
        if i == 0 or not line.strip():
            continue
        uc_chars.add(line.split()[0])
    for ch in "ҙҫҡғ":
        mark = "YES" if ch in uc_chars else "NO "
        print(f"     {mark}  {ch}  U+{ord(ch):04X}  {unicodedata.name(ch).split()[-3:][0]}")

    # ---- 5. extract the base model -------------------------------------
    base_dir = WORK / "base"
    base_dir.mkdir(exist_ok=True)
    sh(["combine_tessdata", "-u", str(TESSDATA / f"{BASE}.traineddata"),
        str(base_dir / f"{BASE}.")], cwd=WORK)
    lstm = base_dir / f"{BASE}.lstm"
    if not lstm.exists():
        sys.exit(f"  could not extract {BASE}.lstm")
    print(f"  base model    : {BASE}.lstm  {lstm.stat().st_size:,} bytes")

    print(f"\n  next: generate .lstmf training files, then lstmtraining")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
