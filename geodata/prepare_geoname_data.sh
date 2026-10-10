#!/bin/bash

set -e

# 定义目标文件夹和URL
TARGET_DIR="geoname_data"
ZIP_FILE="$TARGET_DIR/cities500.zip"
TXT_FILE="$TARGET_DIR/cities500.txt"
ADMIN1_FILE="$TARGET_DIR/admin1CodesASCII.txt"
ADMIN2_FILE="$TARGET_DIR/admin2Codes.txt"
COUNTRY_INFO_FILE="$TARGET_DIR/countryInfo.txt"
GEOJESON_FILE="$TARGET_DIR/ne_10m_admin_0_countries.geojson"
EXTRA_DATA_DIR="$TARGET_DIR/extra_data"
DOWNLOAD_URL="https://download.geonames.org/export/dump/cities500.zip"
# Список стран бывшего СССР, для которых нужны расширенные (полные) данные
LIST=("RU" "BY" "UA" "KZ" "UZ" "AM" "AZ" "GE" "KG" "TJ" "TM" "MD" "LT" "LV" "EE")

if [[ "$1" == "--update" ]]; then
    if [[ -d "$TARGET_DIR" ]]; then
        echo "Обнаружен параметр --update, удаление папки $TARGET_DIR ..."
        rm -rf "$TARGET_DIR"
        echo "Папка $TARGET_DIR удалена."
    else
        echo "Папки $TARGET_DIR не существует, удалять нечего."
    fi
    exit 0
fi

# Создаём целевую папку
mkdir -p "$TARGET_DIR"

# Скачиваем файл
echo "Загрузка $DOWNLOAD_URL в $ZIP_FILE..."
curl -o "$ZIP_FILE" "$DOWNLOAD_URL"

# Проверяем успешность загрузки
if [[ $? -ne 0 ]]; then
  echo "Ошибка загрузки: проверьте сеть или правильность URL."
  exit 1
fi

mkdir -p "$EXTRA_DATA_DIR"

for item in "${LIST[@]}"; do
    echo "Скачивание расширенных данных $item..."
    curl -o "$EXTRA_DATA_DIR/$item.zip" "https://download.geonames.org/export/dump/$item.zip"
    if [[ $? -ne 0 ]]; then
        echo "Ошибка загрузки $item.zip! Выход."
        exit 1
    fi
    unzip -o "$EXTRA_DATA_DIR/$item.zip" -d "$EXTRA_DATA_DIR"

    # Проверяем распакованный файл
    if [[ -f "$EXTRA_DATA_DIR/$item.txt" ]]; then
      echo "Распаковка $item.zip успешна"
    else
      echo "Файл $item.txt не найден, проверьте результат распаковки."
      exit 1
    fi

    # Удаляем промежуточные файлы
    rm -f "$EXTRA_DATA_DIR/$item.zip"
done

rm -f "$EXTRA_DATA_DIR/readme.txt"

echo "Загрузка $ADMIN1_FILE..."
curl -o "$ADMIN1_FILE" "https://download.geonames.org/export/dump/admin1CodesASCII.txt"

# Проверяем успешность загрузки
if [[ $? -ne 0 ]]; then
  echo "Ошибка загрузки: проверьте сеть или правильность URL."
  exit 1
fi

# Скачиваем файл
echo "Загрузка $ADMIN2_FILE..."
curl -o "$ADMIN2_FILE" "https://download.geonames.org/export/dump/admin2Codes.txt"

# Проверяем успешность загрузки
if [[ $? -ne 0 ]]; then
  echo "Ошибка загрузки: проверьте сеть или правильность URL."
  exit 1
fi

# Скачиваем файл информации о странах
echo "Загрузка $COUNTRY_INFO_FILE..."
curl -fL -o "$COUNTRY_INFO_FILE" "https://download.geonames.org/export/dump/countryInfo.txt"

# Проверяем успешность загрузки
if [[ $? -ne 0 ]]; then
  echo "Ошибка загрузки: проверьте сеть или правильность URL."
  exit 1
fi

# Скачиваем файл
echo "Загрузка $GEOJESON_FILE..."
curl -o "$GEOJESON_FILE" "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson"

# Проверяем успешность загрузки
if [[ $? -ne 0 ]]; then
  echo "Ошибка загрузки: проверьте сеть или правильность URL."
  exit 1
fi

echo "Загрузка успешна, распаковка..."

# Распаковываем файл в целевую папку
unzip -o "$ZIP_FILE" -d "$TARGET_DIR"

# Проверяем распакованный файл
if [[ -f "$TARGET_DIR/cities500.txt" ]]; then
  echo "Распаковка успешна, cities500.txt перемещён в целевую папку."
else
  echo "Файл cities500.txt не найден, проверьте результат распаковки."
  exit 1
fi

# Удаляем промежуточные файлы
echo "Очистка промежуточных файлов..."
rm -f "$ZIP_FILE"

echo "Готово! cities500.txt размещён в каталоге $TARGET_DIR."



# Задаём имя zip-файла и целевого txt-файла
ZIP_FILE="$TARGET_DIR/alternateNamesV2.zip"
TXT_FILE="$TARGET_DIR/alternateNamesV2.txt"
DOWNLOAD_URL="https://download.geonames.org/export/dump/alternateNamesV2.zip" # замените на актуальную ссылку

# Проверяем, существует ли целевой txt-файл
if [[ -f "$TXT_FILE" ]]; then
    echo "Целевой файл $TXT_FILE уже существует, скачивание не требуется."
    exit 0
fi

# Если zip-файл существует, распаковываем напрямую
if [[ -f "$ZIP_FILE" ]]; then
    echo "$ZIP_FILE уже существует"
else
    # Скачиваем zip-файл
    echo "Загрузка $ZIP_FILE ..."
    curl -o "$ZIP_FILE" "$DOWNLOAD_URL"
    if [[ $? -ne 0 ]]; then
        echo "Ошибка загрузки, выход."
        exit 1
    fi
fi

# Распаковываем zip-файл
echo "Распаковка $ZIP_FILE ..."
unzip -o "$ZIP_FILE" -d "$TARGET_DIR"
if [[ $? -eq 0 ]]; then
    echo "Распаковка завершена, удаление $ZIP_FILE ..."
    #rm -f "$ZIP_FILE"
else
    echo "Ошибка распаковки."
    exit 1
fi
