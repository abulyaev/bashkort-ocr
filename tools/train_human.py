#!/usr/bin/env python3
"""Fine-tune the auto-trained model on the human-verified lines.

The model is built in two stages. Stage one learns letterforms from ~66,000
auto-aligned lines, which are plentiful but carry ABBYY's word segmentation
along with its mistakes. Stage two, here, fine-tunes that on human-verified
lines, which are few but correct — this is the stage that fixes spacing and the
ҫ/ҙ confusions the auto set cannot teach.

    python3 tools/train_human.py --iterations 6000

The eval set is frozen in `data/train/eval_fixed.list` by `make_eval_set.py`
and is never rewritten here, so scores stay comparable across runs. A line in
it that has vanished from the export is fatal: a shrinking eval set silently
makes every later number incomparable to every earlier one.

Nothing in the eval set is ever trained on — the split is by line, checked, and
the check is fatal rather than a warning.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "train"
VERIFIED = ROOT / "data" / "lines" / "verified"

TRAIN_DIR = WORK / "h_train2"
EVAL_LIST = WORK / "eval_fixed.list"        # frozen stems, never rewritten
EVAL_LSTMF = WORK / "eval_fixed_lstmf.list"  # the same lines as .lstmf paths
BASE_CKPT = WORK / "output2" / "bak_checkpoint"
LANG_TRAINED = WORK / "bak" / "bak.traineddata"
MANIFEST = ROOT / "data" / "lines" / "human" / "manifest.json"


def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], text=True, **kw)


def build_lstmf(jobs: int) -> None:
    """Render every verified pair to .lstmf. Cheap to redo, so always redo it."""
    if TRAIN_DIR.exists():
        shutil.rmtree(TRAIN_DIR)
    r = sh([sys.executable, ROOT / "tools" / "make_lstmf.py",
            "--src", VERIFIED, "--out", TRAIN_DIR, "--jobs", jobs])
    if r.returncode != 0:
        sys.exit("make_lstmf failed")


def edited_stems() -> set[str]:
    """Lines the transcriber actually changed.

    A label accepted verbatim from the model is not necessarily wrong, but it
    carries almost no corrective signal — it asks the network to keep doing what
    it already does. When most of the set is self-labelled that dilutes the
    lines that do disagree, which is the whole point of the human pass.
    """
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {Path(r["image"]).stem for r in rows if r.get("edited")}


def split(train_list: Path, only_edited: bool,
          cap: int = 0) -> tuple[list[Path], list[Path]]:
    """Hold out the frozen eval lines; optionally train only on edited ones."""
    made = {p.stem: p for p in TRAIN_DIR.glob("*.lstmf")}
    if not made:
        sys.exit(f"no .lstmf produced in {TRAIN_DIR}")

    want = [l.strip() for l in EVAL_LIST.read_text().splitlines() if l.strip()]
    eval_stems = [s for s in want if s in made]
    missing = len(want) - len(eval_stems)
    if missing:
        sys.exit(f"{missing} of {len(want)} frozen eval lines are missing from the "
                 f"export — the eval set must not drift between runs")
    print(f"  eval: {len(eval_stems)} frozen lines")

    ev = {s for s in eval_stems}
    keep = edited_stems() if only_edited else None
    train = [made[s] for s in sorted(made)
             if s not in ev and (keep is None or s in keep)]
    evals = [made[s] for s in eval_stems]

    # A line in both sets makes the score meaningless, so make it fatal.
    overlap = {p.stem for p in train} & {p.stem for p in evals}
    if overlap:
        sys.exit(f"train/eval overlap on {len(overlap)} lines — refusing to train")

    if cap and cap < len(train):
        # Deterministic subset so learning-curve points are nested and the
        # only thing changing between runs is how much data there is.
        rng = random.Random(7)
        train = sorted(rng.sample(train, cap), key=lambda p: p.stem)

    train_list.write_text("\n".join(str(p.resolve()) for p in train) + "\n")
    EVAL_LSTMF.write_text("\n".join(str(p.resolve()) for p in evals) + "\n")
    return train, evals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=6000)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--skip-lstmf", action="store_true")
    ap.add_argument("--edited-only", action="store_true",
                    help="train only on lines the transcriber changed")
    ap.add_argument("--tag", default="bakh2", help="model and output-dir name")
    ap.add_argument("--max-train", type=int, default=0,
                    help="cap the training set, for learning-curve runs")
    args = ap.parse_args()

    for p in (BASE_CKPT, LANG_TRAINED):
        if not p.exists():
            sys.exit(f"missing {p}")

    if not args.skip_lstmf:
        print("  rendering .lstmf from verified pairs")
        build_lstmf(args.jobs)

    train_list = WORK / f"{args.tag}_train.list"
    out_dir = WORK / f"out_{args.tag}"
    train, evals = split(train_list, args.edited_only, args.max_train)
    print(f"  train {len(train):,} lines · eval {len(evals):,} lines"
          + ("  (edited only)" if args.edited_only else ""))

    out_dir.mkdir(parents=True, exist_ok=True)
    # No --old_traineddata here. That flag remaps the output layer onto a new
    # unicharset and belongs to stage one, where the base was kaz. This
    # checkpoint already carries the bak charset; remapping it a second time
    # would discard the ҫ unit that stage one exists to add.
    cmd = ["lstmtraining",
           "--continue_from", BASE_CKPT,
           "--traineddata", LANG_TRAINED,
           "--train_listfile", train_list,
           "--eval_listfile", EVAL_LSTMF,
           "--model_output", out_dir / args.tag,
           "--max_iterations", args.iterations,
           "--target_error_rate", 0.01]
    print("  " + " ".join(str(c) for c in cmd) + "\n", flush=True)
    return sh(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
