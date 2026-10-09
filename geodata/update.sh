#!/bin/bash

# Включаем режим отладки
set -e

cd "$(dirname "$0")"

# Получаем имя текущего скрипта
script_name=$(basename "$0")
geodata_name=${1:-geodata}

echo "Получаю последний $geodata_name.zip из репозитория Brooklyn2001/immich-geodata-ru..."

# URL API последнего release
LATEST_RELEASE_API="https://api.github.com/repos/Brooklyn2001/immich-geodata-ru/releases/latest"

echo "Запрашиваю информацию о последнем release через GitHub API..."
response=$(curl -s $LATEST_RELEASE_API)
if [[ $? -ne 0 ]]; then
  echo "Ошибка: не удалось получить информацию о последнем release, проверьте сеть."
  exit 1
fi

# Извлекаем URL загрузки geodata.zip из JSON
zip_url=$(echo "$response" | grep -oP '"browser_download_url":\s*"\K(.*'"$geodata_name"'\.zip)(?=")')
if [[ -z $zip_url ]]; then
  echo "Ошибка: ссылка на $geodata_name.zip не найдена, проверьте последний release репозитория."
  exit 1
fi

echo "Адрес загрузки последнего $geodata_name.zip: $zip_url"

# Скачиваем geodata.zip
echo "Начинаю загрузку $geodata_name.zip..."
curl -L -o geodata.zip "$zip_url"
if [[ $? -ne 0 ]]; then
  echo "Ошибка: не удалось скачать geodata.zip, проверьте сеть."
  exit 1
fi

echo "$geodata_name.zip загружен успешно!"

# Распаковываем geodata.zip
echo "Начинаю распаковку geodata.zip..."
unzip geodata.zip -d temp_geodata
if [[ $? -ne 0 ]]; then
  echo "Ошибка: распаковка geodata.zip не удалась, проверьте целостность файла."
  exit 1
fi

echo "Распаковка успешна, файлы размещены во временной папке temp_geodata/."

# Переносим содержимое в текущую папку, исключая сам скрипт
echo "Переношу содержимое в текущую папку, исключая скрипт ($script_name)..."
for file in temp_geodata/geodata/*; do
  if [[ $(basename "$file") == "$script_name" ]]; then
    echo "Пропускаю файл скрипта: $file"
    continue
  fi
  mv "$file" ./
done

# Удаляем временные файлы и папки
echo "Очистка промежуточных файлов..."
rm -rf geodata.zip temp_geodata
if [[ $? -ne 0 ]]; then
  echo "Внимание: не удалось удалить промежуточные файлы, удалите их вручную."
else
  echo "Промежуточные файлы успешно удалены."
fi

echo "Готово, все geodata-файлы размещены в текущей папке! Перезапустите Immich!"

# Замените на вашу команду перезапуска Immich для автоматического перезапуска после обновления данных
# docker restart immich_server
