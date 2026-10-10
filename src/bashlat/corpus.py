"""Build a clean Bashkort training corpus out of a directory of books.

Books arrive as scans, exports and conversions of wildly varying quality, and
feeding all of it to a language model would teach it OCR noise as readily as
Bashkort. This module extracts, screens and cleans, and — importantly — refuses
to silently discard anything. Every book that is dropped or altered is reported
with a reason, so the decision stays with a human.

Screening catches five distinct failure modes:

  wrong-language    the book is Russian or Tatar
  broken-encoding   the text layer extracts but its CMap is corrupt
  low-yield         far less text than the page count implies — a failed scrape
  garbage           high rate of tokens that are not plausible words
  script-anomaly    unexpected Latin or Arabic content mixed into Cyrillic
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import json

from .detect import detect
from .extract import extract_full

BOOKS_CONFIG = Path(__file__).resolve().parents[2] / "data" / "books.json"


def load_book_config(path: Optional[Path] = None) -> Dict[str, dict]:
    """Human decisions that override automatic screening.

    The screener is a heuristic and will misjudge books — an illustrated
    folk-tale collection reads as `garbage`, a dictionary reads as
    `mixed-language`. Those judgements belong to someone who can read the book,
    so they live in `data/books.json` and are never written by code.

    Keys are normalised to NFC. macOS stores filenames decomposed (NFD), so a
    name typed into JSON and the same name read from the filesystem are
    different byte strings despite looking identical. Every lookup goes through
    `book_key`.
    """
    p = path or BOOKS_CONFIG
    if not p.exists():
        return {}
    return {book_key(k): v
            for k, v in json.loads(p.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def book_key(name: str) -> str:
    """Filename normalised for comparison across NFC/NFD and stray whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", name)).strip()


CHUNK = 3000
BASHKORT_LETTERS = "а-яёәөүңһҙҫҡғА-ЯЁӘӨҮҢҺҘҪҠҒ"
WORD = re.compile(f"[{BASHKORT_LETTERS}]+")
LATIN = re.compile(r"[A-Za-z]")
CYR = re.compile(r"[Ѐ-ӿ]")
ARABIC = re.compile(r"[؀-ۿ]")

# Lines that are page furniture rather than text.
NOISE_LINE = re.compile(r"^[\s\d.,;:_\-–—|«»\[\](){}]*$")


@dataclass
class BookReport:
    file: str
    pages: Optional[int]
    source: str
    lang: str
    confidence: float
    raw_chars: int = 0
    kept_chars: int = 0
    bashkort_share: float = 0.0
    role: str = "corpus"
    flags: List[str] = field(default_factory=list)
    notes: Dict[str, object] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.kept_chars > 0 and not self.flags and self.role == "corpus"

    def __str__(self) -> str:  # pragma: no cover - presentation only
        flag = ",".join(self.flags) if self.flags else (
            "OCR-only" if self.role == "ocr" else "ok")
        return (f"{self.file[:46]:<48}{self.lang:<11}{self.source:<7}"
                f"{self.kept_chars:>9,}  {flag}")


def _dehyphenate(text: str) -> str:
    """Join words split across a line break.

    Conservative on purpose: Bashkort forms genuine hyphenated compounds
    (boron-boron, ata-baba, ğöröf-ğäźät), so only a hyphen at end of line
    followed by a lower-case continuation is joined.
    """
    return re.sub(f"([{BASHKORT_LETTERS}])-\\s*\\n\\s*([а-яёәөүңһҙҫҡғ])", r"\1\2", text)


def _garbage_rate(text: str) -> float:
    """Share of tokens that do not look like words."""
    toks = WORD.findall(text)
    if len(toks) < 50:
        return 0.0
    bad = 0
    for t in toks:
        low = t.lower()
        if len(low) == 1 and low not in "аәийоөуүыэюя":
            bad += 1                       # stray single letters
        elif len(low) > 24:
            bad += 1                       # runaway concatenation
        elif not re.search(r"[аәеёиоөуүыэюя]", low):
            bad += 1                       # no vowel at all
    return bad / len(toks)


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("­", "")                      # soft hyphens
    text = _dehyphenate(text)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", line).strip()
        if not line or NOISE_LINE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def filter_bashkort(text: str) -> Tuple[str, float]:
    """Keep only the chunks that are actually Bashkort. Returns (text, share)."""
    chunks = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]
    kept, total = [], 0
    for ch in chunks:
        if len(ch.strip()) < 200:
            continue
        total += 1
        if detect(ch).lang == "bashkort":
            kept.append(ch)
    share = len(kept) / total if total else 0.0
    return "".join(kept), share


