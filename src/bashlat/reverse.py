"""Latin → Cyrillic, and the round-trip audit built on top of it.

The reverse converter is not really meant for producing Cyrillic — nobody
needs that. It exists so we can ask the only question that objectively
validates an alphabet proposal:

    does Cyrillic → Latin → Cyrillic get the original text back?

Wherever it does not, the Latin orthography has merged a distinction the
Cyrillic one kept. Some of those merges are bugs. Others are the point of the
reform — Cyrillic ь in төньяҡ exists only to stop Russian readers palatalising
the н, and Latin ``tönyaq`` needs no such crutch. ``roundtrip_report`` sorts
the two apart so the genuine losses are visible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import casing
from .translit import Transliterator, _tokenize, load_alphabet

LATIN_WORD = re.compile(r"[A-Za-zÄäÇçĞğıİÑñÖöŞşÜüŹźŚśĐđŦŧÐðÞþ]")

BACK_VOWELS = set("aouı")
FRONT_VOWELS = set("äöüei")
LATIN_VOWELS = BACK_VOWELS | FRONT_VOWELS

# Hand-written rather than auto-inverted from the forward table: several
# forward mappings collide on the way back (both е and э give `e`) and the
# tie-breaks are contextual.
_REVERSE_DIGRAPHS = {
    "şç": "щ",
    "yo": "ё",
    "yu": "ю",
    "ya": "я",
    "ye": "е",
}

_REVERSE_SINGLES = {
    "a": "а", "ä": "ә", "b": "б", "c": "ж", "ç": "ч", "d": "д",
    "f": "ф", "g": "г", "ğ": "ғ", "h": "һ", "x": "х", "ı": "ы",
    "i": "и", "j": "ж", "k": "к", "q": "ҡ", "l": "л", "m": "м",
    "n": "н", "ñ": "ң", "o": "о", "ö": "ө", "p": "п", "r": "р",
    "s": "с", "ş": "ш", "t": "т", "u": "у", "ü": "ү", "v": "в",
    "y": "й", "z": "з",
}


@dataclass
class RoundTrip:
    """One word that did not survive Cyrillic → Latin → Cyrillic intact."""

    original: str
    latin: str
    restored: str
    benign: bool
    reason: str

    def __str__(self) -> str:  # pragma: no cover - presentation only
        mark = "·" if self.benign else "✗"
        return f"{mark} {self.original} → {self.latin} → {self.restored}   {self.reason}"


class ReverseTransliterator:
    def __init__(self, variant: Optional[str] = None, alphabet: Optional[dict] = None) -> None:
        self.alphabet = alphabet or load_alphabet()
        self.variant = variant or self.alphabet["default_variant"]

        self.digraphs = dict(_REVERSE_DIGRAPHS)
        self.singles = dict(_REVERSE_SINGLES)

        for cyr, spec in self.alphabet["variants"][self.variant]["letters"].items():
            low = spec["lower"]
            if len(low) > 1:
                self.digraphs[low] = cyr
            else:
                self.singles[low] = cyr

        # Longest first, so `şç` is matched before `ş` and `dh` before `d`.
        self._ordered = sorted(self.digraphs, key=len, reverse=True)

    def convert(self, text: str) -> str:
        out: List[str] = []
        for token, is_word in _tokenize_latin(text):
            out.append(self._convert_word(token) if is_word else token)
        return "".join(out)

    def _convert_word(self, word: str) -> str:
        letters = [ch for ch in word if LATIN_WORD.match(ch)]
        all_upper = len(letters) > 1 and all(casing.is_upper(ch) for ch in letters)
        lowered = casing.lower(word)

        pieces: List[str] = []
        i = 0
        while i < len(lowered):
            chunk, consumed = self._match(lowered, i)
            was_upper = casing.is_upper(word[i])
            pieces.append(casing.apply_case(chunk, was_upper, all_upper))
            i += consumed

        return "".join(pieces)

    def _match(self, word: str, i: int) -> Tuple[str, int]:
        prev = word[i - 1] if i > 0 else ""

        for digraph in self._ordered:
            if word.startswith(digraph, i):
                # `ye` only spells е in onset position; elsewhere it is й + е,
                # which the single-letter path already handles correctly.
                if digraph == "ye" and not (i == 0 or prev in LATIN_VOWELS):
                    continue
                return self.digraphs[digraph], len(digraph)

        ch = word[i]

        if ch == "e":
            # э wherever Cyrillic е would have been iotated — word-initially
            # and after a vowel. A bare `e` in those positions can only have
            # come from э, because ер and поездка would have produced `ye`.
            # Hence гидроэнергетика, not *гидроенергетика.
            return ("э" if (i == 0 or prev in LATIN_VOWELS) else "е"), 1

        if ch == "w":
            if i == 0:
                return "в", 1  # ваҡыт-type Arabic loans
            # Coda glide: recover у or ү from the harmony of the vowel before it.
            return ("ү" if prev in FRONT_VOWELS else "у"), 1

        return self.singles.get(ch, ch), 1


def _tokenize_latin(text: str):
    buf: List[str] = []
    in_word = False
    for ch in text:
        is_letter = bool(LATIN_WORD.match(ch))
        if is_letter != in_word and buf:
            yield "".join(buf), in_word
            buf = []
        in_word = is_letter
        buf.append(ch)
    if buf:
        yield "".join(buf), in_word


def _strip_signs(word: str) -> str:
    return word.replace("ь", "").replace("ъ", "")


def roundtrip_report(
    text: str,
    variant: Optional[str] = None,
    forward: Optional[Transliterator] = None,
    backward: Optional[ReverseTransliterator] = None,
) -> List[RoundTrip]:
    """Convert every word to Latin and back, and report what changed.

    The naive test — "did the Cyrillic come back byte-identical" — is the wrong
    question, and answering it produces a report that is ~98% noise. Cyrillic
    spells the same sound several ways (ё vs йо, э vs е word-initially, ь that
    marks nothing in a language with no palatalisation), so a converter can be
    perfectly lossless and still fail that test constantly.

    The question that actually matters is whether the *Latin* form is a fixed
    point:

        forward(backward(forward(x))) == forward(x)

    If it is, the Latin spelling survived the excursion through Cyrillic
    unchanged, and whatever differs between the two Cyrillic strings was a
    Cyrillic convention with no phonemic content. If it is not, the Latin
    orthography has genuinely merged two distinct words, and that is a defect
    in the alphabet.
    """
    fwd = forward or Transliterator(variant=variant)
    bwd = backward or ReverseTransliterator(variant=variant)

    seen = set()
    report: List[RoundTrip] = []

    for token, is_word in _tokenize(text):
        if not is_word:
            continue
        key = casing.lower(token)
        if key in seen:
            continue
        seen.add(key)

        latin = fwd.convert(token)
        restored = bwd.convert(latin)
        if restored == token:
            continue

        if fwd.convert(restored) == latin:
            benign = True
            reason = "Cyrillic-only convention (ь/ъ, ё vs йо, э vs е); Latin form is stable"
        else:
            benign = False
            reason = f"MERGE — {latin} is also how {restored} would be written"

        report.append(RoundTrip(token, latin, restored, benign, reason))

    return report
