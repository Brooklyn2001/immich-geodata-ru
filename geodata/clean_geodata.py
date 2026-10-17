#!/usr/bin/env python3
"""Чистильщик уже скачанного geodata (zip или распакованной папки).

Убирает строки, из-за которых Immich падает при инициализации обратного
геокодирования с ошибкой:

    Unable to initialize reverse geocoding:
    PostgresError: invalid input syntax for type integer: "NaN"

Причина: в geodata встречаются битые строки, у которых geonameid (первое
поле cities500.txt) не является числом. Immich делает
`id = Number.parseInt(lineSplit[0])`, получает `NaN` и не может вставить его
в integer-колонку `id` таблицы `geodata_places` — весь импорт geodata падает.

ВАЖНО: начиная с исправления в translate.py свежие сборки сразу пишут файлы с
корректными переводами строк (\\n), и этот скрипт им НЕ нужен. Он предназначен
только для УЖЕ скачанных/собранных архивов, которые могли быть сделаны до
фикса: в них переводы строк были нестандартными (\\r\\r\\n), из-за чего Immich
(Node readline) видел вдвое больше строк, половина пустых, и давал id: NaN.
Скрипт нормализует переводы строк в \\n и отбрасывает действительно битые
строки.

Использование:
    python clean_geodata.py --dir  ./geodata        # чистить распакованную папку
    python clean_geodata.py --archive ./geodata.zip # распаковать, почистить, упаковать обратно
    python clean_geodata.py --archive ./geodata.zip --keep-dir   # не удалять распакованную папку

Дополнительно скрипт обновляет geodata-date.txt на текущую дату (можно
отключить флагом --no-update-date). Это нужно, чтобы Immich ТОЧНО
пере-импортировал данные: он пропускает импорт, если дата в этом файле не
новее даты последнего импорта (хранится в system-metadata).
"""

import argparse
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone

# Колонки cities500.txt (геонимы, через табуляцию):
#   0 geonameid | 1 name | 2 asciiname | 3 alternatenames | 4 latitude
#   5 longitude | 6 feat_class | 7 feat_code | 8 country_code | 9 cc2
#   10 admin1 | 11 admin2 | 12 admin3 | 13 admin4 | 14 population
#   15 elevation | 16 dem | 17 timezone | 18 modification_date
# Immich (map.repository.ts) использует:
#   id = parseInt(0), lat = Number(4), lon = Number(5), стране Code = 8,
#   admin1 = 10, admin2 = 11, modificationDate = 18

CITIES500_EXPECTED_FIELDS = 19


def is_valid_geonameid(value):
    return value is not None and str(value).strip().isdigit() and int(str(value).strip()) > 0


