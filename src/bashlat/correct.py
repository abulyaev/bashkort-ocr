"""Restore Bashkort letters that OCR could not produce.

Every OCR engine tested writes Bashkort with a reduced alphabet. Tesseract and
Apple Vision lose all nine non-Russian letters; Surya recovers five and loses
`ҙ ҫ ҡ`, returns `ң` unreliably, and *over*-writes `ғ` where the text has `г`.

What every one of those failures has in common is that the lost letter collapses
onto a specific Russian look-alike. That makes the damage a known channel rather
than something to be learned:

    ҙ→з   ҫ→с   ҡ→к   ң→н   ғ↔г

So instead of asking "what did OCR mean here", we fold both the observed text
and the lexicon into the same ambiguity classes, look up which real words share
a class, and let context choose. Measured over the corpus, only 2.3% of running
tokens land in a class with more than one candidate after Surya, so most words
have exactly one answer and the model never has to guess at all.

Chosen over a neural corrector because the channel is known exactly rather than
estimated, it needs no GPU, and every correction is traceable to a candidate
list and a bigram count — which matters the first time a linguist disputes an
output.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from . import casing

# Each Bashkort letter and the Russian shape OCR collapses it onto.
FOLD_PAIRS = {"ҙ": "з", "ҫ": "с", "ҡ": "к", "ң": "н", "ғ": "г"}
FOLD = str.maketrans({**FOLD_PAIRS,
                      **{k.upper(): v.upper() for k, v in FOLD_PAIRS.items()}})

WORD_RE = re.compile(r"[а-яёәөүңһҙҫҡғА-ЯЁӘӨҮҢҺҘҪҠҒ]+")

UNSEEN_LOGP = -18.0        # log-probability floor for unseen events
BIGRAM_WEIGHT = 1.0
UNIGRAM_WEIGHT = 1.0


def fold(word: str) -> str:
    """Collapse a word onto its ambiguity class."""
    return casing.lower(word).translate(FOLD)


@dataclass
class Correction:
    position: int
    observed: str
    chosen: str
    candidates: List[str]

    def __str__(self) -> str:  # pragma: no cover - presentation only
        alts = ", ".join(c for c in self.candidates if c != self.chosen)
        return f"{self.observed} -> {self.chosen}" + (f"  (over: {alts})" if alts else "")


class Corrector:
    """Noisy-channel corrector over a folded lexicon with bigram context."""

    def __init__(self, unigrams: Dict[str, int], bigrams: Dict[str, Dict[str, int]]):
        self.unigrams = unigrams
        self.bigrams = bigrams
        self.total = sum(unigrams.values()) or 1
        self.by_class: Dict[str, List[str]] = defaultdict(list)
        for w in unigrams:
            self.by_class[fold(w)].append(w)
        for cands in self.by_class.values():
            cands.sort(key=lambda w: -self.unigrams[w])

    # -- training ---------------------------------------------------------

    @classmethod
    def train(cls, texts: Iterable[str], min_count: int = 1) -> "Corrector":
        uni: Counter = Counter()
        bi: Dict[str, Counter] = defaultdict(Counter)
        for text in texts:
            for line in unicodedata.normalize("NFC", text).split("\n"):
                toks = [casing.lower(t) for t in WORD_RE.findall(line)]
                uni.update(toks)
                for a, b in zip(toks, toks[1:]):
                    bi[a][b] += 1
        if min_count > 1:
            uni = Counter({w: c for w, c in uni.items() if c >= min_count})
            bi = {a: Counter({b: c for b, c in d.items() if b in uni})
                  for a, d in bi.items() if a in uni}
        return cls(dict(uni), {a: dict(d) for a, d in bi.items()})

    # -- scoring ----------------------------------------------------------

    def _log_uni(self, w: str) -> float:
        c = self.unigrams.get(w, 0)
        return math.log(c / self.total) if c else UNSEEN_LOGP

    def _log_bi(self, prev: Optional[str], w: str) -> float:
        if prev is None:
            return self._log_uni(w)
        d = self.bigrams.get(prev)
        if d:
            c = d.get(w, 0)
            if c:
                return math.log(c / sum(d.values()))
        return UNSEEN_LOGP + self._log_uni(w) * 0.5   # backoff

    def candidates(self, token: str) -> List[str]:
        """Real words consistent with an observed token."""
        cands = self.by_class.get(fold(token), [])
        if cands:
            return cands
        low = casing.lower(token)
        return [low]        # unknown word: leave alone

    # -- decoding ---------------------------------------------------------

    def _viterbi(self, tokens: List[str]) -> List[str]:
        if not tokens:
            return []
        beams: List[Tuple[float, List[str]]] = [(0.0, [])]
        for tok in tokens:
            cands = self.candidates(tok)
            nxt: List[Tuple[float, List[str]]] = []
            for score, path in beams:
                prev = path[-1] if path else None
                for c in cands[:8]:
                    s = score + BIGRAM_WEIGHT * self._log_bi(prev, c) \
                              + UNIGRAM_WEIGHT * self._log_uni(c) * 0.25
                    nxt.append((s, path + [c]))
            nxt.sort(key=lambda x: -x[0])
            beams = nxt[:12]
        return beams[0][1]

    def correct_line(self, line: str) -> Tuple[str, List[Correction]]:
        tokens = WORD_RE.findall(line)
        if not tokens:
            return line, []
        best = self._viterbi(tokens)

        out, changes, i = [], [], 0
        pos = 0
        for m in WORD_RE.finditer(line):
            out.append(line[pos:m.start()])
            observed, chosen = m.group(), best[i]
            # Restore the original casing pattern.
            if observed.isupper() and len(observed) > 1:
                final = casing.upper(chosen)
            elif casing.is_upper(observed[0]):
                final = casing.title(chosen)
            else:
                final = chosen
            if final != observed:
                changes.append(Correction(m.start(), observed, final,
                                          self.candidates(observed)[:5]))
            out.append(final)
            pos = m.end()
            i += 1
        out.append(line[pos:])
        return "".join(out), changes

    def correct(self, text: str) -> str:
        return "\n".join(self.correct_line(l)[0] for l in text.split("\n"))

    def correct_verbose(self, text: str) -> Tuple[str, List[Correction]]:
        lines, all_changes = [], []
        for l in text.split("\n"):
            fixed, ch = self.correct_line(l)
            lines.append(fixed)
            all_changes.extend(ch)
        return "\n".join(lines), all_changes

    # -- persistence ------------------------------------------------------

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            {"unigrams": self.unigrams, "bigrams": self.bigrams},
            ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Corrector":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(d["unigrams"], d["bigrams"])

    # -- diagnostics ------------------------------------------------------

    def stats(self) -> dict:
        ambiguous = {k: v for k, v in self.by_class.items() if len(v) > 1}
        return {
            "vocabulary": len(self.unigrams),
            "tokens_trained": self.total,
            "bigram_contexts": len(self.bigrams),
            "ambiguity_classes": len(ambiguous),
            "words_in_ambiguous_classes": sum(len(v) for v in ambiguous.values()),
        }


def damage(text: str) -> str:
    """Apply the OCR channel to clean text — used to build evaluation pairs."""
    return text.translate(FOLD)
