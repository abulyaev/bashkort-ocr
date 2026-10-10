# Build journal

A running record of what was done, what it measured, and what turned out to be
wrong — kept in enough detail to reconstruct the work and to write about it
honestly afterwards.

Everything numbered here was measured, not estimated. Where a claim is an
inference it says so.

---

## The two projects

They share a repository and a corpus but answer different questions.

**A Latin orthography for Bashkort.** Bashkort has been written in Cyrillic
since 1940 and in Jaŋalif, a Latin alphabet, from 1930. The question was what a
modern Latin alphabet should look like, and whether it can be adopted without
losing information.

**OCR for Bashkort.** The question was whether scanned Bashkort books can be
turned into text at all. This one had a surprising answer.

---

## Part one — the alphabet

### Where it started

The request was to reuse the historical Latin alphabet, with German umlauts for
the Bashkort-specific letters. Both instincts turned out to be half right.

Jaŋalif's *sound-to-letter analysis* was sound and is reused. Its *letterforms*
were not: `Ҍ` for /θ/ and `Ь` for /ɯ/ are Cyrillic characters pressed into
service inside a Latin alphabet, awkward enough that Unicode needed
[dedicated proposals in 2008](https://www.unicode.org/L2/L2008/08404r-janalif.pdf)
and [2010](https://www.unicode.org/L2/L2010/10356-n3916-janalif.pdf) to encode
them.

The umlaut instinct was better than the official standard. The
[2024 Common Turkic Alphabet](https://www.turkicacademy.org/en/smi/announcement-common-turkic-alphabet)
uses `Ə` for /æ/. Using `Ä` instead makes the diaeresis mean one consistent
thing across `a/ä  o/ö  u/ü` — so vowel harmony, the backbone of Bashkort
morphology, becomes legible from the page.

### The result

36 letters. Four deliberate departures from the Common Turkic Alphabet, each
with a phonological reason: `Ä` for /æ/, `W` added for /w/, `Ś`/`Ź` for the
interdentals, `Ū` dropped.

### Three findings worth writing about

**Frequency decided the contested letter.** `ҙ`/`ҫ` had no obvious Latin form.
Measuring the converted corpus settled it: **`ź` is eight times more frequent
than `z`** — 2.03% against 0.24%. In Bashkort the interdental is the ordinary
letter and plain `z` is the rare Russian import, because Common Turkic \*z became
/ð/ almost everywhere. That also killed the `dh` digraph option, which would
have been the third most common digraph in the language.

**`ц → ts` was a real bug, caught by an audit.** It collides with the genuine
t+s cluster Bashkort forms before the agent suffix `-сы/-се` — `һөтсөлөк`,
`нефтселәре`. 16 such clusters against 158 instances of `ц` in the corpus.
Writing `ц` as `s` removes the ambiguity, matches pronunciation, and follows
Turkish and Azerbaijani.

**The lossless test had to be reformulated.** "Does Cyrillic → Latin → Cyrillic
return the original" gives a report that is ~98% noise, because Cyrillic spells
the same sound several ways. The question that matters is whether the *Latin*
form is a fixed point: `forward(backward(forward(x))) == forward(x)`. That
reformulation cut 102 alleged failures to 7 real ones — and found the `ц`
collision.

Current: **0 words lose information** across 34.6M characters, in all four ҙ/ҫ
variants. Checked on every test run.

---

## Part two — OCR

### The premise, and why it was wrong

Initial finding: Tesseract has no `bak` model among its 163 languages, and
tested with `-l tat+rus` it produced **zero** Bashkort letters on real scans.
Apple Vision produced zero as well — 3,073 Cyrillic characters recognised, not
one `ә ө ү ң һ ҙ ҫ ҡ ғ`. Conclusion: the gap is real, no open engine can read
Bashkort.

**That conclusion was wrong, and it was my error.** `tat` was chosen because
Tatar is the closest language by name. Its charset was never inspected. It is a
**Latin-only model with no Cyrillic at all**.

`kaz` and `script/Cyrillic` already contained eight of Bashkort's nine letters —
including `ҡ`, U+04A1, whose Unicode name is *CYRILLIC SMALL LETTER BASHKIR KA*.
Working Bashkort OCR had been installed the whole time. Only `ҫ` (U+04AB) is
genuinely absent from every Tesseract charset.

The lesson generalises: **verify a model's character set, never trust its
language label.**

### What does exist commercially

ABBYY FineReader has supported Bashkir
[with dictionary support since version 12](https://help.abbyy.com/en-us/finereader/12/supportedlanguages/),
across 190+ languages. 64 of the source books were OCR'd by it. So Bashkort OCR
existed — proprietary, uninspectable, unembeddable, and one business decision
from disappearing.

Why Tesseract lacks it is not about size. Tesseract ships Faroese (~70k
speakers), Breton (~200k), Maltese (~500k); Bashkort has ~1.1M. The included
Turkic languages are national languages of independent states plus Tatar and
Uyghur. The telling exception is **Turkmen** — a national language, still
missing, and a country with almost no internet presence. The operative variable
is digital corpus availability, not speakers or politics. And there is no gate:
the Tesseract docs state no selection criteria at all. Nobody excluded Bashkort;
nobody added it.

### Ground truth without typing

Tesseract training needs line images paired with their exact text. Most projects
buy that by the hour.

64 of these books carry ABBYY text layers, and `pdftotext -bbox-layout` returns
every line's text **with its bounding box**. Crop the box, pair it with the text:
**65,967 training pairs from 56 books**, 2.9M characters, no typing.

Measured against human ground truth, those labels have roughly **9% of Bashkort
letters wrong**. Good enough to train on — each glyph is labelled correctly ~91%
of the time — and disqualifying for evaluation, where it would measure agreement
with ABBYY rather than correctness. Hence the rule the whole project runs on:
**ABBYY labels train, human labels evaluate, never the reverse.**

The human set covers the seven books ABBYY *couldn't* read — no text layer at
all, faded and old. The hard cases, and the only honest yardstick.

### Training

Fine-tuned from `kaz` on 65,967 lines, 12,000 iterations, CPU-only, ~2 hours on
an M3. Measured on 150 human-verified lines:

| Model | CER | WER | ҙ | **ҫ** | ҡ | ғ | ә | ө | ү | ң | һ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **bak_v2** | **32.0%** | 65.8% | 87 | **44** | 96 | 96 | 97 | 97 | 100 | 90 | 100 |
| bak v1 | 37.2% | 92.3% | 87 | 56 | 97 | 96 | 97 | 99 | 100 | 90 | 94 |
| kaz | 32.5% | **59.8%** | 61 | **0** | 90 | 98 | 97 | 93 | 95 | 97 | 97 |
| rus | 68.0% | 107.1% | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

`ҫ`: **0% → 44%**. A character no OCR engine could read before.

---

## The debugging story

The most useful part of the record. Word error was 92% against Kazakh's 60%
while per-letter recovery was *better* everywhere. Four hypotheses, in order:

| # | Hypothesis | Test | Outcome |
|---|---|---|---|
| 1 | Overfitting at 5,187 iterations | swept every checkpoint | **wrong** — error fell monotonically; last checkpoint was best |
| 2 | Missing word dictionary | rebuilt with a 120,000-word DAWG | **wrong** — output identical to the character |
| 3 | Noisy ABBYY labels | user offered a week of review | **not the constraint** |
| 4 | Missing spaces in `.box` files | diffed with and without whitespace | **correct** |

What found it was measuring the *shape* of the error instead of reasoning about
its cause:

```
CER with spaces      22.4%   (kaz 16.3%)
CER ignoring spaces  11.3%   (kaz 14.1%)   <- better than kaz
tokens produced      0.33x the reference
spaces produced      100 of 548
```

`make_lstmf.py` skipped space characters when writing box files. All 65,967
training lines therefore contained no word breaks, and the model learned that
Bashkort has almost none. Recognition was already better than the best borrowed
model; one line of data preparation was hiding it.

Fixing it: CER 37.2% → 32.0%, WER 92.3% → 65.8%. Training word error fell 24.7%
→ 8.7%.

**A prediction that failed, recorded because it was made in advance.** Having
found the bug, the prediction was 11–13% CER. It came in at 32.0%. Evaluating
with spaces ignored is not the same as training a model to place them — placing
spaces is a separate skill, learned imperfectly.

### Logs lie; artefacts do not

Three silent failures, each caught only by counting files rather than reading
output:

- A slug function stripped non-ASCII, collapsing **every Cyrillic-titled book**
  to the stem `book`. Each overwrote the last: 23 books' worth of pairs lost
  while the log reported a healthy total.
- `--keep_server`, added **to make OCR faster**, deadlocked every batch: the
  child inference server inherited the stdout pipe, and `subprocess.run` waited
  for an EOF that never came. Three restarts were misdiagnosed as stale
  processes and batch size before the flag was suspected.
- An export reported 965 pairs while writing 952 — 13 rows sharing output
  filenames, silently overwriting.

The habit that worked: compare the reported number against the artefact on disk,
every time.

### Other traps, for anyone reproducing this

- **Brew ships `tessdata_fast`.** Integer-quantised models cannot be fine-tuned:
  *"is an integer (fast) model, cannot continue training"*. Fetch the float
  models from `tessdata_best`.
- **`combine_lang_model` needs `radical-stroke.txt`** from the langdata repo,
  even for Cyrillic.
- **`lstm.train` will not read a bare `.gt.txt`** — it needs per-character
  `.box` files, which tesstrain generates separately.
- **macOS stores filenames in NFD.** A name typed into JSON and the same name
  read from disk are different byte strings. 13 of 15 config entries silently
  failed to match before normalisation was added.
- **Surya cannot read isolated line crops.** It is a whole-page model: 343
  seconds for 8 line images, all output empty. Page-level reading of the same
  material took 68 seconds per page and worked.

---

## Reproducing it

```bash
brew install poppler djvulibre tesseract tesseract-lang llama.cpp
python3 -m pip install --user pypdf Pillow fonttools
```

```bash
PYTHONPATH=src python3 tools/align_lines.py --all --limit 30     # 66k training pairs
PYTHONPATH=src python3 tools/make_lstmf.py --src data/lines/auto --out data/train/lstmf
PYTHONPATH=src python3 tools/train_setup.py                      # unicharset + starter
```

Then `lstmtraining --continue_from base/kaz.lstm --old_traineddata
kaz_best.traineddata --traineddata bak/bak.traineddata`, and evaluate with
`tools/evaluate_ocr.py` against verified lines only.

Full tool reference in [tools.md](tools.md); the programme and its phases in
[ocr-plan.md](ocr-plan.md).

---

## Open

- Human-verified set being extended from 952 toward 5,000 lines. Word
  segmentation is the remaining gap and ABBYY's line breaks are what the model
  imitates, so clean human spacing targets it directly.
- Synthetic rendering across the 60 locally-available fonts with full Bashkort
  coverage — never generated; would dilute ABBYY's systematic errors.
- Model selection on held-out error rather than training error.
- Upstream contribution of `bak.traineddata` to `tessdata_best`.

## Claims that would need checking before publication

- That the 65,967-pair set is the largest Bashkort OCR training corpus in
  existence, and the 952-line set the first published Bashkort OCR evaluation
  set. No public Bashkort OCR dataset was found, and no model exists in any open
  engine — but absence of evidence is not proof.
- That `bak.traineddata` is the first Bashkort model in any open OCR engine.
  Searched and not found; not the same as verified.
