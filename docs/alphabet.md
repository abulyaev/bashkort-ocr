# The alphabet

## What it is

36 letters, in collation order:

| | | | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A a | Ä ä | B b | C c | Ç ç | D d | E e | F f | G g | Ğ ğ | H h | X x |
| I ı | İ i | J j | K k | Q q | L l | M m | N n | Ñ ñ | O o | Ö ö | P p |
| R r | S s | Ś ś | Ş ş | T t | U u | Ü ü | V v | W w | Y y | Z z | Ź ź |

Ordering follows Azerbaijani convention (`x` after `h`, `q` after `k`), with the
three added letters slotted next to their base: `ä` after `a`, `ś` after `s`,
`ź` after `z`.

## Full correspondence

| Latin | IPA | Cyrillic | Notes |
|---|---|---|---|
| A a | /ɑ/ | а | |
| Ä ä | /æ/ | ә | front counterpart of `a` |
| B b | /b/ | б | |
| C c | /d͡ʒ/ | — | marginal; loans and proper nouns. Kept for Common Turkic compatibility |
| Ç ç | /t͡ʃ/ | ч | Russian loans almost exclusively — see below |
| D d | /d/ | д | |
| E e | /e/ | е, э | written `ye` word-initially and after a vowel |
| F f | /f/ | ф | loans |
| G g | /ɡ/ | г | front-vowel words |
| Ğ ğ | /ʁ/ | ғ | back-vowel counterpart of `g` |
| H h | /h/ | һ | from Common Turkic \*s: `һин ~ sen`, `һыу ~ su` |
| X x | /χ/ | х | |
| I ı | /ɯ/ | ы | dotless |
| İ i | /i/ | и | dotted, including uppercase `İ` |
| J j | /ʒ/ | ж | |
| K k | /k/ | к | front-vowel words |
| Q q | /q/ | ҡ | back-vowel counterpart of `k` |
| L l | /l/ | л | |
| M m | /m/ | м | |
| N n | /n/ | н | |
| Ñ ñ | /ŋ/ | ң | |
| O o | /o/ | о | |
| Ö ö | /ø/ | ө | front counterpart of `o` |
| P p | /p/ | п | |
| R r | /r/ | р | |
| S s | /s/ | с, ц | absorbs ц — see below |
| **Ś ś** | /θ/ | ҫ | Bashkir-specific |
| Ş ş | /ʃ/ | ш | |
| T t | /t/ | т | |
| U u | /u/ | у | becomes `w` after a vowel |
| Ü ü | /y/ | ү | becomes `w` after a vowel |
| V v | /v/ | в | Russian loans |
| W w | /w/ | у, ү, в | native glide |
| Y y | /j/ | й | |
| Z z | /z/ | з | |
| **Ź ź** | /ð/ | ҙ | Bashkir-specific |

Cyrillic ъ and ь are not represented. Cyrillic ё, ю, я are `yo`, `yu`, `ya`;
щ is `şç`.

## Vowel harmony, and why the alphabet is shaped this way

Bashkir morphology runs on vowel harmony: every suffix has two shapes, selected
by the vowel class of the stem. An orthography that makes the classes visible is
doing real work for the reader, not just transcribing sounds.

| back | `a` | `o` | `u` | `ı` |
|---|---|---|---|---|
| **front** | `ä` | `ö` | `ü` | `i` |

Three of the four pairs are marked by the diaeresis, and the fourth by the dot.
So the rule reduces to one visual cue — *marked = front* — and harmony can be
read off the page:

| stem | plural | class |
|---|---|---|
| `bala` бала | `balalar` балалар | back |
| `keşe` кеше | `keşelär` кешеләр | front |
| `kitap` китап | `kitaptar` китаптар | back |
| `tel` тел | `teldär` телдәр | front |

This is the whole argument for `ä` over CTA's `ə`: the diaeresis participates in
a system, and `ə` does not.

### Consonant harmony follows the same axis

Two consonant pairs alternate with the vowel class rather than contrasting
freely. They are the same underlying consonant in different harmonic contexts:

| front-vowel words | back-vowel words |
|---|---|
| `k` — `kitap` китап, `keşe` кеше | `q` — `qul` ҡул, `xalıq` халыҡ |
| `g` — `göl` гөл, `belem` белем | `ğ` — `ağas` ағас, `tarmağı` тармағы |

Writing them `k/q` and `g/ğ` — rather than, say, `k/k̢` — keeps them looking
like the distinct letters they are in the reader's mind, while the vowels around
them make the pattern obvious.

