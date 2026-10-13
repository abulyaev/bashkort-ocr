# bak.traineddata — Bashkort / Bashkir

## Model card

| | |
|---|---|
| Language | Bashkort (Башҡорт теле), also written Bashkir |
| Code | `bak` (ISO 639-3) |
| Script | Cyrillic, 42 letters |
| Speakers | ~1.1 million; classified vulnerable by UNESCO |
| Training | Two-stage fine-tune from `kaz` |
| Author | Rashit Abulyaev (<https://github.com/abulyaev>) |
| Home | <https://github.com/abulyaev/bashkort-ocr> |
| License | Apache-2.0 |

## Model files

| | size | notes |
|---|---|---|
| [best/bak.traineddata](best/bak.traineddata) | 4.3 MB | float, fine-tunable |
| [fast/bak.traineddata](fast/bak.traineddata) | 1.5 MB | integer |

No legacy model — this is LSTM only.

## Why Bashkort needs its own model

Nine Bashkort letters are not in Russian: **ә ө ү ң һ ҙ ҫ ҡ ғ**. Five of them —
**ҙ ҫ ҡ ғ ң** — differ from an ordinary Russian letter only by a descender
below the baseline (ҙ/з, ҫ/с, ҡ/к, ғ/г, ң/н).

**ҫ** (U+04AB), the voiceless interdental fricative /θ/, appears in no existing
Tesseract unicharset. Among the eight Turkic languages already in tessdata,
none can produce it. Reading Bashkort with an existing model is therefore not a
question of accuracy — the letter cannot be output at all.

## Accuracy

420 held-out lines, transcribed and corrected by a native speaker, excluded
from training. Scored through the `tesseract` CLI, not `lstmeval`.

| model | CER | WER | ҫ | ҙ | ҡ | ғ | ң |
|---|---|---|---|---|---|---|---|
| **bak (best)** | **4.24%** | **14.71%** | **94%** | 97% | 96% | 95% | 94% |
| bak (fast) | 4.94% | 15.57% | — | — | — | — | — |
| kaz | 8.66% | 28.29% | 0% | 81% | 85% | 93% | 89% |
| rus | 22.88% | 73.42% | 0% | 0% | 0% | 0% | 0% |

**On ordinary text the error is lower.** The 420 lines above are specifically
the lines a previous model got wrong, which makes this a conservative floor
rather than a typical page:

| measured on | CER | WER |
|---|---|---|
| corrected lines (hardest; labels written by a human) | 4.24% | 14.71% |
| uncorrected lines (easiest; see caveat) | 0.41% | 2.75% |
| corpus-weighted, 41% corrected / 59% not | ~2.0% | ~7.7% |

Error concentrates in one source. A book of epic poetry whose held-out lines
fall on front matter set in large display capitals runs 19.13% CER; excluding
it the hard set is 2.23% CER / 12.36% WER.

### Caveat on label provenance

Transcription was prefilled with the previous model's reading for speed. On a
line the transcriber accepted unchanged, the ground truth is that model's own
output, so scoring against it is circular. The evaluation set above is drawn
**only from lines the transcriber corrected** — the one category whose label a
human demonstrably wrote — and was held out before training.

No label in this project is fully independent of a model, so these figures are
a bracket rather than a single measurement. This is stated plainly because an
earlier evaluation here, built from "lines no model trained on", turned out to
be 90% uncorrected lines and produced a meaningless 0.14% CER.

## Training procedure

**Base.** `kaz`, selected by measurement rather than linguistic proximity. It
already recognises eight of the nine Bashkort letters at 81–94%, making this an
"add one character to the output layer" problem. An earlier attempt used `tat`
on the assumption that Tatar is the closest relative; Tesseract's `tat` is a
Latin-script model with no Cyrillic, which invalidated that work.

**Stage 1 — 65,967 auto-aligned lines.** Many Bashkort PDFs carry a commercial
OCR text layer. `pdftotext -bbox-layout` gives word boxes; grouping them into
lines and cropping the rendered page at the same coordinates yields image/text
pairs at scale. Noisy, so this stage teaches letterforms only.

**Stage 2 — 1,718 human-corrected lines.** Fixes word segmentation and the
ҙ/ҫ confusions stage 1 cannot teach, because its own labels contain them.

Full pipeline, scripts and per-book results:
<https://github.com/abulyaev/bashkort-ocr>

### Notes that may help others

- **Train only on corrected lines.** Training on all 3,321 verified lines gave
  a worse model than the 1,603 the transcriber had actually changed. Labels
  accepted verbatim from the model ask the network to keep doing what it
  already does, and at volume they drown the lines that disagree.
- **Rank checkpoints through `tesseract`, not `lstmeval`.** lstmeval scores the
  raw LSTM without the dictionary and cannot see word splitting, which costs
  one character but two words. It twice selected a checkpoint that fragmented
  words while real WER rose by four points.
- **The learning curve goes flat early.** 400 corrected lines gave 4.53% CER,
  1,718 gave 4.24%, and the 1,200-line run scored worse than the 800-line one.
  Past a few hundred corrected lines the remaining error was display type and
  page layout, not data volume.

## Training data

Excerpts from seven copyrighted Bashkort books, used with the authors'
permission. Line images and transcriptions are published as release assets at
<https://github.com/abulyaev/bashkort-ocr/releases>.
