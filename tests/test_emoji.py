import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import emoji


def load_standard_emoji_surfaces():
    surfaces = set()
    emoji_test = REPOSITORY_ROOT / "data" / "emoji-test.txt"
    for line in emoji_test.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        codepoints_field, status_field = line.split(";", maxsplit=1)
        status = status_field.strip().split()[0]
        if status not in {"fully-qualified", "component"}:
            continue
        surfaces.add(
            "".join(chr(int(codepoint, 16)) for codepoint in codepoints_field.split())
        )
    return surfaces


class EmojiTestDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard_surfaces = load_standard_emoji_surfaces()
        cls.emojis = []
        emoji.load_emoji_data(cls.emojis)
        emoji.apply_emoji_zwj_sequences(cls.emojis)
        emoji.apply_emoji_test_data(cls.emojis)

    def test_heart_on_fire_uses_fully_qualified_sequence(self):
        expected = "\u2764\uFE0F\u200D\U0001F525"
        matches = [
            item
            for item in self.emojis
            if item.codepoints.replace("\uFE0F", "")
            == expected.replace("\uFE0F", "")
        ]

        self.assertTrue(matches)
        self.assertTrue(all(item.codepoints == expected for item in matches))

    def test_all_surfaces_are_standard_qualified_sequences(self):
        nonstandard = [
            item.codepoints
            for item in self.emojis
            if item.codepoints not in self.standard_surfaces
        ]

        self.assertEqual(nonstandard, [])

    def test_all_surfaces_receive_genre_and_order(self):
        missing_metadata = [
            item.codepoints
            for item in self.emojis
            if item.genre is None or item.order is None
        ]

        self.assertEqual(missing_metadata, [])


class GeneratedDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard_surfaces = load_standard_emoji_surfaces()

    def test_generated_surfaces_are_standard_qualified_sequences(self):
        for dictionary_path in sorted(
            (REPOSITORY_ROOT / "EmojiDictionary").glob("emoji_all_E*.txt")
        ):
            with self.subTest(dictionary=dictionary_path.name):
                nonstandard = []
                for line in dictionary_path.read_text().splitlines():
                    surface = line.split("\t", maxsplit=1)[0]
                    if surface not in self.standard_surfaces:
                        nonstandard.append(surface)

                self.assertEqual(nonstandard, [])


if __name__ == "__main__":
    unittest.main()
