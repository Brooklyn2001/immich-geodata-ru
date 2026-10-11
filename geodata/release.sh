#!/bin/bash

set -e

# Устанавливаем формат времени и имена файлов
CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
TODAY_DATE=$(date -u +"%Y-%m-%d")

export CURRENT_DATE=$CURRENT_DATE
export TODAY_DATE=$TODAY_DATE

# Запуск prepare_geoname_data.sh
# В режиме SKIP_GEOCODE (CI: geodata уже подготовлена отдельными job'ами)
# исходники не перекачиваем и геокодинг не выполняем — только собираем данные.
if [[ -z "$SKIP_GEOCODE" ]]; then
  echo "Запуск prepare_geoname_data.sh..."
  bash prepare_geoname_data.sh
  if [[ $? -ne 0 ]]; then
      echo "Ошибка prepare_geoname_data.sh! Выход."
      exit 1
  fi
fi

rm -rf output
rm -rf output_tmp
rm -rf geodata

GEOCODE_FLAG=""
if [[ -n "$SKIP_GEOCODE" ]]; then
  GEOCODE_FLAG=" --skip-geocode"
fi

LIST=("{admin_2}" "{admin_3}" "{admin_4}" "{admin_2} {admin_3}" "{admin_2} {admin_4}" "{admin_3} {admin_4}" "{admin_2} {admin_3} {admin_4}")
for item in "${LIST[@]}"; do
    striped_name="${item//\{/}"
    striped_name="${striped_name//\}/}"
    bash generate_data.sh --ru-pattern "$item" --output "output/geodata_${striped_name// /_}.zip"$GEOCODE_FLAG
    bash generate_data.sh --ru-pattern "$item" --output "output/geodata_${striped_name// /_}_full.zip" --full$GEOCODE_FLAG
done

cp output/geodata_admin_2.zip output/geodata.zip
cp output/geodata_admin_2_full.zip output/geodata_full.zip
