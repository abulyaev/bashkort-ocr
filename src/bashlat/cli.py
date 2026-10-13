"""Command line interface: python -m bashlat <command> [file]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .detect import detect as detect_text
from .extract import capabilities, extract
from .reverse import ReverseTransliterator, roundtrip_report
from .translit import Transliterator, load_alphabet


def _read(path: Optional[str]) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def cmd_convert(args: argparse.Namespace) -> int:
    tr = Transliterator(variant=args.variant)
    sys.stdout.write(tr.convert(_read(args.file)))
    return 0


def cmd_reverse(args: argparse.Namespace) -> int:
    rev = ReverseTransliterator(variant=args.variant)
    sys.stdout.write(rev.convert(_read(args.file)))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    tr = Transliterator(variant=args.variant)
    result = tr.convert_verbose(_read(args.file))

    if not result.ambiguities:
        print("No ambiguities. Every letter was resolved by rule.")
        return 0

    by_letter: dict = {}
    for amb in result.ambiguities:
        by_letter.setdefault(amb.letter, []).append(amb)

    print(f"{len(result.ambiguities)} decision(s) the converter could not make by rule alone:\n")
    for letter in sorted(by_letter):
        items = by_letter[letter]
        words = sorted({f"{a.word} → {a.latin}" for a in items})
        print(f"  {letter}  ({len(items)} occurrence(s), {len(words)} distinct word(s))")
        print(f"      {items[0].reason}")
        for word in words[:20]:
            print(f"      · {word}")
        if len(words) > 20:
            print(f"      … and {len(words) - 20} more")
        print()
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    text = _read(args.file)
    report = roundtrip_report(text, variant=args.variant)

    genuine = [r for r in report if not r.benign]
    benign = [r for r in report if r.benign]

    print(f"Round-trip audit (variant: {args.variant or load_alphabet()['default_variant']})")
    print(f"  {len(genuine)} genuine merge(s), {len(benign)} benign difference(s)\n")

    if genuine:
        print("GENUINE — the Latin spelling loses information:")
        for r in genuine:
            print(f"  {r}")
        print()

    if benign and args.verbose:
        print("BENIGN — Cyrillic conventions the Latin script drops on purpose:")
        for r in benign:
            print(f"  {r}")
        print()

    if not genuine:
        print("The orthography is lossless on this text.")
    return 0


def cmd_alphabet(args: argparse.Namespace) -> int:
    tr = Transliterator(variant=args.variant)
    alphabet = tr.alphabet
    letters = tr.ordered_alphabet()

    variant_spec = alphabet["variants"][tr.variant]
    print(f"{alphabet['meta']['name']} — {len(letters)} letters")
    print(f"variant: {tr.variant} — {variant_spec['label']}\n")

    print("  " + "  ".join(f"{u}{l}" for u, l in letters))
    print()

    extra = {s["lower"] for s in variant_spec["letters"].values()}
    for upper, low in letters:
        spec = alphabet["letters"].get(low)
        if spec is None:
            for cyr, vs in variant_spec["letters"].items():
                if vs["lower"] == low:
                    spec = {"ipa": vs["ipa"], "cyrillic": cyr, "note": variant_spec["label"]}
                    break
        cyr = spec.get("cyrillic") or "—"
        note = spec.get("note", "")
        mark = " *" if low in extra else "  "
        print(f"  {upper} {low}{mark}  /{spec['ipa']}/".ljust(20) + f"{cyr:>6}   {note}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Show the same text under every ҙ/ҫ variant, for choosing by eye."""
    text = _read(args.file)
    alphabet = load_alphabet()

    for name in ["acute", "stroke", "icelandic", "digraph"]:
        spec = alphabet["variants"][name]
        tr = Transliterator(variant=name)
        print("=" * 78)
        print(f"  {name.upper()}  —  {spec['label']}")
        print("=" * 78)
        print(tr.convert(text).strip())
        print()
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    """Decide whether each book is in Bashkort."""
    paths: List[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            paths.extend(sorted(q for q in p.iterdir() if q.is_file()
                                and not q.name.startswith(".")))
        else:
            paths.append(p)

    if args.check_tools:
        caps = capabilities()
        print("external tools:")
        for k, v in caps.items():
            print(f"  {'ok     ' if v else 'MISSING'}  {k}")
        if not caps["tesseract"]:
            print("\n  OCR unavailable: scanned books will report 'unknown'.")
        print()

    rows = []
    for p in paths:
        ex = extract(p, allow_ocr=not args.no_ocr)
        v = detect_text(ex.text, ex.source)
        rows.append((p, ex, v))
        flag = "" if v.lang == "bashkort" else "   <-- not bashkort"
        note = f"  {ex.note}" if ex.note else ""
        print(f"  {p.name[:52]:<54}{v.lang:<14}{v.confidence:<7.2f}"
              f"{ex.source:<6}{v.chars:>8,}{flag}{note}", flush=True)
        if args.verbose and v.evidence:
            for k in ("bash_words", "tatar_words", "russian_words"):
                if v.evidence.get(k):
                    print(f"        {k}: {v.evidence[k]}")
            if v.distribution:
                print(f"        distribution: "
                      f"{ {k: round(x,2) for k, x in v.distribution.items()} }")

    if len(rows) > 1:
        by_lang: dict = {}
        for _, _, v in rows:
            by_lang[v.lang] = by_lang.get(v.lang, 0) + 1
        print("\n  summary:")
        for lang, n in sorted(by_lang.items(), key=lambda kv: -kv[1]):
            print(f"    {lang:<16}{n:>4}")
        by_src: dict = {}
        for _, ex, _ in rows:
            by_src[ex.source] = by_src.get(ex.source, 0) + 1
        print(f"    {'':<16}     via " +
              ", ".join(f"{k}={n}" for k, n in sorted(by_src.items())))
    return 0


def cmd_correct(args: argparse.Namespace) -> int:
    """Restore Bashkort letters that OCR could not produce."""
    from .correct import Corrector

    model = Path(args.model)
    if not model.exists():
        print(f"no model at {model}. Train one with:\n"
              f"  PYTHONPATH=src python3 -m bashlat corpus-train", file=sys.stderr)
        return 1

    c = Corrector.load(model)
    text = _read(args.file)
    fixed, changes = c.correct_verbose(text)
    sys.stdout.write(fixed)

    if args.report:
        print(f"\n--- {len(changes)} correction(s) ---", file=sys.stderr)
        for ch in changes[:args.report]:
            print(f"  {ch}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bashlat",
        description="Bashkort Cyrillic ↔ Latin transliteration.",
    )
    parser.add_argument(
        "--variant", "-V", default=None,
        help="letters for ҙ/ҫ: acute (ź/ś), stroke (đ/ŧ), icelandic (ð/þ), digraph (dh/th)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, help_text in [
        ("convert", cmd_convert, "Cyrillic → Latin"),
        ("reverse", cmd_reverse, "Latin → Cyrillic"),
        ("audit", cmd_audit, "list every letter the converter had to guess"),
        ("roundtrip", cmd_roundtrip, "check whether Cyrillic → Latin → Cyrillic is lossless"),
        ("compare", cmd_compare, "show the text under all four ҙ/ҫ variants"),
        ("alphabet", cmd_alphabet, "print the alphabet table"),
        ("detect", cmd_detect, "decide whether books are in Bashkort (pdf, djvu, epub)"),
        ("correct", cmd_correct, "restore ҙ ҫ ҡ ң ғ that OCR could not produce"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=fn)
        if name == "correct":
            p.add_argument("--model", default="data/models/corrector.json",
                           help="trained corrector model")
            p.add_argument("--report", type=int, nargs="?", const=40, default=0,
                           metavar="N", help="list the first N corrections on stderr")
        if name not in ("alphabet", "detect"):
            p.add_argument("file", nargs="?", default="-", help="input file, or - for stdin")
        if name == "roundtrip":
            p.add_argument("--verbose", "-v", action="store_true", help="also list benign differences")
        if name == "detect":
            p.add_argument("paths", nargs="+", help="book files, or a directory of them")
            p.add_argument("--no-ocr", action="store_true",
                           help="skip OCR; scanned books report 'unknown'")
            p.add_argument("--check-tools", action="store_true",
                           help="report which external tools are available")
            p.add_argument("--verbose", "-v", action="store_true",
                           help="show the word evidence behind each verdict")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
