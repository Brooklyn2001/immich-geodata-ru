#!/bin/bash

set -e

# Устанавливаем формат времени и имена файлов
CURRENT_DATE=${CURRENT_DATE:-$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")}
TODAY_DATE=${TODAY_DATE:-$(date -u +"%Y-%m-%d")}

RU_PATTERN="{admin_2}"
FULL=false
OUTPUT_FOLDER="./output_tmp"
OUTPUT_FILE="./output/geodata.zip"

# Разбор аргументов командной строки
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ru-pattern)
      RU_PATTERN="$2"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --full)
      FULL=true
      shift
      ;;
    *)
      echo "Неизвестный параметр: $1"
      exit 1
      ;;
  esac
done

rm -rf $OUTPUT_FOLDER

FULL_ARGS=""
if [ "$FULL" = true ]; then
  FULL_ARGS=" --full"
fi

# Запуск python enhance_data.py
echo "Запуск python enhance_data.py..."
python enhance_data.py $FULL_ARGS --output ./geoname_data/cities500.txt.tmp

# Геокодирование через Nominatim по усиленному cities500.txt.tmp
# (первый проход — по данным базового cities500, чтобы не гнать полный дамп страны)
LIST=("RU" "BY" "UA" "KZ" "UZ" "AM" "AZ" "GE" "KG" "TJ" "TM" "MD" "LT" "LV" "EE")
for item in "${LIST[@]}"; do
    echo "Запуск python generate_geodata_nominatim.py $item (по cities500)..."
    python generate_geodata_nominatim.py --country-code "$item" --data-file ./geoname_data/cities500.txt.tmp
    if [[ $? -ne 0 ]]; then
        echo "Ошибка python generate_geodata_nominatim.py $item! Выход."
        exit 1
    fi
done

rm -rf "$OUTPUT_FOLDER"
mkdir -p "$OUTPUT_FOLDER"

echo "Запуск python translate.py..."
python translate.py --ru-pattern "$RU_PATTERN" --output "$OUTPUT_FOLDER" --input-cities500 ./geoname_data/cities500.txt.tmp
if [[ $? -ne 0 ]]; then
    echo "Ошибка python translate.py! Выход."
    exit 1
fi

echo "Перевод названий стран в geoname_data/countryInfo.txt..."
python translate_country_info.py --input ./geoname_data/countryInfo.txt --output "$OUTPUT_FOLDER/countryInfo.txt"
if [[ $? -ne 0 ]]; then
    echo "Ошибка перевода countryInfo.txt! Выход."
    exit 1
fi


# Копируем geojson-файл в выходную папку
echo "Копирование geoname_data/ne_10m_admin_0_countries.geojson в выходную папку..."
mkdir -p output
cp geoname_data/ne_10m_admin_0_countries.geojson $OUTPUT_FOLDER
if [[ $? -ne 0 ]]; then
    echo "Ошибка копирования geojson-файла! Выход."
    exit 1
fi

# Создаём файл geodata-date.txt
echo "Создание файла geodata-date.txt..."
echo "$CURRENT_DATE" > "$OUTPUT_FOLDER/geodata-date.txt"

# Упаковываем выходную папку
ZIP_FILE="$OUTPUT_FILE"
echo "Упаковка выходной папки в $ZIP_FILE..."
rm -rf geodata
mv "$OUTPUT_FOLDER" geodata
zip -r "$ZIP_FILE" geodata/
if [[ $? -ne 0 ]]; then
    echo "Ошибка упаковки файла! Выход."
    exit 1
fi

echo "Скрипт выполнен! Упакованный файл: $ZIP_FILE"
