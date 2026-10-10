"""Bashkort Cyrillic → Latin transliteration.

Most of the 42 Cyrillic letters map one-to-one and are handled by a lookup
table in ``data/alphabet.json``. This module exists for the four that do not:

    е   /je/ word-initially and after a vowel, /e/ elsewhere
    у   /w/ after a vowel, /u/ elsewhere        (тау taw, but туған tuğan)
    ү   /w/ after a vowel, /y/ elsewhere        (дәүләт däwlät, but күҙ küź)
    в   /v/ in Russian loans, /w/ in the Arabic stratum — not predictable
        from spelling, so it is driven by data/exceptions.tsv

The у/ү rule is the interesting one. Bashkir writes its glide with the same
letters it writes the high vowels with, and disambiguates by position: in a
syllable coda it is /w/. That is fully mechanical, so unlike в it needs no
word list.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from . import casing

_ROOT = Path(__file__).resolve().parents[2]
_ALPHABET_PATH = _ROOT / "data" / "alphabet.json"
_EXCEPTIONS_PATH = _ROOT / "data" / "exceptions.tsv"

CYRILLIC_VOWELS = set("аәеёиоөуүыэюя")
CYRILLIC_LETTER = re.compile(r"[а-яёА-ЯЁғҒҙҘҡҠңҢөӨҫҪүҮһҺәӘ]")

# Context is judged on what was actually emitted, not on the Cyrillic source.
# у and ү are spelled like vowels but surface as the consonant /w/ in coda
# position, and a following е must then behave as if it followed a consonant:
# кеүек is kewek, not *kewyek.
LATIN_VOWELS = set("aäeıioöuü")

# Letters that only occur in Russian-mediated vocabulary. Their presence is a
# reliable signal that a word is a loan, which matters for the в decision and
# for anyone reviewing a converted text by hand.
LOAN_MARKERS = set("цщёъьфчв")


@dataclass
class Ambiguity:
    """One place where the converter had to guess."""

    word: str
    latin: str
    letter: str
    reason: str
    line: int

    def __str__(self) -> str:  # pragma: no cover - presentation only
        return f"line {self.line}: {self.word} → {self.latin}  ({self.letter}: {self.reason})"


@dataclass
class ConversionResult:
    text: str
    ambiguities: List[Ambiguity] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - presentation only
        return self.text


def load_alphabet(path: Optional[Path] = None) -> dict:
    with open(path or _ALPHABET_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_exceptions(path: Optional[Path] = None) -> Tuple[Dict[str, str], List[str]]:
    """Parse data/exceptions.tsv.

    Returns ``(whole_word_overrides, w_stems)``. An entry whose Cyrillic field
    ends in a hyphen is a stem rule: it marks every word beginning with that
    stem as having /w/ rather than /v/. Bashkir is agglutinative, so a
    whole-word lexicon is the wrong shape — listing ``ваҡыт`` would otherwise
    miss ваҡытта, ваҡытында, ваҡытлы and the rest of the paradigm.
    """
    path = path or _EXCEPTIONS_PATH
    words: Dict[str, str] = {}
    stems: List[str] = []
    if not path.exists():
        return words, stems
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            key = casing.lower(parts[0].strip())
            if key.endswith("-"):
                stems.append(key[:-1])
            else:
                words[key] = parts[1].strip()
    # Longest first so that ваҡыт- wins over ваҡ- when both could apply.
    stems.sort(key=len, reverse=True)
    return words, stems


class Transliterator:
    """Convert Bashkort Cyrillic to Latin.

    Parameters
    ----------
    variant:
        Which pair of letters to use for ҙ /ð/ and ҫ /θ/. One of
        ``acute`` (ź/ś), ``stroke`` (đ/ŧ), ``icelandic`` (ð/þ) or
        ``digraph`` (dh/th). See ``data/alphabet.json``.
    exceptions:
        Overrides the lexicon loaded from ``data/exceptions.tsv``.
    """

    def __init__(
        self,
        variant: Optional[str] = None,
        alphabet: Optional[dict] = None,
        exceptions: Optional[Dict[str, str]] = None,
    ) -> None:
        self.alphabet = alphabet or load_alphabet()
        self.variant = variant or self.alphabet["default_variant"]
        if self.variant not in self.alphabet["variants"]:
            valid = ", ".join(sorted(self.alphabet["variants"]))
            raise ValueError(f"unknown variant {self.variant!r}; expected one of: {valid}")

        self.map: Dict[str, str] = dict(self.alphabet["context_free_map"])
        for cyr, spec in self.alphabet["variants"][self.variant]["letters"].items():
            self.map[cyr] = spec["lower"]

        if exceptions is None:
            self.exceptions, self.w_stems = load_exceptions()
        else:
            self.exceptions, self.w_stems = exceptions, []

    # -- public API --------------------------------------------------------

    def convert(self, text: str) -> str:
        """Convert `text`, discarding the ambiguity report."""
        return self.convert_verbose(text).text

    def convert_verbose(self, text: str) -> ConversionResult:
        """Convert `text` and record every guess the converter made."""
        ambiguities: List[Ambiguity] = []
        out: List[str] = []
        line = 1

        for token, is_word in _tokenize(text):
            if is_word:
                latin, notes = self._convert_word(token)
                out.append(latin)
                for letter, reason in notes:
                    ambiguities.append(Ambiguity(token, latin, letter, reason, line))
            else:
                out.append(token)
                line += token.count("\n")

        return ConversionResult("".join(out), ambiguities)

    def audit(self, text: str) -> List[Ambiguity]:
        """Return only the ambiguity report for `text`."""
        return self.convert_verbose(text).ambiguities

    # -- internals ---------------------------------------------------------

    def _convert_word(self, word: str) -> Tuple[str, List[Tuple[str, str]]]:
        letters = [ch for ch in word if CYRILLIC_LETTER.match(ch)]
        all_upper = len(letters) > 1 and all(casing.is_upper(ch) for ch in letters)
        lowered = casing.lower(word)

        override = self.exceptions.get(lowered)
        if override is not None:
            return self._recase_whole(override, word, all_upper), []

        # Resolved once per word: в is /w/ throughout a word built on a listed
        # stem, and /v/ otherwise.
        v_is_w = any(lowered.startswith(stem) for stem in self.w_stems)

        pieces: List[str] = []
        notes: List[Tuple[str, str]] = []
        prev_emitted = ""  # last non-empty Latin chunk; ъ/ь emit nothing

        for i, ch in enumerate(word):
            low = casing.lower(ch)
            prev_cyr = casing.lower(word[i - 1]) if i > 0 else ""
            latin, note = self._convert_letter(
                low, prev_cyr, prev_emitted, at_start=(i == 0), v_is_w=v_is_w
            )
            if note:
                notes.append(note)
            if latin:
                prev_emitted = latin
            pieces.append(casing.apply_case(latin, casing.is_upper(ch), all_upper))

        return "".join(pieces), notes

    def _convert_letter(
        self, ch: str, prev_cyr: str, prev_emitted: str, at_start: bool,
        v_is_w: bool = False,
    ) -> Tuple[str, Optional[Tuple[str, str]]]:
        after_vowel = bool(prev_emitted) and prev_emitted[-1] in LATIN_VOWELS

        if ch == "е":
            # Bashkir е is iotated in onset position. After a consonant it is a
            # plain /e/: белем belem, but ер yer. The preceding sound is judged
            # from the Latin output, so кеүек gives kewek — the ү has already
            # become the consonant w and no longer licenses iotation.
            if at_start or after_vowel or prev_cyr in "ъь":
                return "ye", None
            return "e", None

        if ch in "уү":
            # Coda position -> the glide /w/. This is why дәүләт is däwlät
            # and not *däülät, and why һыу is hıw and not *hıu.
            if after_vowel:
                return "w", None
            return ("u" if ch == "у" else "ü"), None

        if ch == "в":
            if v_is_w:
                return "w", None
            return "v", ("в", "guessed /v/ (Russian loan); add a stem to exceptions.tsv if it is /w/")

        if ch in self.map:
            latin = self.map[ch]
            if ch in LOAN_MARKERS and ch != "в":
                return latin, (ch, "loanword-only letter; check the spelling of the source")
            return latin, None

        # Not ours — punctuation, Latin already, digits. Pass through.
        return ch, None

    @staticmethod
    def _recase_whole(latin: str, source: str, all_upper: bool) -> str:
        if all_upper:
            return casing.upper(latin)
        if source and casing.is_upper(source[0]):
            return casing.title(latin)
        return latin

    # -- alphabet presentation --------------------------------------------

    def ordered_alphabet(self) -> List[Tuple[str, str]]:
        """The alphabet in collation order as (upper, lower) pairs."""
        order = list(self.alphabet["base_order"])
        letters = self.alphabet["letters"]
        extra = self.alphabet["variants"][self.variant]["letters"]

        uppers = {low: spec["upper"] for low, spec in letters.items()}
        for spec in extra.values():
            uppers[spec["lower"]] = spec["upper"]
            anchor = spec["sort_after"]
            order.insert(order.index(anchor) + 1, spec["lower"])

        return [(uppers[low], low) for low in order]


def _tokenize(text: str) -> Iterable[Tuple[str, bool]]:
    """Split `text` into alternating runs of Cyrillic letters and everything else."""
    buf: List[str] = []
    in_word = False

    for ch in text:
        is_letter = bool(CYRILLIC_LETTER.match(ch))
        if is_letter != in_word and buf:
            yield "".join(buf), in_word
            buf = []
        in_word = is_letter
        buf.append(ch)

    if buf:
        yield "".join(buf), in_word


def normalize(text: str) -> str:
    """NFC-normalise so that precomposed and decomposed ә/ө/ү compare equal."""
    return unicodedata.normalize("NFC", text)
