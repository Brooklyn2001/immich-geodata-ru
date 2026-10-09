#!/bin/bash

set -e

# Устанавливаем формат времени и имена файлов
CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
TODAY_DATE=$(date -u +"%Y-%m-%d")

export CURRENT_DATE=$CURRENT_DATE
export TODAY_DATE=$TODAY_DATE

# Запуск prepare_geoname_data.sh
echo "Запуск prepare_geoname_data.sh..."
bash prepare_geoname_data.sh
if [[ $? -ne 0 ]]; then
    echo "Ошибка prepare_geoname_data.sh! Выход."
    exit 1
fi

rm -rf output
rm -rf output_tmp
rm -rf geodata

LIST=("{admin_2}" "{admin_3}" "{admin_4}" "{admin_2} {admin_3}" "{admin_2} {admin_4}" "{admin_3} {admin_4}" "{admin_2} {admin_3} {admin_4}")
for item in "${LIST[@]}"; do
    striped_name="${item//\{/}"
    striped_name="${striped_name//\}/}"
    bash generate_data.sh --ru-pattern "$item" --output "output/geodata_${striped_name// /_}.zip"
    bash generate_data.sh --ru-pattern "$item" --output "output/geodata_${striped_name// /_}_full.zip" --full
done

cp output/geodata_admin_2.zip output/geodata.zip
cp output/geodata_admin_2_full.zip output/geodata_full.zip
