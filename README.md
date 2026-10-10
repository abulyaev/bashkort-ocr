# Bashkort OCR

A Tesseract model for **Bashkort** (Башҡорт теле, ISO 639-3 `bak`), a Turkic
language of about 1.1 million speakers. No open-source OCR engine has shipped a
Bashkort model. This is the first.

```bash
tesseract page.png out -l bak
```

## Why it did not exist

Bashkort is written in a 42-letter Cyrillic alphabet. Nine of its letters are
not in Russian: **ә ө ү ң һ ҙ ҫ ҡ ғ**. Five of those — **ҙ ҫ ҡ ғ ң** — differ
from an ordinary Russian letter *only by a descender below the baseline*:

| Bashkort | Russian | differs by |
|---|---|---|
| ҙ | з | a descending tail |
| ҫ | с | a descending tail |
| ҡ | к | a descending leg |
| ғ | г | a crossbar and tail |
| ң | н | a descending hook |

So a scanner that crops a line too tightly deletes exactly the information that
distinguishes the language from Russian. And `ҫ` (U+04AB) — the voiceless
interdental fricative /θ/, which among Turkic languages only Bashkort has —
appears in **no Tesseract character set at all**. Reading Bashkort with an
existing model is not a matter of accuracy; the letters are unrepresentable.

Run Russian over a Bashkort page and every one of the nine letters comes back
at **0%** recall.

## Results

