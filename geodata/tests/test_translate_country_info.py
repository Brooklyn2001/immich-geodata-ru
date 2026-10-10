import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translate_country_info import translate_country_info  # noqa: E402


class TranslateCountryInfoTest(unittest.TestCase):
    def test_translates_country_column_and_preserves_other_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.txt"
            output_path = temp_path / "output.txt"
            translations_path = temp_path / "ru.json"

            input_path.write_bytes(
                b"#ISO\tISO3\tISO-Numeric\tfips\tCountry\r\n"
                b"RU\tRUS\t643\tRS\tRussia\tMoscow\r\n"
                b"AN\tANT\t530\tNT\tNetherlands Antilles\tWillemstad\r\n"
            )
            translations_path.write_text(
                json.dumps({"countries": {"RU": "\u0420\u043e\u0441\u0441\u0438\u044f"}}),
                encoding="utf-8",
            )

            translated_count = translate_country_info(
                input_path, output_path, translations_path
            )

            self.assertEqual(translated_count, 1)
            self.assertEqual(
                output_path.read_bytes(),
                b"#ISO\tISO3\tISO-Numeric\tfips\tCountry\r\n"
                b"RU\tRUS\t643\tRS\t\xd0\xa0\xd0\xbe\xd1\x81\xd1\x81\xd0\xb8\xd1\x8f\tMoscow\r\n"
                b"AN\tANT\t530\tNT\tNetherlands Antilles\tWillemstad\r\n",
            )

    def test_list_value_takes_first_variant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.txt"
            output_path = temp_path / "output.txt"
            translations_path = temp_path / "ru.json"

            input_path.write_text("RU\tRUS\t643\tRS\tRussia\tMoscow\n", encoding="utf-8")
            translations_path.write_text(
                json.dumps(
                    {"countries": {"RU": ["\u0420\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u0430\u044f \u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u044f", "\u0420\u043e\u0441\u0441\u0438\u044f"]}}
                ),
                encoding="utf-8",
            )

            translated_count = translate_country_info(
                input_path, output_path, translations_path
            )

            self.assertEqual(translated_count, 1)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "RU\tRUS\t643\tRS\t\u0420\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u0430\u044f \u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u044f\tMoscow\n",
            )


if __name__ == "__main__":
    unittest.main()