def screen(path: Path, config: Optional[dict] = None) -> Tuple[BookReport, str]:
    """Extract and screen one book. Returns its report and the cleaned text."""
    cfg = config or {}
    if cfg.get("exclude"):
        rep = BookReport(path.name, None, "-", "-", 0.0)
        rep.flags.append("excluded")
        rep.notes["reason"] = cfg.get("note", "excluded by data/books.json")
        return rep, ""

    ex = extract_full(path,
                      skip_pages=cfg.get("skip_pages", 0),
                      skip_end_pages=cfg.get("skip_end_pages", 0))
    raw = ex.text or ""
    v = detect(raw[:120000] or "", ex.source)

    rep = BookReport(path.name, ex.pages, ex.source, v.lang, v.confidence,
                     raw_chars=len(raw))

    # Books reserved for OCR work are expected to have no text layer — that is
    # precisely why they are reserved. Judging them by text yield would flag
    # every one of them as a failure.
    if cfg.get("role") == "ocr":
        rep.role = "ocr"
        rep.notes["reserved_for"] = "OCR training and ground truth"
        rep.notes["note"] = cfg.get("note", "")
        return rep, ""

    if ex.source == "none" or len(raw.strip()) < 500:
        rep.flags.append("low-yield")
        rep.notes["reason"] = ex.note or f"only {len(raw.strip())} chars extracted"
        return rep, ""

    if ex.source == "text?":
        rep.flags.append("broken-encoding")

    if v.lang not in ("bashkort", "uncertain"):
        rep.flags.append("wrong-language")

    cyr = len(CYR.findall(raw))
    lat = len(LATIN.findall(raw))
    arab = len(ARABIC.findall(raw))
    rep.notes.update(cyrillic=cyr, latin=lat, arabic=arab)
    if arab > 200:
        rep.flags.append("script-anomaly")
        rep.notes["script"] = f"{arab} Arabic-script characters"
    elif cyr > 500 and lat > 0.35 * cyr:
        rep.flags.append("script-anomaly")
        rep.notes["script"] = f"{lat} Latin vs {cyr} Cyrillic"

    g = _garbage_rate(raw)
    rep.notes["garbage_rate"] = round(g, 3)
    if g > 0.18:
        rep.flags.append("garbage")

    if ex.pages and ex.pages > 20 and len(raw) < 300 * ex.pages:
        rep.flags.append("low-yield")
        rep.notes["yield"] = f"{len(raw)//max(ex.pages,1)} chars/page"

    text = clean(raw)
    text, share = filter_bashkort(text)
    rep.bashkort_share = round(share, 3)
    rep.kept_chars = len(text)

    if share < 0.55 and "wrong-language" not in rep.flags:
        rep.flags.append("mixed-language")

    # A human has read this book and overruled the heuristics. Their flags are
    # kept for the record but no longer block acceptance.
    if cfg.get("force") and rep.flags:
        rep.notes["overridden"] = rep.flags
        rep.notes["by"] = cfg.get("note", "data/books.json")
        rep.flags = []

    return rep, text


def build(src: Path, out: Path, config: Optional[Dict[str, dict]] = None) -> List[BookReport]:
    """Screen every book in `src`, writing accepted text into `out`."""
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_book_config() if config is None else config
    reports = []
    for p in sorted(src.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() in (".crdownload",):
            continue
        rep, text = screen(p, cfg.get(book_key(p.name)))
        reports.append(rep)
        if rep.accepted and text:
            (out / (p.stem + ".txt")).write_text(text, encoding="utf-8")
        print("  " + str(rep), flush=True)
    return reports


def ocr_books(src: Path, config: Optional[Dict[str, dict]] = None) -> List[Path]:
    """Books reserved for OCR training — no text layer, good scans."""
    cfg = load_book_config() if config is None else config
    on_disk = {book_key(p.name): p for p in src.iterdir() if p.is_file()}
    return [on_disk[k] for k, c in cfg.items()
            if c.get("role") == "ocr" and k in on_disk]
