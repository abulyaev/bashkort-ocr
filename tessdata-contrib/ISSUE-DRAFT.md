<!--
Draft issue for https://github.com/tesseract-ocr/tessdata_contrib/issues
Title: Add bak (Bashkort / Bashkir) — Cyrillic, LSTM, fine-tuned from kaz
Nothing has been posted. Review, edit, then open it yourself.
-->

## Add `bak` (Bashkort / Bashkir)

I would like to contribute a Tesseract model for **Bashkort** (Башҡорт теле,
ISO 639-3 `bak`), a Turkic language with roughly 1.1 million speakers,
classified as vulnerable by UNESCO. There is currently no `bak` model in
tessdata, tessdata_best or tessdata_fast, while eight other Turkic languages
are present (`aze`, `aze_cyrl`, `kaz`, `kir`, `tat`, `tur`, `uzb`, `uzb_cyrl`).

### Why an existing model will not do

Nine Bashkort letters are absent from Russian: ә ө ү ң һ ҙ ҫ ҡ ғ. Five of them
— ҙ ҫ ҡ ғ ң — differ from a Russian letter only by a descender below the
baseline (ҙ/з, ҫ/с, ҡ/к, ғ/г, ң/н).

**ҫ (U+04AB) is in no existing Tesseract unicharset**, so no current model can
emit it at all. On held-out Bashkort text, `rus` scores 0% recall on all nine
letters and `kaz` scores 0% on ҫ.

### Accuracy

420 held-out lines, corrected by a native speaker, excluded from training,
scored through the `tesseract` CLI:

| model | CER | WER | ҫ recall |
|---|---|---|---|
| **bak (best)** | **4.24%** | **14.71%** | **94%** |
| bak (fast) | 4.94% | 15.57% | — |
| kaz | 8.66% | 28.29% | 0% |
| rus | 22.88% | 73.42% | 0% |

Those lines are specifically the ones a previous model got wrong, so they are a
conservative floor. Corpus-weighted, ordinary pages run nearer 2.0% CER and
7.7% WER. The model card documents how the evaluation set was built and why,
including a label-provenance caveat I would rather state than hide: every line
was transcribed with a model's suggestion prefilled, so the eval uses only
lines the transcriber corrected, and the numbers are a bracket rather than a
single measurement.

### What I would submit

Following the layout of the existing entries:

```
bak/
├── README.md              model card, accuracy, training procedure
├── best/bak.traineddata   4.3 MB, float
└── fast/bak.traineddata   1.5 MB, integer
```

No legacy model; this is LSTM only.

Training was a two-stage fine-tune from `kaz`: 65,967 auto-aligned lines from
PDF text layers for letterforms, then 1,718 human-corrected lines for
correctness. Pipeline, scripts, per-book results and the training data are
public under Apache-2.0 at <https://github.com/abulyaev/bashkort-ocr>, which I
maintain, so the contrib entry can point there for anything that should not
live in this repository.

Training images are excerpts from copyrighted Bashkort books used with the
authors' written permission.

Happy to adjust the layout or the model card to whatever you prefer before
opening a PR.
