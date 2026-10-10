"""bashlat — Bashkort Cyrillic to Latin transliteration.

    >>> from bashlat import Transliterator
    >>> Transliterator().convert("Башҡорт теле — төрки тел")
    'Başqort tele — törki tel'
"""

from .translit import Transliterator, Ambiguity
from .reverse import ReverseTransliterator, roundtrip_report
from .detect import Verdict, detect
from .extract import Extraction, capabilities, extract

__version__ = "0.2.0"

__all__ = [
    "Transliterator",
    "ReverseTransliterator",
    "Ambiguity",
    "roundtrip_report",
    "detect",
    "Verdict",
    "extract",
    "Extraction",
    "capabilities",
]
