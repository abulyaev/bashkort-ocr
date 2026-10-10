"""Case conversion for the Bashkort Latin alphabet.

Python's built-in ``str.upper()`` / ``str.lower()`` are wrong for any alphabet
that distinguishes dotted and dotless i, which this one does because Bashkir
contrasts /i/ (и) with /ɯ/ (ы):

    'i'.upper()   -> 'I'   but must be 'İ'
    'İ'.lower()   -> 'i̇'   (i + U+0307!) but must be 'i'
    'ı'.upper()   -> 'I'   correct by luck

Getting this wrong silently corrupts text: `iś` ("deed") would uppercase to
`IŚ`, which reads back as `ıś` — a different word. Every case operation in this
project goes through here.
"""

from __future__ import annotations

# The only pairs Python gets wrong. Everything else (ä/Ä, ş/Ş, ź/Ź, ñ/Ñ, þ/Þ,
# đ/Đ, ŧ/Ŧ ...) round-trips correctly through the standard methods.
_UPPER_OVERRIDES = {"i": "İ", "ı": "I"}
_LOWER_OVERRIDES = {"İ": "i", "I": "ı"}

VOWELS = set("aäeıioöuüAÄEIİOÖUÜ")


def upper(text: str) -> str:
    """Uppercase, honouring the dotted/dotless i distinction."""
    return "".join(_UPPER_OVERRIDES.get(ch, ch.upper()) for ch in text)


def lower(text: str) -> str:
    """Lowercase, honouring the dotted/dotless i distinction."""
    return "".join(_LOWER_OVERRIDES.get(ch, ch.lower()) for ch in text)


def is_upper(ch: str) -> bool:
    """True if `ch` is an uppercase letter, including İ and the dotless I."""
    return ch != lower(ch)


def apply_case(latin: str, was_upper: bool, whole_word_upper: bool) -> str:
    """Cast a converted letter or digraph back into the source letter's case.

    Digraphs are the reason this is not a one-liner. Cyrillic `Е` at the start
    of `Ер` becomes `ye`, which must title-case to `Ye`, not `YE`. But in the
    all-caps heading `ЕР` it must become `YER`. The caller tells us which
    situation we are in via `whole_word_upper`.
    """
    if not was_upper:
        return latin
    if whole_word_upper or len(latin) == 1:
        return upper(latin)
    return upper(latin[0]) + latin[1:]


def title(word: str) -> str:
    """Capitalise the first letter of a word, leaving the rest alone."""
    if not word:
        return word
    return upper(word[0]) + word[1:]
