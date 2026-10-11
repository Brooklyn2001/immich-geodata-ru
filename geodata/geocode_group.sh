#!/bin/bash
# Геокодирование группы стран через Nominatim. Вызывается по одной группе на job
# в CI (см. .github/workflows/release.yaml), чтобы каждая job укладывалась в
# 6-часовой лимит GitHub Actions. Аргументы — коды стран, например:
#   bash geocode_group.sh RU BY UA KZ UZ
# Результат пишется в data/<CODE>.csv (аккумулятор: resume пропускает уже
# обработанные координаты, поэтому base+full проходы дополняют набор).

set -e

if [ $# -eq 0 ]; then
    echo "Ошибка: укажите хотя бы один код страны."
    exit 1
fi

# Переходим в каталог geodata, чтобы относительные пути (geoname_data/, data/)
# указывали на правильные папки.
cd "$(dirname "$0")"

# Первый проход — базовый cities500 (население >= 100 из extra_data).
echo "== Группа: $* (base) =="
python enhance_data.py --output ./geoname_data/cities500.txt.tmp
for item in "$@"; do
    echo "Геокодирование $item (base)..."
    python generate_geodata_nominatim.py --country-code "$item" --data-file ./geoname_data/cities500.txt.tmp
done

# Второй проход — расширенный cities500 (все точки из extra_data).
echo "== Группа: $* (full) =="
python enhance_data.py --full --output ./geoname_data/cities500.txt.tmp
for item in "$@"; do
    echo "Геокодирование $item (full)..."
    python generate_geodata_nominatim.py --country-code "$item" --data-file ./geoname_data/cities500.txt.tmp
done

echo "Геокодирование группы завершено: $*"