## What was inherited, and what was not

Bashkir already had a Latin alphabet. Jaŋalif was introduced in 1930 and
abolished in 1940. Its sound-to-letter analysis was sound; its letterforms were
a product of 1920s typesetting politics:

| Cyrillic | IPA | Jaŋalif | This alphabet |
|---|---|---|---|
| ҙ | /ð/ | Đ đ | Ź ź |
| ҫ | /θ/ | **Ҍ ҍ** | Ś ś |
| ә | /æ/ | Ə ə | Ä ä |
| ө | /ø/ | Ɵ ɵ | Ö ö |
| ү | /y/ | Y y | Ü ü |
| ы | /ɯ/ | **Ь ь** | I ı |
| ғ | /ʁ/ | Ƣ ƣ | Ğ ğ |
| ң | /ŋ/ | Ŋ ŋ | Ñ ñ |
| ж | /ʒ/ | Ƶ ƶ | J j |
| ч | /t͡ʃ/ | C c | Ç ç |

Two of those are not Latin letters at all. `Ҍ` is the Cyrillic semisoft sign and
`Ь` is the Cyrillic soft sign, both pressed into service inside a Latin
alphabet. They were awkward enough that Unicode needed
[dedicated proposals in 2008](https://www.unicode.org/L2/L2008/08404r-janalif.pdf)
and [2010](https://www.unicode.org/L2/L2010/10356-n3916-janalif.pdf) to encode
the Jaŋalif repertoire. Reviving them today would put Bashkort outside every
standard keyboard layout and most font families.

So: inherit the analysis, replace the glyphs.

## Deviations from the Common Turkic Alphabet

The 2024 CTA is `A B C Ç D E Ə F G Ğ H X I İ J K Q L M N Ñ O Ö P R S Ş T U Ū Ü V Y Z`.
This alphabet differs in four places, each deliberately.

### 1. `Ä ä` instead of `Ə ə`

Bashkir vowels come in back/front pairs, and vowel harmony is the backbone of
the morphology — every suffix has two shapes selected by the stem.

```
back    a    o    u    ı
front   ä    ö    ü    i
```

Writing the front series with a diaeresis makes the diacritic mean exactly one
thing across the whole system, so harmony is visible on the page:
`bala → balalar` against `keşe → keşelär`. `ə` is unrelated in shape to `a` and
destroys that pattern for no gain. It is also absent from most keyboard layouts,
whereas `ä` is a keystroke away on any layout that already produces `ö` and `ü`
— which this alphabet needs regardless.

Turkmen and Gagauz, both Latin-script Turkic languages, made the same choice.

### 2. `W w` added

CTA has no `W` and assigns /w/ to `V`. Bashkir cannot afford that merge:

| | | |
|---|---|---|
| native /w/ | `тау` | `taw` |
| | `һыу` | `hıw` |
| | `дәүләт` | `däwlät` |
| | `ауыл` | `awıl` |
| loan /v/ | `Волга` | `Volga` |
| | `Буранғолов` | `Buranğolov` |

/w/ is extremely frequent — it is the regular coda realisation of у and ү — and
collapsing it into `v` would make the orthography misrepresent the language.

### 3. `ц` is written `s`, not `ts`

A `ts` digraph collides with genuine t+s clusters, which Bashkir produces
regularly when the agent suffix `-сы/-се` attaches to a t-final stem:

| | | |
|---|---|---|
| `һөтсөлөк` | `hötsölök` | dairy farming — real т+с |
| `нефтселәре` | `neftseläre` | its oil workers — real т+с |

The corpus contains 16 such clusters against 158 instances of ц. Writing ц as
`s` removes the ambiguity, matches how Bashkir speakers actually pronounce the
letter, and follows Turkish and Azerbaijani practice: `цирк sirk`,
`революция revolyusiya`, `станция stansiya`.

### 4. `Ū ū` not adopted

Bashkir has no phonemic vowel length.

## The interdentals

`ҙ` /ð/ and `ҫ` /θ/ exist in no other Turkic language, so the CTA has nothing to
inherit from and every option is a fresh decision. Four are implemented; select
with `--variant`.

| variant | ҙ | ҫ | `һүҙ` | `аҫыл` | `өҫтәл` |
|---|---|---|---|---|---|
| `acute` (default) | ź | ś | `hüź` | `aśıl` | `öśtäl` |
| `stroke` | đ | ŧ | `hüđ` | `aŧıl` | `öŧtäl` |
| `icelandic` | ð | þ | `hüð` | `aþıl` | `öþtäl` |
| `digraph` | dh | th | `hüdh` | `adhıl` | `öthtäl` |

The default is `acute`, for two reasons.

**It encodes a real relationship.** Bashkir's interdentals descend from the
Common Turkic sibilants — \*z → /ð/ and \*s → /θ/:

| Turkish | Tatar | Bashkir | |
|---|---|---|---|
| söz | süz | һүҙ | `hüź` |
| kız | кыз | ҡыҙ | `qıź` |
| biz | без | беҙ | `beź` |
| asıl | асыл | аҫыл | `aśıl` |
| üst | өст | өҫ | `öś` |

An acute on `z` and `s` therefore means *the Bashkir reflex of this sibilant*,
in the same way the diaeresis in `ä` means *the front counterpart of this vowel*.
The Cyrillic letters encode the same analysis — they are `з` and `с` with a
descender. `đ`/`ŧ` instead imply descent from \*d and \*t, which is false.

**It stays legible across the Turkic world.** A Turkish or Kazakh reader
encountering `hüź` recovers `söz` immediately. `hüđ` and `hüð` tell them nothing.

The counter-argument for `stroke` is real and worth stating: `Đ` is what Bashkir
Jaŋalif actually used, and `Đ`/`Ŧ` is what the CTA's Bashkir column lists today.
If institutional alignment matters more than etymology or cross-Turkic
legibility, that is the defensible choice, and `--variant stroke` produces it.

`digraph` is documented but not recommended: it breaks one-sound-one-letter,
collides with genuine t+h and d+h across morpheme boundaries, and produces
strings like `öthtäl` that no one can parse.

## Against other Turkic Latin alphabets

| Sound | This | Turkish | Azerbaijani | Turkmen | CTA 2024 | Jaŋalif 1930 |
|---|---|---|---|---|---|---|
| /æ/ | **ä** | — | ə | ä | ə | ə |
| /ø/ | ö | ö | ö | ö | ö | ɵ |
| /y/ | ü | ü | ü | ü | ü | y |
| /ɯ/ | ı | ı | ı | **y** | ı | ь |
| /i/ | i | i | i | i | i | i |
| /q/ | **q** | — | q | — | q | q |
| /ʁ/ | ğ | ğ | ğ | — | ğ | ƣ |
| /ŋ/ | **ñ** | — | — | ň | ñ | ŋ |
| /x/ | **x** | — | x | h | x | x |
| /h/ | h | h | h | h | h | h |
| /ʒ/ | j | j | j | ž | j | ƶ |
| /t͡ʃ/ | ç | ç | ç | ç | ç | c |
| /ʃ/ | ş | ş | ş | ş | ş | ş |
| /j/ | y | y | y | **ý** | y | j |
| /w/ | **w** | — | — | w | *(v)* | v |
| /θ/ | **ś** | — | — | — | *(ŧ)* | ҍ |
| /ð/ | **ź** | — | — | — | *(đ)* | đ |

Bold marks where this alphabet needs a letter Turkish does not have. The
overlap with Turkish is 29 of 36 letters, and with Azerbaijani 31 — a reader of
either can decode most of a Bashkort page on sight.

## Letter frequency

Measured over the 131,564 letters of converted corpus in `texts/latin/`:

| | | | | | |
|---|---|---|---|---|---|
| a | 12.31% | s | 2.48% | ñ | 1.11% |
| ı | 6.73% | h | 2.12% | ü | 0.97% |
| n | 6.43% | d | 2.09% | x | 0.48% |
| r | 6.40% | o | 2.07% | v | 0.39% |
| e | 6.18% | **ź** | **2.03%** | **ś** | **0.33%** |
| ä | 5.89% | ş | 1.82% | f | 0.26% |
| t | 5.81% | p | 1.71% | **z** | **0.24%** |
| l | 5.73% | ğ | 1.61% | j | 0.14% |
| y | 3.75% | ö | 1.55% | ç | 0.04% |
| i | 3.18% | w | 1.37% | c | 0.03% |
| b | 2.97% | g | 1.24% | | |
| m | 2.80% | | | | |
| q | 2.74% | | | | |
| u | 2.52% | | | | |
| k | 2.49% | | | | |

Three things fall out of this that bear on the design.

**`ź` is eight times more common than `z`** — 2.03% against 0.24%. In Bashkir the
interdental is the ordinary letter and plain `z` is the rare loan. This is the
sound law visible in a frequency table: Common Turkic \*z became /ð/ almost
everywhere, so `z` survives mainly in Russian vocabulary. The letter for /ð/
therefore needs to be comfortable and unobtrusive at high frequency — an
argument against `dh`, which would be the third most common digraph in the
language.

**`ś` and `ź` are wildly asymmetric.** /θ/ is a sixth as frequent as /ð/, because
\*s more often became `h` (`һин ~ sen`, `һыу ~ su`) than `ś`. Both still need
letters, but only `ź` is under real typographic load.

**`ç` and `c` together account for 0.07%** — 90 occurrences in 131,564 letters.
This confirms that /t͡ʃ/ is vestigial in Bashkir, and that `ç` was nearly free to
reassign. It was kept for /t͡ʃ/ anyway, because reassigning it would have broken
cross-Turkic legibility for a saving of 90 characters.

## Typing

Every letter is reachable on a standard layout with a dead key or long-press:

| | macOS | Windows US-Intl | iOS |
|---|---|---|---|
| ä ö ü | `⌥U` + vowel | `"` + vowel | long-press |
| ş ç | `⌥C` for ç | `,` + letter | long-press |
| ğ ñ | `⌥N` for ñ | `~` + letter | long-press |
| ś ź | `⌥E` + letter | `'` + letter | long-press |
| ı | `⌥`-layer | — | long-press `i` |

A dedicated Bashkort layout would be worth producing; nothing here requires one.

## Casing, and why `İ` cannot be dropped

`İ` is not a separate letter. It is the uppercase of ordinary `i`. The reason it
is not plain `I` is that `I` is already the uppercase of `ı` /ɯ/.

The pairing is easy to get backwards, because collation puts the back vowel
first and its capital `I` looks like the ordinary English letter. It is not:

| Cyrillic | IPA | lowercase | UPPERCASE | |
|---|---|---|---|---|
| **и** | /i/ | `i` | `İ` | `ил` → `il` → `İL` |
| **ы** | /ɯ/ | `ı` | `I` | `ҡыҙ` → `qıź` → `QIŹ` |

The dot belongs to the letter and survives in both directions. English discards
it when capitalising; Bashkort cannot, because its presence or absence *is* the
phonemic distinction:

```
тарихи  →  tarixi  →  TARİXİ     historical
тарихы  →  tarixı  →  TARİXI     its history
```

**Both vowels are needed.** и and ы are separate phonemes in opposite harmony
classes, and they carry grammatical weight. The corpus contains 2,249 и against
4,194 ы, and collapsing them merges productive suffixes:

| | | |
|---|---|---|
| `тарихи` | `tarixi` | historical — Arabic adjectival `-и` |
| `тарихы` | `tarixı` | its history — 3rd person possessive `-ы` |
| `ижади` | `ijadi` | creative |
| `ижады` | `ijadı` | its creativity |

**So the capital must be distinct too.** If `i` uppercased to `I`, then `I` would
stand for either vowel, and the distinction would vanish wherever capitals
appear. Measured on the corpus:

| | |
|---|---|
| distinct words | 3,965 |
| containing `i` or `ı` — ambiguous in ALL CAPS without `İ` | **2,213 (56%)** |
| beginning with `i` or `ı` — ambiguous sentence-initially | 212 |

Headlines, book covers, signage and titles are exactly where all-caps appears, so
this is not an edge case. Turkish, Azerbaijani, Kazakh, Crimean Tatar and the
CTA all carry `İ` for the same reason.

### The alternative, and why it was rejected

Turkmen avoids the dotted capital entirely: it writes /ɯ/ as `y` and moves /j/ to
`ý`, leaving `i` with a normal `I`. Turkmen also uses `ä` and `w`, so it is
otherwise close to this alphabet. Applied to Bashkir:

```
Turkish-style   Ural batır — başqort xalqınıñ qomartqıhı, bıwından-bıwınğa
                tapşırğan bay xazina — awıź-tel ijadınıñ hoqlanğıs ölgöhö.

Turkmen-style   Ural batyr — başqort xalqynyñ qomartqyhy, bywyndan-bywynğa
                tapşyrğan baý xazina — awyź-tel ijadynyñ hoqlanğys ölgöhö.
```

Bashkir is ы-heavy, so `y` ends up carrying most of the vowel load while also
being the shape readers associate with a consonant — `bywyndan-bywynğa` is
markedly harder to parse than `bıwından-bıwınğa`. It would also put an acute on
1,039 instances of /j/, and break the international spelling of `batır`.

Keeping `İ` costs nothing at the keyboard and one small module in software.

### The software cost

Case conversion is locale-sensitive: `i`→`İ`, `ı`→`I`, `İ`→`i`, `I`→`ı`. Python,
JavaScript and most default library routines get this wrong and will silently
corrupt text — `iś` uppercased naively becomes `IŚ`, which reads back as `ıś`, a
different word. Every case operation in this project goes through
`src/bashlat/casing.py`; anything built on top of it should do the same.

## Technical appendix

### Codepoints

Only eleven letters fall outside ASCII. All are in Latin-1 Supplement or Latin
Extended-A — the two most widely supported blocks after ASCII itself:

| Letter | Upper | Lower | Block |
|---|---|---|---|
| Ä ä | U+00C4 | U+00E4 | Latin-1 Supplement |
| Ç ç | U+00C7 | U+00E7 | Latin-1 Supplement |
| Ñ ñ | U+00D1 | U+00F1 | Latin-1 Supplement |
| Ö ö | U+00D6 | U+00F6 | Latin-1 Supplement |
| Ü ü | U+00DC | U+00FC | Latin-1 Supplement |
| Ğ ğ | U+011E | U+011F | Latin Extended-A |
| İ  | U+0130 | — | Latin Extended-A |
| ı  | — | U+0131 | Latin Extended-A |
| Ś ś | U+015A | U+015B | Latin Extended-A |
| Ş ş | U+015E | U+015F | Latin Extended-A |
| Ź ź | U+0179 | U+017A | Latin Extended-A |

The variant letters, for reference: Đ U+0110 / đ U+0111, Ŧ U+0166 / ŧ U+0167,
Ð U+00D0 / ð U+00F0, Þ U+00DE / þ U+00FE.

**Every letter is precomposed.** No combining marks are required anywhere in the
orthography, which means text normalises to a single codepoint per letter under
NFC, sorts predictably, and survives naive substring operations. This was a hard
constraint during design and it is why `z̈`/`s̈` were rejected outright for the
interdentals — no precomposed forms exist, so they would have required
U+0308 COMBINING DIAERESIS and broken all three properties.

Store and exchange text as **UTF-8, NFC**.

### Collation

```
a ä b c ç d e f g ğ h x ı i j k q l m n ñ o ö p r s ś ş t u ü v w y z ź
```

Following Azerbaijani convention: `x` after `h`, `q` after `k`. The three added
letters sort immediately after their base — `ä` after `a`, `ś` after `s`,
`ź` after `z`. Note that `ı` precedes `i`, which is standard across Turkic Latin
alphabets and will surprise a default Unicode collator.

`Transliterator.ordered_alphabet()` returns this sequence.

### Casing

| lower | UPPER | |
|---|---|---|
| `i` | `İ` | **not** `I` |
| `ı` | `I` | |
| `İ` | `i` | **not** `i` + U+0307 |
| `I` | `ı` | **not** `i` |

Everything else round-trips correctly through standard library routines. These
four cases do not, in Python, JavaScript, Java, Go, or shell `tr`. Use a
Turkish/Azerbaijani locale where one is available (`tr-TR`, `az-AZ`), or an
explicit table — `src/bashlat/casing.py` is fourteen lines and has no
dependencies.

The failure is silent and lossy, so it is worth testing for explicitly:

```python
assert "i".upper() != casing.upper("i")   # Python gives I, correct is İ
assert "İ".lower() != casing.lower("İ")   # Python gives i + U+0307
```

### Locale identifiers

`ba-Latn` for the Latin orthography, against `ba-Cyrl` for the existing
Cyrillic one. The bare tag `ba` should be treated as Cyrillic for now.

## Further reading

- [orthography.md](orthography.md) — the conversion rules and the audit tooling
- [reading-guide.ru.md](reading-guide.ru.md) — reading guide in Russian, for Bashkir speakers
- [Bashkir alphabet](https://en.wikipedia.org/wiki/Bashkir_alphabet) — Jaŋalif tables
- [Common Turkic alphabet](https://en.wikipedia.org/wiki/Common_Turkic_alphabet)
- Unicode proposals for Jaŋalif letters, [2008](https://www.unicode.org/L2/L2008/08404r-janalif.pdf) and [2010](https://www.unicode.org/L2/L2010/10356-n3916-janalif.pdf)
