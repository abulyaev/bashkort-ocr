# Tools reference

Everything this project provides: commands, modules, data files, and how they
fit together.

---

## Install

Core requires nothing but Python 3.9+.

```bash
PYTHONPATH=src python3 -m bashlat alphabet
```

Book handling needs external tools. Without them, `detect` and `corpus` still
work on plain text but cannot open scans.

```bash
brew install poppler djvulibre tesseract tesseract-lang
```

```bash
python3 -m pip install --user pypdf
```

| Tool | Provides | Needed for |
|---|---|---|
| `poppler` | `pdftotext`, `pdfinfo`, `pdftoppm` | PDF text and rasterising |
| `djvulibre` | `djvutxt`, `djvused`, `ddjvu` | DjVu text and rasterising |
| `tesseract` + `tesseract-lang` | OCR | scanned books with no text layer |
| `pypdf` | fallback PDF reader | PDFs poppler chokes on |

Check what is present:

```bash
PYTHONPATH=src python3 -m bashlat detect --check-tools --no-ocr texts/source
```

Surya (Phase 1 OCR) lives in a separate environment so it cannot disturb the
core, which stays dependency-free:

```bash
brew install llama.cpp && uv venv --python 3.12 .venv-ocr && VIRTUAL_ENV=.venv-ocr uv pip install surya-ocr
```

---

## The pipeline

```
  books (pdf, djvu, epub, fb2, docx, doc)
        │
        │  extract.py        text layer, else OCR; flags broken CMaps
        ▼
  raw text
        │
        │  detect.py         bashkort / tatar / russian / uncertain
        │  corpus.py         screen, clean, filter by chunk, apply overrides
        ▼
  texts/corpus/*.txt         34.7M chars, 87 books
        │
        ├──► correct.py      train the OCR post-corrector
        │
        └──► translit.py     Cyrillic → Latin
                 │
                 │  reverse.py     Latin → Cyrillic, round-trip audit
                 ▼
           texts/latin/*.txt
```

---

## Commands

All invoked as `PYTHONPATH=src python3 -m bashlat <command>`.

### `convert` — Cyrillic to Latin

```bash
PYTHONPATH=src python3 -m bashlat convert texts/source/ural-batyr.txt
```

Reads a file or stdin. `--variant` selects the ҙ/ҫ letters: `acute` (default,
ź/ś), `stroke` (đ/ŧ), `icelandic` (ð/þ), `digraph` (dh/th).

### `reverse` — Latin to Cyrillic

```bash
PYTHONPATH=src python3 -m bashlat reverse texts/latin/ural-batyr.txt
```

Exists mainly to make `roundtrip` possible.

### `roundtrip` — is the orthography lossless?

```bash
cat texts/source/*.txt | PYTHONPATH=src python3 -m bashlat roundtrip -
```