Measured on 420 held-out lines the model never saw, each transcribed and
corrected by a native speaker. See [Evaluation](#evaluation) for why this is
the hardest possible test and what the real-page number is.

| model | CER | WER | ҫ | ҙ | ҡ | ғ | ң |
|---|---|---|---|---|---|---|---|
| **`bak` (this model)** | **4.24%** | **14.71%** | **94%** | 97% | 96% | 95% | 94% |
| `kaz` — closest substitute | 8.66% | 28.29% | 0% | 81% | 85% | 93% | 89% |
| `rus` | 22.88% | 73.42% | 0% | 0% | 0% | 0% | 0% |

Half the character error and half the word error of the nearest alternative,
and the only model that can produce `ҫ` at all.

**On ordinary pages the error is lower.** The 420 lines above are the subset a
previous model got *wrong*, so they are a conservative floor, not typical text:

| measured on | CER | WER |
|---|---|---|
| corrected lines — hardest, trustworthy labels | 4.24% | 14.71% |
| uncorrected lines — easiest, see caveat below | 0.41% | 2.75% |
| **corpus-weighted (41% corrected / 59% not)** | **~2.0%** | **~7.7%** |

Error is concentrated in one book. `Боронғо башҡорт ҡобайырҙары` runs 19.13%
CER against 2.13–3.66% for everything else; its held-out lines land on front
matter set in large display capitals the model has not learned (`СӘҒИТОВ` read
as `СОҒИТОВ`). Excluding it, the hard set is **2.23% CER / 12.36% WER**.

| book | lines | CER | WER |
|---|---|---|---|
| Боронғо башҡорт ҡобайырҙары | 60 | 19.13% | 32.36% |
| Башҡорт халыҡ әкиәттәре | 60 | 3.66% | 18.45% |
| Ҡара яу | 60 | 2.59% | 13.30% |
| Башҡорт драматургияһы антологияһы | 60 | 2.47% | 16.86% |
| Йәдкәр | 60 | 2.18% | 12.93% |
| Ҡолой кантон | 60 | 2.13% | 10.47% |
| doc257928583 | 60 | 0.39% | 2.09% |

## Install

Drop `bak.traineddata` into your tessdata directory:

```bash
curl -LO https://github.com/abulyaev/bashkort-ocr/releases/latest/download/bak.traineddata
mv bak.traineddata "$(dirname "$(find /usr/local /opt/homebrew /usr/share -name eng.traineddata 2>/dev/null | head -1)")"
```

Or place it by hand: `/opt/homebrew/share/tessdata` on macOS with Homebrew,
`/usr/share/tesseract-ocr/*/tessdata` on most Linux distributions. Confirm with
`tesseract --list-langs`, which should now include `bak`. Then:

```bash
tesseract scan.png out -l bak           # a page
tesseract line.png - -l bak --psm 7     # a single line
```

Use `--psm 13` for line crops that include slivers of neighbouring lines; `--psm 7`
returns nothing when an image holds more than one line.

## How it was built

Two stages, both fine-tuning rather than training from scratch.

**Base model.** `kaz` (Kazakh), chosen by measurement, not by name. It already
recognises eight of the nine Bashkort letters at 81–94%, so the job was adding
one character to the output layer rather than learning Cyrillic from nothing.
An earlier attempt used `tat` (Tatar) on the reasoning that Tatar is the
closest relative — but Tesseract's `tat` is a *Latin-script* model with no
Cyrillic at all, which invalidated a whole phase of work before the error was
caught.

**Stage 1 — letterforms, from 65,967 auto-aligned lines.** Many Bashkort PDFs
carry a text layer from commercial OCR. Running `pdftotext -bbox-layout` gives
word boundary boxes; grouping those into lines and cropping the rendered page
at the same coordinates produces image/text pairs at scale with no typing. The
text layer has errors, so this stage teaches letter shapes, not correctness.

**Stage 2 — correctness, from human-verified lines.** 5,193 lines across seven
books, transcribed by a native speaker through a purpose-built browser tool.
This is the stage that fixes word segmentation and the ҙ/ҫ confusions the
auto-aligned data cannot teach, because its own labels contain them.

### Three findings that changed the outcome

**Only corrected lines train the model.** Transcription was prefilled with the
previous model's reading to make it fast. Training on all 3,321 verified lines
produced a *worse* model than training on the 1,603 the transcriber had
actually changed. Two thirds of the data was the model's own output fed back:
correct labels, most likely, but they ask the network to keep doing what it
already does, and at that volume they drown the lines that disagree. Half the
data, better model.

**Rank checkpoints on the real pipeline, not `lstmeval`.** `lstmeval` scores
the raw LSTM with no dictionary. It chose a checkpoint that splits words —
`Гөлбәғиҙә` into `Гөл бә ғи ҙ ә` — which costs one character but two words, so
it barely registered the fault while real-world WER went from 11.35% to 15.72%.
Re-ranking every checkpoint through `tesseract` itself picked a different one,
less than half as deep.

**Box files must contain spaces.** The `.box` generator skipped space
characters. The model learned from text with no word breaks, and no amount of
extra data fixed it. One line of code, and it was diagnosed only after three
wrong hypotheses about the word-error gap.

More of these, including the ones that cost real work, are in
[docs/journal.md](docs/journal.md).

## Evaluation

The evaluation set is the part of this project most worth scrutinising, because
the obvious way to build it is wrong.

Every line was transcribed with a model's suggestion prefilled. On a line the
transcriber accepted unchanged, **the ground truth is the model's own output**.
Scoring a model against its own output is circular, and it flatters whichever
model did the prefilling.

An earlier version of this eval sampled lines no model had trained on. But
training consumes the *corrected* lines, so what was left was 90% lines
accepted verbatim — two books were 100% — and the model scored 0.14% CER on
them. That number was meaningless and is not reported here.

The set used now is drawn from **corrected lines only**, the single kind whose
label a human demonstrably wrote, and is held out *before* training. The cost
is that corrected lines are by construction the ones the model got wrong, so
4.24% reads worse than any real page. It is a floor. The companion set of
uncorrected lines gives the optimistic bound, 0.41%, and the truth lies between.

**Known limitation.** No label in this project is fully independent of a model,
so every figure here is a bracket rather than a measurement. Closing that
requires a few hundred lines transcribed with prefill disabled. That work is
not done, and the numbers should be read with it in mind.

Scoring:

```bash
python3 tools/eval_holdout.py --per-book bak
python3 tools/eval_holdout.py --list eval_verbatim.list bak
```

## Reproducing

```bash
brew install tesseract tesseract-lang poppler          # or your package manager
pip install pillow

python3 tools/prepare_transcription.py                 # line crops from PDFs
python3 tools/transcribe.py                            # browser tool, localhost:8765
python3 tools/transcribe.py --export                   # image/label pairs
python3 tools/make_eval_set.py --per-book 60           # freeze the held-out set
python3 tools/train_human.py --edited-only --tag v1    # stage 2
python3 tools/eval_holdout.py --per-book v1
```

Stage 1 needs `tessdata_best` — Homebrew ships `tessdata_fast`, which is
integer-quantised and cannot be fine-tuned at all. `combine_lang_model` also
wants `radical-stroke.txt` from the `langdata` repository, which is not
mentioned where you would expect.

[docs/tools.md](docs/tools.md) documents each tool.

## Data

The training images and transcriptions are published as release assets rather
than committed, so they can be withdrawn without rewriting history. They are
excerpts from copyrighted books used with the authors' permission for building
this model.

If you are one of those authors and want your work removed, open an issue and
the asset will be deleted.

## Also here

The repository carries the Latin-alphabet work this project grew out of:
a 36-letter Latin orthography for Bashkort with a round-trip-lossless mapping
to Cyrillic, verified across a 34.6-million-character corpus.
See [docs/alphabet.md](docs/alphabet.md) and [docs/orthography.md](docs/orthography.md).

## Status

Usable, and better than every alternative, but not finished. Known gaps:

- Display and title type is weak — the one book dominated by it runs 19% CER
- Drama layout (speaker attributions, stage directions) drives word error
- No label is independent of a model; see [Evaluation](#evaluation)
- Not yet submitted upstream to `tessdata_best`

## License

Apache-2.0, matching Tesseract, for the model and the code. The books the model
was trained on remain their authors' property.

## Credits

Built by [Rashit Abulyaev](https://github.com/abulyaev). The Bashkort language
is classified as vulnerable by UNESCO; the authors who allowed their books to be
used made this possible.
