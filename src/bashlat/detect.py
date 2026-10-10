"""Decide whether a book is written in Bashkort.

The hard part is not telling Bashkort from English — it is telling Bashkort from
Tatar, which shares most of its Cyrillic inventory, and from Russian, which
turns up inside otherwise Bashkort books as front matter, footnotes and
scholarly apparatus.

Two independent streams of evidence are combined:

**Characters.** ҙ ҫ ҡ ғ occur in Bashkort and not in Tatar; җ occurs in Tatar
and not in Bashkort; ә ө ү ң һ mark Turkic generally but decide nothing between
them. Cheap, and decisive when the text layer is clean.

**Function words.** Bashkort and Tatar differ in exactly the words that occur
most often, which makes short high-frequency pairs the strongest signal
available — менән/белән, өсөн/өчен, был/бу, ине/иде, тип/дип, беҙ/без. This
stream survives OCR damage that destroys the character stream, because a
mis-scanned diacritic still leaves a recognisable word shape.

Documents are scored in chunks rather than whole, because a Bashkort novel with
a Russian preface is not a Russian book, and a single verdict over the whole
file would call it one. Chunk verdicts are reported as a distribution.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- character inventories -------------------------------------------------

BASHKORT_ONLY = set("ҙҫҡғҘҪҠҒ")      # absent from Tatar
TATAR_ONLY = set("җҖ")                # absent from Bashkort
TURKIC_SHARED = set("әөүңһӘӨҮҢҺ")     # decides nothing on its own
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
WORD = re.compile(r"[Ѐ-ӿa-zA-ZäöüğñşźśçıİÄÖÜĞÑŞŹŚÇ]+")

# Latin-script Bashkort, i.e. this project's own output.
LATIN_BASHKORT = set("äöüğñşźśıÄÖÜĞÑŞŹŚİ")

# --- function words --------------------------------------------------------
# Weight 3 = the word differs from its Tatar counterpart and is common.
# Weight 1 = common but shared, so only useful in bulk.

# Homographs across these languages are weighted down rather than dropped:
# `был` is Bashkort "this" but also Russian "was", and `тип` is Bashkort's
# quotative but also a Russian noun. Counting either at full weight lets one
# string vote twice.
BASHKORT_WORDS = {
    "менән": 3, "өсөн": 3, "был": 1, "ине": 3, "юҡ": 3, "тип": 1,
    "беҙ": 3, "һеҙ": 3, "ҙур": 3, "яҡшы": 3, "кеүек": 3, "һуң": 3,
    "ошо": 3, "ҡына": 3, "уның": 2, "улар": 2, "уларҙың": 3, "беҙҙең": 3,
    "барыһы": 2, "түгел": 2, "бөтә": 2, "һәр": 2, "яңы": 2, "тик": 1,
    "һәм": 1, "шул": 1, "бар": 1, "күп": 1, "бик": 1, "әле": 1,
    "инде": 1, "ул": 1, "ләкин": 1, "әммә": 1, "ғына": 2, "бына": 2,
}

TATAR_WORDS = {
    "белән": 3, "өчен": 3, "бу": 3, "иде": 3, "юк": 3, "дип": 3,
    "без": 3, "сез": 3, "зур": 3, "яхшы": 3, "кебек": 3, "соң": 3,
    "шушы": 3, "гына": 2, "аның": 2, "алар": 2, "аларның": 3, "безнең": 3,
    "барысы": 2, "түгел": 1, "бөтен": 2, "һәр": 1, "яңа": 2,
    "һәм": 1, "шул": 1, "бар": 1, "күп": 1, "бик": 1, "әле": 1, "инде": 1,
}

RUSSIAN_WORDS = {
    "и": 1, "в": 1, "на": 1, "не": 1, "что": 2, "как": 2, "это": 2,
    "для": 2, "по": 1, "из": 1, "но": 1, "он": 1, "она": 2, "они": 2,
    "мы": 1, "его": 2, "их": 1, "при": 2, "от": 1, "за": 1, "то": 1,
    # `был` omitted deliberately — it collides with Bashkort "this".
    # была/было/были carry Russian past tense without the ambiguity.
    "была": 2, "было": 2, "были": 2, "все": 2, "так": 1, "уже": 2,
    "или": 2, "если": 2, "этом": 2, "чтобы": 3,
    "который": 3, "которые": 3, "года": 2, "году": 2, "также": 3,
}

LATIN_BASHKORT_WORDS = {
    "menän": 3, "ösön": 3, "bıl": 3, "ine": 3, "yuq": 3, "tip": 3,
    "beź": 3, "heź": 3, "źur": 3, "yaqşı": 3, "kewek": 3, "huñ": 3,
    "oşo": 3, "qına": 3, "häm": 1, "şul": 1, "bar": 1, "küp": 1,
    "bik": 1, "äle": 1, "inde": 1, "ul": 1, "ğına": 2,
}

# --- OCR-safe discriminators ------------------------------------------------
# Tesseract ships no Bashkort model (163 languages, `bak` is not among them),
# so scanned books must be read with `tat`. A Tatar model has no ҙ ҫ ҡ ғ in its
# charset and silently rewrites them to their nearest Tatar shapes — беҙ→без,
# юҡ→юк — which is precisely the evidence that identifies Bashkort. Under OCR
# the character stream is therefore not merely noisy, it is biased toward Tatar.
#
# These pairs discriminate without using any Bashkort-only letter, so they
# survive a Tatar-model scan intact. They are the only word evidence trusted
# when the source is OCR.
OCR_SAFE_BASHKORT = {
    "менән": 3, "өсөн": 3, "был": 3, "ине": 3, "кеүек": 3, "ошо": 3,
    "улар": 3, "уның": 3, "һуң": 2, "яңы": 2, "бөтә": 2, "түгел": 1,
}
OCR_SAFE_TATAR = {
    "белән": 3, "өчен": 3, "бу": 3, "иде": 3, "кебек": 3, "шушы": 3,
    "алар": 3, "аның": 3, "соң": 2, "яңа": 2, "бөтен": 2,
}

LANGS = ("bashkort", "tatar", "russian", "turkic-other")

MIN_CHARS = 400          # below this, extraction is treated as having failed
CHUNK = 3000
UNCERTAIN_BELOW = 0.40   # below this the verdict is reported as `uncertain`


@dataclass
class Verdict:
    lang: str
    confidence: float
    source: str = "text"
    chars: int = 0
    distribution: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, object] = field(default_factory=dict)

    @property
    def is_bashkort(self) -> bool:
        return self.lang == "bashkort"

    def __str__(self) -> str:  # pragma: no cover - presentation only
        share = self.distribution.get(self.lang, 0.0)
        return (f"{self.lang:<13} conf={self.confidence:.2f} "
                f"[{self.source}] {self.chars:,} chars, {share:.0%} of text")


def _score_chunk(text: str, ocr: bool = False) -> Tuple[Dict[str, float], Dict[str, object]]:
    """Return raw per-language scores for one chunk, plus the evidence behind them.

    When `ocr` is set, the Bashkort/Tatar decision rests entirely on the
    OCR-safe word pairs; the character stream is used only to separate Cyrillic
    Turkic from Russian, never to choose between Bashkort and Tatar.
    """
    words = [w.lower() for w in WORD.findall(text)]
    if not words:
        return {}, {}

    n_words = len(words)
    cyr = sum(1 for c in text if CYRILLIC.match(c))
    latin_marks = sum(1 for c in text if c in LATIN_BASHKORT)

    # -- character stream ---------------------------------------------------
    b_chars = sum(1 for c in text if c in BASHKORT_ONLY)
    t_chars = sum(1 for c in text if c in TATAR_ONLY)
    s_chars = sum(1 for c in text if c in TURKIC_SHARED)

    per1k = lambda n, d: (1000.0 * n / d) if d else 0.0
    b_rate, t_rate, s_rate = per1k(b_chars, cyr), per1k(t_chars, cyr), per1k(s_chars, cyr)

    # -- word stream --------------------------------------------------------
    def hits(table):
        found = {}
        total = 0
        for w in words:
            if w in table:
                found[w] = found.get(w, 0) + 1
                total += table[w]
        return total, found

    b_w, b_found = hits(OCR_SAFE_BASHKORT if ocr else BASHKORT_WORDS)
    t_w, t_found = hits(OCR_SAFE_TATAR if ocr else TATAR_WORDS)
    r_w, r_found = hits(RUSSIAN_WORDS)
    l_w, l_found = hits(LATIN_BASHKORT_WORDS)

    wn = lambda n: 1000.0 * n / n_words

    if ocr:
        # ҙ ҫ ҡ ғ cannot be trusted here — the Tatar model cannot emit them, so
        # their absence is an artefact of the scan, not evidence about the book.
        scores = {
            "bashkort": wn(b_w) * 3.0,
            "tatar": wn(t_w) * 3.0,
            "russian": wn(r_w) * 2.2,
            # Turkic-shared letters DO survive a Tatar scan, so they still
            # separate a Turkic book from a Russian one.
            "turkic-other": min(s_rate, 40) * 0.9,
        }
    else:
        scores = {
            # Character evidence is capped so a single stray glyph cannot decide
            # a chunk; word evidence carries most of the weight.
            "bashkort": min(b_rate, 40) * 1.6 + wn(b_w) * 2.2 + wn(l_w) * 2.2
                        + (per1k(latin_marks, max(len(text), 1)) * 0.8),
            "tatar": min(t_rate, 40) * 2.4 + wn(t_w) * 2.2,
            "russian": wn(r_w) * 2.2,
            "turkic-other": min(s_rate, 40) * 0.5,
        }

    # Turkic-shared characters support Bashkort and Tatar equally; they only
    # stand alone when neither language's own evidence appears.
    if scores["bashkort"] < 1 and scores["tatar"] < 1:
        scores["turkic-other"] += min(s_rate, 40) * 0.8

    ev = {
        "bash_chars_per1k": round(b_rate, 1),
        "tatar_chars_per1k": round(t_rate, 1),
        "turkic_chars_per1k": round(s_rate, 1),
        "bash_words": dict(sorted(b_found.items(), key=lambda kv: -kv[1])[:6]),
        "tatar_words": dict(sorted(t_found.items(), key=lambda kv: -kv[1])[:6]),
        "russian_words": dict(sorted(r_found.items(), key=lambda kv: -kv[1])[:6]),
        "latin_words": dict(sorted(l_found.items(), key=lambda kv: -kv[1])[:6]),
    }
    return scores, ev


def detect(text: str, source: str = "text") -> Verdict:
    """Classify `text`, scoring it in chunks and reporting the distribution."""
    text = unicodedata.normalize("NFC", text or "")
    stripped = text.strip()

    if len(stripped) < MIN_CHARS:
        return Verdict("unknown", 0.0, source, len(stripped),
                       evidence={"reason": f"only {len(stripped)} chars of text"})

    ocr = source == "ocr"
    chunks = [stripped[i:i + CHUNK] for i in range(0, len(stripped), CHUNK)]
    votes: Dict[str, int] = {}
    agg: Dict[str, float] = {k: 0.0 for k in LANGS}
    merged_ev: Dict[str, object] = {}
    decided = 0

    for ch in chunks:
        sc, ev = _score_chunk(ch, ocr=ocr)
        if not sc:
            continue
        best = max(sc, key=sc.get)
        if sc[best] < 1.2:            # chunk carries no usable signal
            continue
        votes[best] = votes.get(best, 0) + 1
        decided += 1
        for k, v in sc.items():
            agg[k] += v
        if not merged_ev:
            merged_ev = ev

    if not decided:
        return Verdict("unknown", 0.0, source, len(stripped),
                       evidence={"reason": "no language signal in any chunk"})

    dist = {k: v / decided for k, v in votes.items()}
    lang = max(dist, key=dist.get)
    share = dist[lang]

    # Confidence blends how many chunks agreed with how far ahead the winner is.
    total = sum(agg.values()) or 1.0
    margin = agg[lang] / total
    confidence = round(min(0.99, 0.45 * share + 0.55 * margin), 2)
    if source == "ocr":
        confidence = round(confidence * 0.8, 2)
    elif source == "text?":
        # The extractor flagged this layer's encoding as broken, which strips
        # exactly the Turkic letters the verdict depends on. Whatever the words
        # say, we do not actually know what language this book is in.
        confidence = round(confidence * 0.35, 2)

    merged_ev["chunks"] = decided
    merged_ev["votes"] = votes

    # A thin margin on a damaged scan is a guess, and reporting it as a verdict
    # is worse than admitting the file needs a human. The winning language is
    # kept in the evidence so the caller can still see which way it leaned.
    if confidence < UNCERTAIN_BELOW:
        merged_ev["leaning"] = lang
        return Verdict("uncertain", confidence, source, len(stripped), dist, merged_ev)

    return Verdict(lang, confidence, source, len(stripped), dist, merged_ev)


def detect_mixed(text: str, source: str = "text") -> Verdict:
    """Like `detect`, but reports `mixed` when no language holds a majority."""
    v = detect(text, source)
    if v.lang != "unknown" and v.distribution.get(v.lang, 0) < 0.6:
        second = sorted(v.distribution.items(), key=lambda kv: -kv[1])[1:2]
        v.evidence["runner_up"] = second[0] if second else None
        v.lang = f"mixed:{v.lang}"
    return v
