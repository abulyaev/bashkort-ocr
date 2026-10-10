"""Tests for the Bashkort language detector.

Run with:  python3 tests/test_detect.py
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bashlat import detect  # noqa: E402
from bashlat.extract import suspect_text_layer  # noqa: E402

# Short constructed passages, not excerpts, so the fixtures carry no licence.
BASHKORT = (
    "Был китап башҡорт теленең тарихы менән бәйле. Уның өсөн беҙ күп "
    "материал йыйҙыҡ. Улар ҙур эш башҡарҙы, ләкин һуң булды. Ошо хеҙмәт "
    "яҡшы кеүек, әммә етешһеҙлектәре лә бар ине. Беҙҙең халыҡ өсөн был "
    "бик мөһим. Уның һүҙҙәре аңлайышлы, шуға күрә улар яңы юл асты. "
    "Тик ваҡыт етмәне, шул сәбәпле эш тамамланманы әле. "
) * 4

TATAR = (
    "Бу китап татар теленең тарихы белән бәйле. Аның өчен без күп "
    "материал җыйдык. Алар зур эш башкарды, ләкин соң булды. Шушы хезмәт "
    "яхшы кебек, әмма җитешсезлекләре дә бар иде. Безнең халык өчен бу "
    "бик мөһим. Аның сүзләре аңлаешлы, шуңа күрә алар яңа юл ачты. "
) * 4

RUSSIAN = (
    "Эта книга связана с историей языка. Для неё мы собрали много "
    "материала. Они проделали большую работу, но было уже поздно. "
    "Этот труд хорош, однако у него есть недостатки, которые были "
    "заметны. Для нашего народа это очень важно, потому что они "
    "открыли новый путь. Если бы не время, работа была бы закончена. "
) * 4

LATIN_BASHKORT = (
    "Bıl kitap başqort teleneñ tarixı menän bäyle. Unıñ ösön beź küp "
    "material yıyźıq. Ular źur eş başqarźı, läkin huñ buldı. Oşo xeźmät "
    "yaqşı kewek, ämmä yeteşheźlektäre lä bar ine. Beźźeñ xalıq ösön bıl "
    "bik möhim. Unıñ hüźźäre añlayışlı, şuğa kürä ular yañı yul astı. "
) * 4


class TestLanguageSeparation(unittest.TestCase):
    def test_bashkort(self):
        self.assertEqual(detect(BASHKORT).lang, "bashkort")

    def test_tatar_not_confused_with_bashkort(self):
        # The whole difficulty: Tatar shares most of the Cyrillic inventory.
        self.assertEqual(detect(TATAR).lang, "tatar")

    def test_russian(self):
        self.assertEqual(detect(RUSSIAN).lang, "russian")

    def test_latin_script_bashkort(self):
        self.assertEqual(detect(LATIN_BASHKORT).lang, "bashkort")

    def test_confidence_is_meaningful(self):
        for text in (BASHKORT, TATAR, RUSSIAN):
            with self.subTest(text[:20]):
                self.assertGreater(detect(text).confidence, 0.5)

    def test_is_bashkort_helper(self):
        self.assertTrue(detect(BASHKORT).is_bashkort)
        self.assertFalse(detect(TATAR).is_bashkort)
        self.assertFalse(detect(RUSSIAN).is_bashkort)


class TestAbstention(unittest.TestCase):
    """The detector must decline rather than guess."""

    def test_empty_and_tiny_input(self):
        for text in ("", "   ", "Ике һүҙ"):
            with self.subTest(repr(text)):
                self.assertEqual(detect(text).lang, "unknown")

    def test_broken_text_layer_forces_uncertain(self):
        # A layer flagged as corrupt must not yield a confident verdict, no
        # matter how clean the surviving words look.
        v = detect(RUSSIAN, source="text?")
        self.assertEqual(v.lang, "uncertain")
        self.assertEqual(v.evidence.get("leaning"), "russian")

    def test_ocr_confidence_is_discounted(self):
        self.assertLess(detect(BASHKORT, "ocr").confidence,
                        detect(BASHKORT, "text").confidence)


class TestOcrSafety(unittest.TestCase):
    """Tesseract ships no Bashkort model, so scans are read with `tat`.

    That model cannot emit ҙ ҫ ҡ ғ and rewrites them to Tatar shapes. The
    detector must therefore not treat their absence as evidence of Tatar.
    """

    def test_bashkort_survives_loss_of_its_own_letters(self):
        damaged = (BASHKORT
                   .replace("ҙ", "з").replace("ҫ", "с")
                   .replace("ҡ", "к").replace("ғ", "г"))
        self.assertEqual(detect(damaged, source="ocr").lang, "bashkort")

    def test_same_damage_under_text_source_would_mislead(self):
        # Documents why the OCR path exists at all: with the character stream
        # trusted, the same damaged text is no longer safely Bashkort.
        damaged = (BASHKORT
                   .replace("ҙ", "з").replace("ҫ", "с")
                   .replace("ҡ", "к").replace("ғ", "г"))
        self.assertNotEqual(detect(damaged, source="ocr").lang,
                            "tatar")


class TestSuspectTextLayer(unittest.TestCase):
    def test_clean_cyrillic_is_not_suspect(self):
        self.assertFalse(suspect_text_layer(RUSSIAN))
        self.assertFalse(suspect_text_layer(BASHKORT))

    def test_cyrillic_with_heavy_latin_and_no_turkic_is_suspect(self):
        broken = ("Эта книга связана с историей aBcDeFgH IjKlMnOp "
                  "QrStUvWx YzAbCdEf для неё мы собрали много ") * 12
        self.assertTrue(suspect_text_layer(broken))

    def test_short_input_is_not_judged(self):
        self.assertFalse(suspect_text_layer("Привет abc"))


class TestMixedDocuments(unittest.TestCase):
    def test_bashkort_book_with_russian_front_matter(self):
        # A Bashkort book with a Russian preface is a Bashkort book.
        v = detect(RUSSIAN + BASHKORT * 4)
        self.assertEqual(v.lang, "bashkort")

    def test_distribution_is_reported(self):
        v = detect(RUSSIAN + BASHKORT * 4)
        self.assertIn("bashkort", v.distribution)
        self.assertGreater(v.distribution["bashkort"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
