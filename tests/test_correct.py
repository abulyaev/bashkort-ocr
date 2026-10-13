"""Tests for the OCR post-corrector.

Run with:  python3 tests/test_correct.py
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bashlat.correct import Corrector, damage, fold  # noqa: E402

# Constructed sentences, not excerpts, so the fixtures carry no licence.
TRAIN = [
    "Беҙҙең ауылда ҙур мәктәп бар ине. Уның ҡаршыһында ҡыҙыл алма ағасы үҫә.\n"
    "Был китап башҡорт теленең тарихы менән бәйле. Уның өсөн беҙ күп эш эшләнек.\n"
    "Ҡыҙ ҡулына китап алды. Ҡатын өҫтәл артында ултыра ине.\n"
    "Беҙ һүҙ бирҙек, шуға күрә эште ваҡытында тамамланыҡ.\n"
    "Аҡ ҡайын яурыны буйлап ҡар яуа. Ҡаҙан эргәһендә ут яна.\n"
] * 40


class TestFolding(unittest.TestCase):
    def test_fold_collapses_the_ocr_pairs(self):
        self.assertEqual(fold("ҡыҙ"), "кыз")
        self.assertEqual(fold("өҫтәл"), "өстәл")
        self.assertEqual(fold("ғына"), "гына")
        self.assertEqual(fold("яңы"), "яны")

    def test_fold_is_case_insensitive(self):
        self.assertEqual(fold("Ҡыҙ"), fold("ҡыҙ"))

    def test_damage_matches_fold(self):
        for w in ("ҡыҙ", "һүҙ", "аҫыл", "ғына", "яңы"):
            with self.subTest(w):
                self.assertEqual(damage(w), fold(w))

    def test_unaffected_letters_survive(self):
        # ә ө ү һ are recovered by Surya and must not be folded away.
        self.assertEqual(fold("әсә"), "әсә")
        self.assertEqual(fold("өй"), "өй")
        self.assertEqual(fold("үҙ"), "үз")   # only the ҙ folds
        self.assertEqual(fold("һыу"), "һыу")


class TestCorrection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Corrector.train(TRAIN)

    def test_restores_unambiguous_words(self):
        for clean in ("ҡыҙ", "һүҙ", "өҫтәл", "ҡатын", "беҙҙең"):
            with self.subTest(clean):
                self.assertEqual(self.c.correct(damage(clean)), clean)

    def test_restores_a_whole_sentence(self):
        clean = "Ҡыҙ ҡулына китап алды"
        self.assertEqual(self.c.correct(damage(clean)), clean)

    def test_leaves_clean_text_alone(self):
        clean = "Был китап башҡорт теленең тарихы менән бәйле"
        self.assertEqual(self.c.correct(clean), clean)

    def test_unknown_words_pass_through(self):
        self.assertEqual(self.c.correct("зумбагырк"), "зумбагырк")

    def test_punctuation_and_layout_preserved(self):
        src = damage("Ҡыҙ ҡулына китап алды. Ҡатын өҫтәл артында ултыра ине!")
        out = self.c.correct(src)
        self.assertEqual(out.count("."), 1)
        self.assertEqual(out.count("!"), 1)
        self.assertEqual(len(out.split()), len(src.split()))

    def test_newlines_preserved(self):
        self.assertEqual(self.c.correct("ҡыз\n\nһүз").count("\n"), 2)


class TestCasing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Corrector.train(TRAIN)

    def test_capitalised_word_stays_capitalised(self):
        self.assertEqual(self.c.correct(damage("Ҡыҙ")), "Ҡыҙ")

    def test_all_caps_stays_all_caps(self):
        self.assertEqual(self.c.correct(damage("ҠЫҘ")), "ҠЫҘ")


class TestAmbiguity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Corrector.train(TRAIN)

    def test_candidates_are_offered_for_a_collision(self):
        # ҡаҙан and ҡазан fold to the same string.
        cands = self.c.candidates("казан")
        self.assertGreaterEqual(len(cands), 1)
        self.assertTrue(all(fold(x) == "казан" for x in cands))

    def test_corrections_are_reported_with_alternatives(self):
        _, changes = self.c.correct_verbose(damage("Ҡыҙ ҡулына китап алды"))
        self.assertTrue(changes)
        self.assertTrue(all(ch.candidates for ch in changes))


class TestPersistence(unittest.TestCase):
    def test_round_trips_through_disk(self):
        import tempfile
        c = Corrector.train(TRAIN)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            c.save(p)
            loaded = Corrector.load(p)
        self.assertEqual(loaded.correct(damage("ҡыҙ")), "ҡыҙ")
        self.assertEqual(loaded.stats()["vocabulary"], c.stats()["vocabulary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
