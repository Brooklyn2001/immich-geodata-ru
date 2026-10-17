import argparse
import csv
from utils import load_geo_data, ensure_folder_exists, logger, load_alternate_name
import os

parser = argparse.ArgumentParser(description="Разбор аргумента ru_pattern.")
parser.add_argument(
    "--ru-pattern",
    type=str,
    default="{admin_2}",
    help="Параметр шаблона, по умолчанию {admin_2}",
)
parser.add_argument("--output", type=str, default="output", help="Путь к выходной папке")
parser.add_argument(
    "--input-cities500",
    type=str,
    default="./geoname_data/cities500.txt",
    help="Путь к входному cities500.txt",
)
args = parser.parse_args()
ru_pattern = args.ru_pattern

alternate_name_folder = "./geoname_data"
alternate_name = load_alternate_name(
    os.path.join(alternate_name_folder, "alternateNamesV2.txt")
)

admin_1_set = set()
with open("./geoname_data/admin1CodesASCII.txt", "r", encoding="utf-8") as f:
    for line in f.readlines():
        parts = line.split("\t")
        admin_1_set.add(parts[0])


def _is_valid_geonameid(value):
    """Возвращает True, если value строго положительное целое (валидный geonameid).

    Immich делает id = Number.parseInt(lineSplit[0]); нечисловое первое поле
    даёт NaN в integer-колонке id и роняет импорт geodata. Поэтому отбрасываем
    всё, что не является целым числом.
    """
    if value is None:
        return False
    s = str(value).strip()
    return s.isdigit() and int(s) > 0


def _to_float(value):
    """Возвращает float(value) или None, если привести нельзя."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_geodata_list(folder_path):
    geo_dict = {}

    # Перебираем все файлы в папке
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".csv"):
            # Убираем расширение файла как ключ
            key = os.path.splitext(file_name)[0]
            file_path = os.path.join(folder_path, file_name)
            geo_dict[key] = load_geo_data(file_path)

    return geo_dict


def translate_cities500():
    geodata_folder = "./data"
    geodata = load_geodata_list(geodata_folder)

    input_file = args.input_cities500
    if not os.path.exists(input_file):
        logger.error(f"Входной файл {input_file} не существует")
        return

    output_file = os.path.join(args.output, "cities500.txt")
    ensure_folder_exists(output_file)

    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.reader(infile, delimiter="\t")
        # lineterminator="\n" + newline="" дают чистые \n (без \r\r\n на Windows).
        writer = csv.writer(outfile, delimiter="\t", lineterminator="\n")

        for row in reader:
            # Отбрасываем строки, которые сломали бы импорт geodata в Immich:
            # - geonameid (кол. 0) идёт в integer-колонку id — если он не число,
            #   Number.parseInt вернёт NaN и Postgres упадёт с
            #   'invalid input syntax for type integer: "NaN"'.
            # - lat/lon (кол. 4/5) идут в double — нечисловые дадут мусорные точки.
            # - строка короче 19 полей ломает modificationDate (row[18] = undefined).
            if len(row) < 19 or not _is_valid_geonameid(row[0]):
                logger.warning(
                    f"Строка {row[0]!r} с некорректным geonameid пропущена "
                    f"(привела бы к id: NaN у Immich)"
                )
                continue
            if _to_float(row[4]) is None or _to_float(row[5]) is None:
                logger.warning(
                    f"Строка geonameid={row[0]!r} с некорректными координатами "
                    f"({row[4]!r},{row[5]!r}) пропущена"
                )
                continue

            country_code = row[8]  # код страны
            latitude = str(row[4])  # широта
            longitude = str(row[5])  # долгота

            admin1_code = row[10]
            if not admin1_code or f"{country_code}.{admin1_code}" not in admin_1_set:
                continue

            translated_name = None

            # Ветка 1: русское имя из geodata (уже геокодировано через Nominatim).
            # Инвариант целостности: если точка есть в geodata, но у неё нет
            # admin_2 (обязательный уровень паттерна) — НЕ пишем частичный результат
            # и пропускаем строку, иначе Immich «запомнит» неполное название.
            if (
                country_code in geodata
                and (longitude, latitude) in geodata[country_code]
            ):
                location = geodata[country_code][(longitude, latitude)]
                if not location["admin_2"]:
                    logger.debug(
                        f"{row[1]} ({country_code}): в geodata нет admin_2 — "
                        f"частичный результат не пишем, строка пропущена"
                    )
                    continue
                res = ru_pattern.format(**location)
                if res:
                    translated_name = res
                    logger.debug(
                        f"{row[1]} ({country_code}): имя из geodata "
                        f"(паттерн {ru_pattern!r}) → {res}"
                    )

            if translated_name is None and row[0] in alternate_name:
                name = alternate_name[row[0]]
                translated_name = name
                logger.debug(
                    f"{row[1]} ({country_code}): фолбэк — русское имя "
                    f"из alternate_name (geonameid {row[0]}) → {name}"
                )

            if translated_name is None:
                candidates = row[3].split(",")
                russian_word = next(
                    (word for word in candidates if is_russian(word)), None
                )
                if russian_word:
                    translated_name = russian_word
                    logger.debug(
                        f"{row[1]} ({country_code}): фолбэк — русское слово из "
                        f"кандидатов {candidates!r} → {russian_word}"
                    )

            if translated_name is not None:
                row[1] = translated_name
                row[2] = translated_name
            else:
                # Ветка «оригинал»: русского имени нигде нет — оставляем локальное
                # (национальное) название без замены.
                logger.debug(
                    f"{row[1]} ({country_code}): русского имени нет, "
                    f"оставлен оригинал {row[1]!r}"
                )

            # Записываем обработанную строку в выходной файл
            writer.writerow(row)


def is_russian(text):
    if not text:
        return False
    for char in text:
        lowercase = char.lower()
        if not ("\u0430" <= lowercase <= "\u044f" or lowercase == "\u0451"):
            return False
    return True


def translate_admin1():
    def process(input_file):
        if not os.path.exists(input_file):
            logger.error(f"Входной файл {input_file} не существует")
            return

        output_file = os.path.join(args.output, os.path.basename(input_file))
        ensure_folder_exists(output_file)

        with open(input_file, "r", encoding="utf-8") as infile, open(
            output_file, "w", encoding="utf-8", newline=""
        ) as outfile:
            reader = csv.reader(infile, delimiter="\t")
            writer = csv.writer(outfile, delimiter="\t", lineterminator="\n")

            for row in reader:
                res = None
                code = row[3]

                if code in alternate_name:
                    res = alternate_name[code]

                if res:
                    row[1] = res
                    row[2] = res

                # Записываем обработанную строку в выходной файл
                writer.writerow(row)

    process("./geoname_data/admin1CodesASCII.txt")
    logger.info("admin1CodesASCII.txt обработан")

    process("./geoname_data/admin2Codes.txt")
    logger.info("admin2Codes.txt обработан")


if __name__ == "__main__":
    translate_cities500()
    translate_admin1()
