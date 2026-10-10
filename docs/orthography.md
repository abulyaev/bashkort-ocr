# Conversion rules

38 of the 42 Cyrillic letters map one-to-one and need no discussion. This
document covers the four that do, plus the audit tooling for checking the
result.

## 1. `у` and `ү` — vowel or glide

Bashkir writes /w/ with the same letters it writes /u/ and /y/ with, and
disambiguates by position. In a syllable coda the letter is the glide:

| Cyrillic | Latin | |
|---|---|---|
| `тау` | `taw` | mountain |
| `һыу` | `hıw` | water |
| `ауыл` | `awıl` | village |
| `дәүләт` | `däwlät` | state |
| `уҡыу` | `uqıw` | to read |
| `яҙыусы` | `yaźıwsı` | writer |

...but in an onset it is the vowel:

| Cyrillic | Latin | |
|---|---|---|
| `туған` | `tuğan` | relative |
| `күҙ` | `küź` | eye |
| `үҙ` | `üź` | own |
| `буйы` | `buyı` | along |

**Rule.** `у`/`ү` → `w` when the preceding sound is a vowel; otherwise `u`/`ü`.
Fully mechanical, no word list required.

## 2. `е` — iotated or not

| Cyrillic | Latin | |
|---|---|---|
| `ер` | `yer` | earth — word-initial |
| `белем` | `belem` | knowledge — after a consonant |
| `поезд` | `poyezd` | train — after a vowel |
| `гидроэнергетика` | `gidroenergetika` | э after a vowel does **not** iotate |

**Rule.** `е` → `ye` word-initially, after a vowel, or after ъ/ь; otherwise `e`.
`э` is always `e`.

### The interaction that bites

Context must be judged on **what was emitted**, not on the Cyrillic source:

```
кеүек  →  kewek     not  *kewyek
һөйөүе →  höyöwe    not  *höyöwye
```

`ү` in `кеүек` has already become the consonant `w`. The `е` that follows it is
therefore post-consonantal and must not iotate — even though the letter before
it in Cyrillic *looks* like a vowel. Reading the rule off the source text
produces `kewyek`, which is wrong.

## 3. `в` — /v/ or /w/

The only genuinely unpredictable letter. Cyrillic `в` spells:

- **/v/** in Russian loans — `Волга Volga`, `вагон vagon`, `Буранғолов Buranğolov`
- **/w/** in the Arabic stratum — `ваҡыт waqıt`, `вәғәҙә wäğäźä`

Nothing in the spelling distinguishes them, and no phonological rule predicts
them; it is a fact about each word's history. The converter defaults to `v` and
reads overrides from [`data/exceptions.tsv`](../data/exceptions.tsv).

Every `в` is reported by `bashlat audit`, so a document can be triaged in one
pass:

```bash
PYTHONPATH=src python3 -m bashlat audit texts/source/bashqortostan.txt
```

This file is the one part of the project that needs a native ear rather than a
rule. It ships with eight entries and should grow.

## 4. `ц` — and why not `ts`

Written `s`. See [alphabet.md](alphabet.md#3-ц-is-written-s-not-ts) — the short
version is that `ts` collides with real t+s clusters in words like `һөтсөлөк`
and `нефтселәре`.

## Letters that signal a loanword

`ц щ ё ъ ь ф ч в` occur almost exclusively in Russian-mediated vocabulary.
`bashlat audit` flags them, not because the conversion is uncertain, but because
their presence marks a word whose spelling may deserve review — a Latin Bashkort
orthography is an opportunity to naturalise loans rather than transliterate
Russian spelling conventions letter by letter.

Note in particular that `ч` is nearly free: Common Turkic \*č became `с` /s/ in
Bashkir (`сәс` against Tatar `чәч`, `өс` against Turkish `üç`), so /t͡ʃ/ survives
only in loans. 45 occurrences in the whole corpus, against 533 for `в`.

## Cyrillic conventions that are simply dropped

- **ь and ъ.** Bashkir has no palatalisation contrast. `төньяҡ` → `tönyaq`;
  the soft sign exists only to stop a Russian-trained reader palatalising the
  `н`, and Latin `ny` needs no such help.
- **ё vs йо.** Both spell /jo/. Latin writes `yo` for both.
- **э vs е word-initially.** Both are recoverable from position in Latin.

These are why a naive round-trip test is misleading — see below.

## Auditing

### `roundtrip` — is the orthography lossless?

The naive question, *does Cyrillic → Latin → Cyrillic return the original*,
gives a report that is about 98% noise, because Cyrillic spells the same sound
several different ways and a perfect converter still "fails" constantly.

The question that matters is whether the **Latin** form is a fixed point:

```
forward(backward(forward(x))) == forward(x)
```

If it holds, whatever differs between the two Cyrillic strings was a Cyrillic
convention with no phonemic content. If it fails, the Latin orthography has
genuinely merged two distinct words — a defect in the alphabet.

Applying this to the 79,000-character corpus reduced the report from 102 alleged
failures to 7 real ones, all a single bug, now fixed. Current state:

```
0 genuine merge(s), 269 benign difference(s)
```

This test is how the `ц → ts` collision was found.

```bash
cat texts/source/*.txt | PYTHONPATH=src python3 -m bashlat roundtrip -
```

Add `-v` to see the benign differences too.

### `audit` — what did the converter guess?

Lists every letter resolved by anything other than a deterministic rule, grouped
and deduplicated. In practice this means `в`, plus the loanword markers.

```bash
PYTHONPATH=src python3 -m bashlat audit texts/source/ural-batyr.txt
```
