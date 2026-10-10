"""Tests for the Bashkort transliterator.

Run with:  python3 tests/test_translit.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bashlat import ReverseTransliterator, Transliterator, roundtrip_report  # noqa: E402
from bashlat import casing  # noqa: E402


class TestCoreMapping(unittest.TestCase):
    """Words taken from the ba.wikipedia fixture in texts/source/."""

    CASES = [
        ("Башҡорт", "Başqort"),
        ("теле", "tele"),
        ("төрки", "törki"),
        ("халҡының", "xalqınıñ"),
        ("телдәренең", "teldäreneñ"),
        ("тармағы", "tarmağı"),
        ("ҡыпсаҡ", "qıpsaq"),
        ("төркөмөнөң", "törkömönöñ"),
        ("төркөмсәһенә", "törkömsähenä"),
        ("ҡарай", "qaray"),
        ("диалекттары", "dialekttarı"),
        ("көнсығыш", "könsığış"),
        ("көнбайыш", "könbayış"),
        ("һәм", "häm"),
        ("Республикаһының", "Respublikahınıñ"),
        ("булып", "bulıp"),
        ("тора", "tora"),
    ]

    def setUp(self):
        self.tr = Transliterator()

    def test_words(self):
        for cyr, latin in self.CASES:
            with self.subTest(cyr):
                self.assertEqual(self.tr.convert(cyr), latin)


class TestGlideRule(unittest.TestCase):
    """у/ү spell /w/ in coda position — the rule that makes дәүләт däwlät."""

    CASES = [
        ("тау", "taw"),
        ("һыу", "hıw"),
        ("ауыл", "awıl"),
        ("һауа", "hawa"),
        ("дәүләт", "däwlät"),
        ("уҡыу", "uqıw"),
        # ...but not in onset position:
        ("туған", "tuğan"),
        ("буйы", "buyı"),
        ("күҙ", "küź"),
        ("үҙ", "üź"),
        ("университет", "universitet"),
    ]

    # Once у/ү has surfaced as the consonant w, a following е must NOT iotate.
    # Reading context off the Cyrillic instead of the emitted Latin gives
    # *kewyek here — the bug this class pins down.
    GLIDE_THEN_E = [
        ("кеүек", "kewek"),
        ("һөйөүе", "höyöwe"),
        ("белеүсе", "belewse"),
        ("ҡыҙыҡһыныуы", "qıźıqhınıwı"),
        ("яҙыусы", "yaźıwsı"),
    ]

    def setUp(self):
        self.tr = Transliterator()

    def test_glide(self):
        for cyr, latin in self.CASES:
            with self.subTest(cyr):
                self.assertEqual(self.tr.convert(cyr), latin)

    def test_glide_blocks_following_iotation(self):
        for cyr, latin in self.GLIDE_THEN_E:
            with self.subTest(cyr):
                self.assertEqual(self.tr.convert(cyr), latin)


class TestIotation(unittest.TestCase):
    CASES = [
        ("ер", "yer"),        # word-initial е is /je/
        ("белем", "belem"),   # after a consonant it is plain /e/
        ("эш", "eş"),
        ("көньяҡ", "könyaq"),  # ь is redundant once н and я are separate letters
    ]

    def setUp(self):
        self.tr = Transliterator()

    def test_iotation(self):
        for cyr, latin in self.CASES:
            with self.subTest(cyr):
                self.assertEqual(self.tr.convert(cyr), latin)


class TestInterdentals(unittest.TestCase):
    WORDS = ["һүҙ", "ҡыҙ", "беҙ", "аҫыл", "өҫтәл", "яҙ", "иҫке"]

    EXPECTED = {
        "acute":     ["hüź", "qıź", "beź", "aśıl", "öśtäl", "yaź", "iśke"],
        "stroke":    ["hüđ", "qıđ", "beđ", "aŧıl", "öŧtäl", "yađ", "iŧke"],
        "icelandic": ["hüð", "qıð", "beð", "aþıl", "öþtäl", "yað", "iþke"],
        "digraph":   ["hüdh", "qıdh", "bedh", "athıl", "öthtäl", "yadh", "ithke"],
    }

    def test_all_variants(self):
        for variant, expected in self.EXPECTED.items():
            tr = Transliterator(variant=variant)
            for cyr, latin in zip(self.WORDS, expected):
                with self.subTest(variant=variant, word=cyr):
                    self.assertEqual(tr.convert(cyr), latin)

    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError):
            Transliterator(variant="umlaut")


class TestCasing(unittest.TestCase):
    def setUp(self):
        self.tr = Transliterator()

    def test_dotted_and_dotless_i(self):
        self.assertEqual(casing.upper("i"), "İ")
        self.assertEqual(casing.upper("ı"), "I")
        self.assertEqual(casing.lower("İ"), "i")
        self.assertEqual(casing.lower("I"), "ı")

    def test_python_builtin_would_be_wrong(self):
        # Documents exactly why casing.py exists.
        self.assertNotEqual("i".upper(), casing.upper("i"))
        self.assertNotEqual("İ".lower(), casing.lower("İ"))

    def test_digraph_title_case(self):
        self.assertEqual(self.tr.convert("Ер"), "Yer")
        self.assertEqual(self.tr.convert("ЕР"), "YER")
        self.assertEqual(self.tr.convert("ер"), "yer")

    def test_word_casing(self):
        self.assertEqual(self.tr.convert("Иҙел"), "İźel")
        self.assertEqual(self.tr.convert("йыл"), "yıl")
        self.assertEqual(self.tr.convert("ЙЫЛ"), "YIL")
        self.assertEqual(self.tr.convert("ИҪ"), "İŚ")


class TestExceptions(unittest.TestCase):
    def test_arabic_stratum_v_is_w(self):
        tr = Transliterator()
        self.assertEqual(tr.convert("ваҡыт"), "waqıt")
        self.assertEqual(tr.convert("Ваҡыт"), "Waqıt")
        self.assertEqual(tr.convert("ВАҠЫТ"), "WAQIT")

    def test_stem_rules_cover_the_whole_paradigm(self):
        # Bashkir is agglutinative: a whole-word lexicon would list ваҡыт and
        # still mis-convert ваҡытта. Stems must match suffixed forms.
        tr = Transliterator()
        for cyr, latin in [
            ("ваҡыт", "waqıt"),
            ("ваҡытта", "waqıtta"),
            ("ваҡытында", "waqıtında"),
            ("ваҡланып", "waqlanıp"),
            ("вағыраҡ", "wağıraq"),
            ("ватырһың", "watırhıñ"),
            ("вәзирҙәрен", "wäzirźären"),
        ]:
            with self.subTest(cyr):
                self.assertEqual(tr.convert(cyr), latin)

    def test_russian_loan_v_stays_v(self):
        tr = Transliterator()
        self.assertEqual(tr.convert("Волга"), "Volga")
        self.assertEqual(tr.convert("Буранғолов"), "Buranğolov")

    def test_folklore_corpus_has_no_unresolved_v(self):
        corpus = Path(__file__).resolve().parents[1] / "texts" / "source"
        tr = Transliterator()
        for name in ["ural-batyr-akiat.txt", "aqbuzat-epos.txt"]:
            path = corpus / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            unresolved = [a for a in tr.audit(text) if a.letter == "в"]
            with self.subTest(name):
                self.assertEqual(unresolved, [], f"{len(unresolved)} unresolved в")

    def test_v_is_flagged_as_a_guess(self):
        tr = Transliterator()
        flagged = [a.letter for a in tr.audit("Волга")]
        self.assertIn("в", flagged)

    def test_exception_words_are_not_flagged(self):
        tr = Transliterator()
        self.assertEqual(tr.audit("ваҡыт"), [])


class TestPassthrough(unittest.TestCase):
    def setUp(self):
        self.tr = Transliterator()

    def test_punctuation_and_layout_survive(self):
        src = "Төп диалекттары: көнсығыш, төньяҡ-көнбайыш һәм көньяҡ."
        out = self.tr.convert(src)
        self.assertEqual(out, "Töp dialekttarı: könsığış, tönyaq-könbayış häm könyaq.")

    def test_newlines_preserved(self):
        self.assertEqual(self.tr.convert("ер\n\nтау"), "yer\n\ntaw")

    def test_non_cyrillic_untouched(self):
        self.assertEqual(self.tr.convert("UNESCO 1928"), "UNESCO 1928")


class TestReverse(unittest.TestCase):
    def setUp(self):
        self.fwd = Transliterator()
        self.bwd = ReverseTransliterator()

    def test_roundtrip_of_core_vocabulary(self):
        words = [
            "Башҡорт", "теле", "халҡының", "дәүләт", "һыу", "тау", "ауыл",
            "һүҙ", "ҡыҙ", "аҫыл", "өҫтәл", "ер", "белем", "йыл", "күҙ",
            "тармағы", "ҡыпсаҡ", "төркөмөнөң", "һәм", "уҡыу", "тора",
        ]
        for word in words:
            with self.subTest(word):
                self.assertEqual(self.bwd.convert(self.fwd.convert(word)), word)

    def test_glide_harmony_is_recoverable(self):
        # w must resolve back to у or ү according to the preceding vowel.
        self.assertEqual(self.bwd.convert("taw"), "тау")
        self.assertEqual(self.bwd.convert("däwlät"), "дәүләт")
        self.assertEqual(self.bwd.convert("hıw"), "һыу")

    def test_soft_sign_loss_is_the_expected_difference(self):
        self.assertEqual(self.fwd.convert("көньяҡ"), "könyaq")
        self.assertEqual(self.bwd.convert("könyaq"), "көняҡ")


class TestLoanLetters(unittest.TestCase):
    """ц is written s. A ts digraph would collide with genuine t+s clusters."""

    def setUp(self):
        self.tr = Transliterator()

    def test_ts_is_written_s(self):
        self.assertEqual(self.tr.convert("цирк"), "sirk")
        self.assertEqual(self.tr.convert("революция"), "revolyusiya")
        self.assertEqual(self.tr.convert("станция"), "stansiya")

    def test_genuine_t_plus_s_survives(self):
        # These are why ц cannot be ts: the agent suffix -сы/-се after a
        # t-final stem produces a real т+с cluster.
        self.assertEqual(self.tr.convert("һөтсөлөк"), "hötsölök")
        self.assertEqual(self.tr.convert("нефтселәре"), "neftseläre")

    def test_t_plus_s_is_not_confusable_with_ts(self):
        self.assertNotEqual(self.tr.convert("һөтсөлөк"), self.tr.convert("һөцөлөк"))


class TestNonIotatedE(unittest.TestCase):
    """э after a vowel must stay distinct from е after a vowel."""

    def setUp(self):
        self.fwd = Transliterator()
        self.bwd = ReverseTransliterator()

    def test_forward_distinguishes(self):
        self.assertEqual(self.fwd.convert("гидроэнергетика"), "gidroenergetika")
        self.assertEqual(self.fwd.convert("Поэзия"), "Poeziya")
        # ...whereas е in the same slot iotates:
        self.assertEqual(self.fwd.convert("поезд"), "poyezd")

    def test_reverse_recovers_e_oborotnoye(self):
        self.assertEqual(self.bwd.convert("gidroenergetika"), "гидроэнергетика")
        self.assertEqual(self.bwd.convert("poyezd"), "поезд")


class TestCorpusIsLossless(unittest.TestCase):
    """The headline claim: no word in the corpus loses information."""

    def test_no_genuine_merges_in_corpus(self):
        corpus_dir = Path(__file__).resolve().parents[1] / "texts" / "source"
        files = sorted(corpus_dir.glob("*.txt"))
        if not files:
            self.skipTest("no corpus present")

        text = "\n".join(f.read_text(encoding="utf-8") for f in files)
        self.assertGreater(len(text), 10000, "corpus unexpectedly small")

        for variant in ["acute", "stroke", "icelandic", "digraph"]:
            with self.subTest(variant=variant):
                merges = [r for r in roundtrip_report(text, variant=variant) if not r.benign]
                self.assertEqual(merges, [], f"{len(merges)} merge(s): {merges[:3]}")


class TestAlphabetTable(unittest.TestCase):
    def test_letter_count_and_order(self):
        tr = Transliterator()
        letters = tr.ordered_alphabet()
        self.assertEqual(len(letters), 36)
        lowers = [low for _, low in letters]
        self.assertEqual(lowers[:3], ["a", "ä", "b"])
        self.assertEqual(lowers[lowers.index("s") + 1], "ś")
        self.assertEqual(lowers[-1], "ź")

    def test_every_letter_has_a_case_pair(self):
        tr = Transliterator()
        for upper, low in tr.ordered_alphabet():
            with self.subTest(low):
                self.assertEqual(casing.lower(upper), low)
                self.assertEqual(casing.upper(low), upper)


if __name__ == "__main__":
    unittest.main(verbosity=2)