Converts every word to Latin and back, reporting only genuine merges. Tests
whether the Latin form is a fixed point, not whether the Cyrillic came back
byte-identical — see [orthography.md](orthography.md#auditing). `-v` also lists
benign differences.

### `audit` — what did the converter guess?

```bash
PYTHONPATH=src python3 -m bashlat audit texts/source/ural-batyr.txt
```

Lists every letter resolved by something other than a deterministic rule,
grouped and deduplicated. In practice: `в`, plus loanword markers.

### `compare` — see all four ҙ/ҫ variants

```bash
PYTHONPATH=src python3 -m bashlat compare texts/source/ural-batyr.txt
```

### `alphabet` — print the letter table

```bash
PYTHONPATH=src python3 -m bashlat alphabet --variant stroke
```

### `detect` — is this book in Bashkort?

```bash
PYTHONPATH=src python3 -m bashlat detect texts/source
```

Accepts files or a directory. Reads PDF, DjVu, EPUB, FB2, DOCX, DOC, TXT.

| Flag | Effect |
|---|---|
| `-v` | show the word evidence behind each verdict |
| `--no-ocr` | skip OCR; scanned books report `unknown` |
| `--check-tools` | report which external tools are installed |

Verdicts: `bashkort`, `tatar`, `russian`, `turkic-other`, `uncertain`,
`unknown`. Sources: `text`, `ocr`, `text?` (encoding suspect), `none`.

### `correct` — restore letters OCR could not produce

```bash
PYTHONPATH=src python3 -m bashlat correct --report scanned.txt
```

Needs a trained model at `data/models/corrector.json`. `--report N` lists the
first N corrections on stderr with their rejected alternatives.

---

## Modules

### `alphabet.json` + `translit.py` — the orthography

`Transliterator` converts Cyrillic to Latin. 38 of 42 letters are a table
lookup; the four that are not:

- `у`/`ү` → `w` after a vowel, else `u`/`ü`
- `е` → `ye` word-initially or after a vowel, else `e`
- `в` → `v` by default, `w` for stems listed in `exceptions.tsv`

Context is judged on what was *emitted*, not the Cyrillic source, so `кеүек`
gives `kewek` rather than `kewyek`.

```python
from bashlat import Transliterator
Transliterator().convert("Башҡорт теле")     # 'Başqort tele'
Transliterator(variant="stroke").convert("һүҙ")  # 'hüđ'
```

### `casing.py` — dotted and dotless i

Python, JavaScript, Java and Go all get `i`→`İ` and `I`→`ı` wrong. Every case
operation in the project goes through here. Fourteen lines, no dependencies.

```python
from bashlat import casing
casing.upper("il")      # 'İL'   — not 'IL'
casing.lower("QIŹ")     # 'qıź'  — not 'qiź'
```

### `reverse.py` — Latin to Cyrillic and the audit

`roundtrip_report` classifies each difference as a genuine merge or a Cyrillic
convention with no phonemic content (ь/ъ, ё vs йо, э vs е).

### `detect.py` — language identification

Combines two evidence streams. Characters: `ҙ ҫ ҡ ғ` are Bashkort and not
Tatar; `җ` is Tatar and not Bashkort. Function words: the languages differ
exactly where they are most frequent — менән/белән, өсөн/өчен, был/бу, ине/иде.

Scored in chunks so a Bashkort novel with a Russian preface is still Bashkort.

**Under OCR the character stream is discarded.** Tesseract has no `bak` model,
so scans are read with `tat`, whose charset cannot emit `ҙ ҫ ҡ ғ` — it rewrites
them to Tatar shapes. Their absence is then an artefact of the scan, not
evidence, so only OCR-safe word pairs are used.

```python
from bashlat import detect
v = detect(text)
v.lang, v.confidence, v.distribution
```

### `extract.py` — getting text out of books

`extract()` samples the body for detection; `extract_full()` takes everything
for corpus building. Both accept `skip_pages`.

Two behaviours worth knowing:

- **Samples the interior.** Copyright pages and УДК/ББК codes are in Russian
  even in Bashkort books; reading page 1 is the most common way to misclassify.
- **`suspect_text_layer()`** catches PDFs whose ToUnicode CMap is corrupt. They
  extract cleanly, read like prose, and are missing exactly the Turkic letters —
  so a Bashkort book reports as confident Russian. Flagged `text?` and
  re-read by OCR where that helps.

Also strips `<binary>`, `<style>`, `<script>` *contents* — FB2 embeds cover art
as base64, which survives naive tag-stripping as a million Latin characters.

### `correct.py` — the OCR post-corrector

Noisy channel. The damage is known rather than learned:

```
ҙ→з   ҫ→с   ҡ→к   ң→н   ғ↔г
```

Both the observed text and the lexicon are folded into the same ambiguity
classes; context picks among the candidates by bigram score. Most words have
exactly one candidate and are never guessed at.

Restores those five letters only. `ә ө ү һ` are recovered by Surya, and adding
them would triple the ambiguity — see [ocr-plan.md](ocr-plan.md).

```python
from bashlat.correct import Corrector, damage
c = Corrector.train(texts)              # 8 seconds on 35M chars
c.correct("Кыз кулына китап алды")      # 'Ҡыҙ ҡулына китап алды'
c.save(Path("data/models/corrector.json"))
```

### `corpus.py` — screening and cleaning

Screens every book, reports why anything was dropped, and never discards
silently. Failure modes: `wrong-language`, `broken-encoding`, `low-yield`,
`garbage`, `script-anomaly`, `mixed-language`.

Human overrides live in `data/books.json` and are never written by code.
Filenames are matched through `book_key()`, which normalises to NFC — macOS
stores filenames decomposed, so a name typed into JSON and the same name read
from disk are different byte strings despite looking identical.

---

## Data files

| File | Owner | Contents |
|---|---|---|
| `data/alphabet.json` | code | 36 letters, IPA, collation, Cyrillic map, four ҙ/ҫ variants |
| `data/exceptions.tsv` | **human** | stems whose `в` is /w/ — needs a native ear |
| `data/books.json` | **human** | per-book exclude / force / skip_pages / role |
| `data/models/corrector.json` | generated | trained corrector — rebuild, do not edit |

`data/books.json` keys:

```json
{
  "book.pdf": {
    "exclude": true,        // drop entirely
    "force": true,          // keep despite quality flags
    "skip_pages": 7,        // ignore leading front matter
    "role": "ocr",          // no text layer; Phase 3 material, not LM training
    "note": "why"
  }
}
```

---

## Rebuilding

```bash
rm -rf texts/corpus && PYTHONPATH=src python3 -c "
import sys; sys.path.insert(0,'src')
from pathlib import Path; from bashlat.corpus import build
build(Path('texts/source'), Path('texts/corpus'))"
```

Then retrain the corrector from the rebuilt corpus.

---

## Tests

```bash
for t in tests/*.py; do python3 "$t"; done
```

| Suite | Tests | Covers |
|---|---|---|
| `test_translit.py` | 30 | mapping, glide rule, iotation, casing, all four variants, corpus losslessness |
| `test_detect.py` | 16 | Bashkort vs Tatar vs Russian, abstention, OCR safety, broken layers |
| `test_correct.py` | 15 | folding, restoration, casing, ambiguity, persistence |

`test_translit.py` asserts **zero genuine merges** across the whole corpus, in
all four variants — the headline correctness claim, checked on every run.

---

## OCR tools

Standalone scripts in `tools/`, run with `PYTHONPATH=src python3 tools/<name>`.

| Script | What it does |
|---|---|
| `ocr.py` | read a scanned book end to end — Surya, then the corrector |
| `evaluate_ocr.py` | score any Tesseract model against the verified set: CER, WER, per-letter recall |
| `align_lines.py` | crop line images from PDFs with a text layer and pair them with their text — 65,967 training pairs, no typing |
| `prepare_transcription.py` | cut line images from books with **no** text layer, for human transcription |
| `extend_transcription.py` | add more crops to the transcription set — **appends only**, never rebuilds |
| `page_reference.py` | read each source page whole, as reference beside the line being typed |
| `transcribe.py` | local browser tool at `localhost:8765`; `--review` revisits flagged lines, `--export` writes tesstrain pairs |
| `flag_review.py` | rank transcribed lines by how likely they contain an error |
| `make_lstmf.py` | line pairs → `.lstmf` training files, in parallel |
| `train_setup.py` | unicharset and starter model for a training run |

### The OCR pipeline

```
books with a text layer          books without one
        │                                │
   align_lines.py                prepare_transcription.py
        │                        extend_transcription.py
        │                        page_reference.py
        │                                │
        │                          transcribe.py  ← human
        ▼                                ▼
  65,967 ABBYY-labelled            5,202 crops, human-verified
  lines  → TRAINING                → EVALUATION (and clean training)
        │                                │
        └──────────► make_lstmf.py ◄─────┘
                          │
                    train_setup.py
                          │
                    lstmtraining          fine-tune from kaz
                          │
                   bak.traineddata
                          │
                   evaluate_ocr.py        against the verified set only
```

The split is the important part. ABBYY's labels have roughly **9% of Bashkort
letters wrong** — fine for bulk training, disqualifying for measurement, because
scoring against them would measure agreement with ABBYY rather than
correctness. Only human-verified lines are ever used to evaluate.

### Artefacts

| Path | Contents |
|---|---|
| `data/lines/auto/` | 65,967 line pairs from text-layer books |
| `data/lines/human/` | 5,202 crops + `manifest.json` (transcriptions, reference text, review flags) |
| `data/lines/verified/` | exported human-verified tesstrain pairs |
| `data/train/bak_v2.traineddata` | the trained model |
| `data/train/output2/` | training checkpoints |

`manifest.json` is the single source of truth for transcription work and is
written on every save. `manifest.backup.json` is a snapshot taken before the
set was extended.

## Document index

| Document | What it is |
|---|---|
| [alphabet.md](alphabet.md) | the specification — letters, rationale, comparison, Unicode |
| [orthography.md](orthography.md) | conversion rules and the audit method |
| [keyboard.md](keyboard.md) | iOS and Android keyboard specification |
| [reading-guide.ru.md](reading-guide.ru.md) | Как читать — guide in Russian for Bashkort speakers |
| [draft-law.md](draft-law.md) | draft legislation adopting the alphabet |
| [ocr-plan.md](ocr-plan.md) | the three-phase OCR programme and its results |
| **tools.md** | this file |
