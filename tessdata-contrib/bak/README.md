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

157 lines transcribed with **no model output in front of the transcriber** — no
prefilled suggestion, no machine reading of the page — cut from parts of the
books no training data came from. Scored through the `tesseract` CLI, not
`lstmeval`, which cannot see word splitting.

| model | CER | WER | ҫ | ҙ | ҡ | ғ | ң |
|---|---|---|---|---|---|---|---|
| **bak (best)** | **2.43%** | **14.88%** | **17/17** | 98% | 97% | 99% | 100% |
| bak (fast) | 3.17% | 15.27% | — | — | — | — | — |
| kaz | 5.42% | 24.04% | 0/17 | 87% | 87% | 98% | 99% |
| rus | 21.00% | 76.65% | 0/17 | 0% | 0% | 0% | 0% |

`ҫ` is given as a count: the set holds 17 instances, and a percentage would
overstate the precision.

Per book:

| book | lines | CER | WER |
|---|---|---|---|
| drama anthology | 24 | 4.82% | 32.31% |
| epic poetry | 21 | 3.21% | 19.17% |
| historical novel | 14 | 3.17% | 15.49% |
| literary collection | 23 | 2.86% | 16.07% |
| folk tales | 25 | 2.66% | 13.94% |
| prose collection | 25 | 1.07% | 9.58% |
| historical prose | 25 | 0.68% | 4.64% |

A second, deliberately hard set of 420 lines — drawn from lines a previous
model got wrong — gives 4.24% CER / 14.71% WER.

### On how the evaluation set was built

Transcription was prefilled with the previous model's reading for speed, so on
any line accepted unchanged the ground truth would be that model's own output
and scoring against it would be circular. Two earlier evaluation sets here were
compromised that way; one, built from "lines no model trained on", turned out
to be 90% unchanged lines and produced a meaningless 0.14% CER.

The figures above therefore come from lines transcribed blind. The tooling
enforces it: autofill refuses to write a suggestion onto those rows, and
training excludes them.

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
