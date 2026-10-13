# Bashkort OCR

A Tesseract model for **Bashkort** (Башҡорт теле, ISO 639-3 `bak`), a Turkic
language of about 1.1 million speakers. No open-source OCR engine has shipped a
Bashkort model. This is the first.

```bash
tesseract page.png out -l bak
```

## Why it did not exist

Bashkort is written in a 42-letter Cyrillic alphabet. Nine of its letters are
not in Russian: **ә ө ү ң һ ҙ ҫ ҡ ғ**. Five of those (**ҙ ҫ ҡ ғ ң**) differ
from an ordinary Russian letter *only by a descender below the baseline*:

| Bashkort | Russian | differs by |
|---|---|---|
| ҙ | з | a descending tail |
| ҫ | с | a descending tail |
| ҡ | к | a descending leg |
| ғ | г | a crossbar and tail |
| ң | н | a descending hook |

A scanner that crops a line too tightly deletes the information that
distinguishes the language from Russian. And `ҫ` (U+04AB), the voiceless
interdental fricative /θ/ that among Turkic languages only Bashkort has,
appears in no Tesseract character set at all. An existing model cannot
represent these letters, so it cannot output them.

Run Russian over a Bashkort page and all nine letters come back at 0% recall.

## Results

Measured on 157 lines transcribed with no model output in front of the
transcriber: no prefilled suggestion, no machine reading of the page. The
labels owe nothing to any model. Pages came from parts of the books no training
data was drawn from.

| model | CER | WER | ҫ | ҙ | ҡ | ғ | ң |
|---|---|---|---|---|---|---|---|
| **`bak` (this model)** | **2.43%** | **14.88%** | **17/17** | 98% | 97% | 99% | 100% |
| `kaz` — closest substitute | 5.42% | 24.04% | 0/17 | 87% | 87% | 98% | 99% |
| `rus` | 21.00% | 76.65% | 0/17 | 0% | 0% | 0% | 0% |

Less than half the character error of the nearest alternative, and the only
model that produces `ҫ` at all. `ҫ` is reported as a count because the set
holds 17 instances; the percentage would overstate the precision.

| book | lines | CER | WER |
|---|---|---|---|
| Башҡорт драматургияһы антологияһы | 24 | 4.82% | 32.31% |
| Боронғо башҡорт ҡобайырҙары | 21 | 3.21% | 19.17% |
| Ҡара яу | 14 | 3.17% | 15.49% |
| Йәдкәр | 23 | 2.86% | 16.07% |
| Башҡорт халыҡ әкиәттәре | 25 | 2.66% | 13.94% |
| doc257928583 | 25 | 1.07% | 9.58% |
| Ҡолой кантон | 25 | 0.68% | 4.64% |

A second, larger set of 420 lines gives 4.24% CER / 14.71% WER. Those are
lines a previous model got wrong, so it is a deliberately hard subset.

Word error is the weak spot, and it is concentrated in drama: speaker
attributions, stage directions and dash-led dialogue, where the characters come
out right and the word boundaries do not. Character error is worst on the epic
poetry, whose front matter is set in large display capitals the model has never
seen (`СӘҒИТОВ` read as `СОҒИТОВ`).

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
closest relative. But Tesseract's `tat` is a Latin-script model with no
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

### More transcription stopped helping at around 500 lines

Training the same pipeline on nested subsets of the corrected lines, scored on
the same held-out set:

| corrected lines | CER | WER |
|---|---|---|
| 400 | 4.53% | 16.73% |
| 800 | 4.45% | 15.81% |
| 1,200 | 4.51% | 17.31% |
| 1,718 | 4.24% | 14.71% |

Quadrupling the data moved character error by 0.29 points, and the 1,200-line
run scored worse than the 800-line one, so some of that is run-to-run noise.
The curve is flat.

I am stating this plainly because the intuition runs hard the other way. This
project spent a long stretch collecting more transcriptions on the assumption
that volume was the constraint. It was not. Past a few hundred corrected lines
the remaining error came from display type the model had never seen, from
dramatic layout, and from page images that had been cropped badly before
training started. Typing more body text fixes none of that.

If you are building OCR for a low-resource language, measure your learning
curve early. A few hundred carefully corrected lines may get you most of what
transcription can give.

### Three findings that changed the outcome

**Only corrected lines train the model.** Transcription was prefilled with the
previous model's reading to make it fast. Training on all 3,321 verified lines
produced a *worse* model than training on the 1,603 the transcriber had
actually changed. Two thirds of the data was the model's own output fed back:
correct labels, most likely, but they ask the network to keep doing what it
already does, and at that volume they drown the lines that disagree. Half the
data, better model.

**Rank checkpoints on the real pipeline, not `lstmeval`.** `lstmeval` scores
the raw LSTM with no dictionary. It chose a checkpoint that splits words,
turning `Гөлбәғиҙә` into `Гөл бә ғи ҙ ә`. That costs one character but two words, so
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
transcriber accepted unchanged, the ground truth is the model's own output.
Scoring a model against its own output is circular, and it flatters whichever
model did the prefilling.

An earlier version of this eval sampled lines no model had trained on. But
training consumes the *corrected* lines, so what was left was 90% lines
accepted verbatim, two books at 100%, and the model scored 0.14% CER on
them. That number was meaningless and is not reported here.

This was fixed by measuring it properly. 175 lines were cut from pages no
training data came from and transcribed with the suggestion box empty and the
page reading suppressed; 157 were legible enough to label. `tools/autofill.py`
refuses to touch them and `tools/train_human.py` excludes them from training,
so they stay independent. The headline figures come from that set.

Two estimates made before that set existed are recorded here, because one held
and one did not. Weighting the hard and easy sets by their share of the corpus
predicted roughly 2.0% CER and 7.7% WER. The real figures are 2.43% and 14.88%.
Character error came close. Word error was out by a factor of two, because on a
line accepted verbatim the label is the model's own output, so its word error is
near zero by construction and dragged the weighted estimate down. The optimistic
bound turned out to be an artifact. Measured word error matched the hard set
almost exactly, 14.88% against 14.71%.

Scoring:

```bash
python3 tools/eval_holdout.py --list eval_blind.list --per-book bak   # unbiased
python3 tools/eval_holdout.py --per-book bak                          # hard subset
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

Stage 1 needs `tessdata_best`. Homebrew ships `tessdata_fast`, which is
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

- Display and title type is weak; the one book dominated by it runs 19% CER
- Drama layout (speaker attributions, stage directions) drives word error
- More transcription will not fix either; the learning curve is flat
- Word error (14.88%) is high relative to character error; drama layout is the
  main driver
- Not yet submitted to `tessdata_contrib`. A prepared submission, including
  an integer `fast` build, is in [tessdata-contrib/](tessdata-contrib/)

## License

Apache-2.0, matching Tesseract, for the model and the code. The books the model
was trained on remain their authors' property.

## Credits

Built by [Rashit Abulyaev](https://github.com/abulyaev). The Bashkort language
is classified as vulnerable by UNESCO; the authors who allowed their books to be
used made this possible.