def to_float(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def clean_cities500(fields):
    """Возвращает True, если строку (уже split по '\\t') нужно сохранить."""
    if len(fields) < CITIES500_EXPECTED_FIELDS:
        return False
    if not is_valid_geonameid(fields[0]):
        return False
    if to_float(fields[4]) is None or to_float(fields[5]) is None:
        return False
    return True


def clean_admin_codes(fields):
    """admin1CodesASCII.txt / admin2Codes.txt: id | name | ascii | geonameid.

    Immich читает их в Map<id, name>, поэтому integer-ошибок не дают, но
    пустые/битые строки чистим заодно.
    """
    if len(fields) < 4:
        return False
    if not fields[0].strip():
        return False
    return True


def clean_text_file(path, validator, field_sep="\t"):
    """Переписывает файл, оставляя только строки, принятые validator.

    Возвращает (исходное_число_строк, оставлено_строк).
    """
    total = 0
    kept = 0
    tmp_path = path + ".clean_tmp"
    # Читаем в бинарном режиме и разбиваем по физическим строкам ('\n'), чтобы
    # корректно обрабатывать любые завершения строк (включая нестандартное
    # '\r\r\n', которым пишет translate.py). В текстовом режиме с newline=""
    # Python разбивает и по одиночному '\r', что дробит каждую запись пополам.
    with open(path, "rb") as fin, open(
        tmp_path, "w", encoding="utf-8", newline=""
    ) as fout:
        for raw in fin:
            total += 1
            line = raw.decode("utf-8", errors="replace")
            # Снимаем перевод строки целиком (все хвостовые \r и \n).
            stripped = line.rstrip("\r\n")
            # Пропускаем пустые строки и комментарии.
            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue
            fields = stripped.split(field_sep)
            if validator(fields):
                fout.write(stripped + "\n")
                kept += 1
    os.replace(tmp_path, path)
    return total, kept


def stamp_geodata_date(geodata_dir):
    """Обновляет geodata-date.txt на текущее время (UTC, ISO с зоной).

    Имя файла может быть geodata-date.txt или geodata_date.txt — ищем оба.
    """
    names = ["geodata-date.txt", "geodata_date.txt"]
    existing = next((n for n in names if os.path.exists(os.path.join(geodata_dir, n))), None)
    path = os.path.join(geodata_dir, existing if existing else names[0])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(now + "\n")
    return path


def clean_dir(geodata_dir, update_date):
    """Чистит файлы прямо в папке geodata_dir."""
    if not os.path.isdir(geodata_dir):
        raise SystemExit(f"Папка не найдена: {geodata_dir}")

    cities = os.path.join(geodata_dir, "cities500.txt")
    admin1 = os.path.join(geodata_dir, "admin1CodesASCII.txt")
    admin2 = os.path.join(geodata_dir, "admin2Codes.txt")

    files = []
    if os.path.exists(cities):
        t, k = clean_text_file(cities, clean_cities500)
        files.append((os.path.basename(cities), t, k))
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: не найден {os.path.basename(cities)}")

    for p in (admin1, admin2):
        if os.path.exists(p):
            t, k = clean_text_file(p, clean_admin_codes)
            files.append((os.path.basename(p), t, k))

    print(f"\nОбработано: {geodata_dir}")
    for name, total, kept in files:
        removed = total - kept
        print(f"  {name:24} строк всего: {total:8}  оставлено: {kept:8}  удалено: {removed}")

    if update_date:
        stamped = stamp_geodata_date(geodata_dir)
        print(f"  обновлена дата импорта: {os.path.basename(stamped)}")
    else:
        print("  (дата импорта НЕ обновлена: используйте флаг --no-update-date осознанно)")


def main():
    parser = argparse.ArgumentParser(description="Чистит geodata Immich от битых строк")
    parser.add_argument("--dir", help="распакованная папка geodata (например ./geodata)")
    parser.add_argument("--archive", help="путь к geodata.zip")
    parser.add_argument("--keep-dir", action="store_true", help="не удалять распакованную папку после --archive")
    parser.add_argument("--no-update-date", action="store_true", help="не обновлять geodata-date.txt")
    args = parser.parse_args()

    if not args.dir and not args.archive:
        raise SystemExit("Укажите --dir или --archive, например:\n"
                         "  python clean_geodata.py --dir ./geodata\n"
                         "  python clean_geodata.py --archive ./geodata.zip")

    update_date = not args.no_update_date

    if args.dir:
        clean_dir(args.dir, update_date)
        print("\nГотово. Перезапустите Immich, чтобы он пере-импортировал данные.")
        return

    archive = args.archive
    if not os.path.exists(archive):
        raise SystemExit(f"Архив не найден: {archive}")

    tmpdir = tempfile.mkdtemp(prefix="geodata_clean_")
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(tmpdir)
        # Внутри архива может быть вложенная папка geodata/ (release.sh кладёт
        # файлы в geodata/ внутри zip). Ищем каталог, где лежит cities500.txt.
        geodata_dir = None
        for root, _dirs, files in os.walk(tmpdir):
            if "cities500.txt" in files:
                geodata_dir = root
                break
        if geodata_dir is None:
            raise SystemExit("В архиве не найден cities500.txt")

        clean_dir(geodata_dir, update_date)

        # Переупаковываем с тем же относительным путём, что был внутри архива.
        out_archive = archive
        rel = os.path.relpath(geodata_dir, tmpdir)
        with zipfile.ZipFile(out_archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(geodata_dir):
                for name in files:
                    full = os.path.join(root, name)
                    arcname = os.path.join(rel, os.path.relpath(full, geodata_dir))
                    zf.write(full, arcname)
        print(f"\nАрхив переупакован: {out_archive}")
    finally:
        if not args.keep_dir:
            shutil.rmtree(tmpdir, ignore_errors=True)

    print("Готово. Распакуйте новый архив и примонтируйте/перезапустите Immich.")


if __name__ == "__main__":
    main()
