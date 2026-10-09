import os
from utils import logger, GEODATA_HEADER
import argparse
import shutil

parser = argparse.ArgumentParser()

parser.add_argument("--full", action="store_true", help="Режим расширенных данных")
parser.add_argument(
    "--output",
    type=str,
    default="./geoname_data/cities500.txt.tmp",
    help="Выходной файл cities500",
)

# Разбор аргументов
args = parser.parse_args()

MIN_POPULATION = 100

# Пути к файлам
data_base_dir = "./geoname_data"
cities_file = os.path.join(data_base_dir, "cities500.txt")
extra_data_folder = os.path.join(data_base_dir, "extra_data/")
output_file = args.output


def need_finer_data(data):
    if args.full:
        return True
    return False


# Читаем все id из cities500.txt
with open(cities_file, "r") as f:
    existing_ids = set()
    existing_loc = set()
    for line in f:
        d = line.split("\t")
        existing_ids.add(d[0])
        existing_loc.add((d[4], d[5]))

shutil.copyfile(cities_file, output_file)

with open(output_file, "a") as append_f:
    # Перебираем все txt-файлы в папке extra_data
    for file_name in os.listdir(extra_data_folder):
        if file_name.endswith(".txt"):
            logger.info(f"Начата обработка {file_name}")
            file_path = os.path.join(extra_data_folder, file_name)

            with open(file_path, "r") as f:
                c = 0
                for line in f:
                    columns = line.split("\t")

                    # Первый id
                    id_value = columns[0]
                    loc = (columns[4], columns[5])

                    try:
                        num_value = float(columns[14])
                    except ValueError:
                        continue  # если не удаётся преобразовать в число, пропускаем строку

                    # Определяем, нужно ли добавлять строку
                    if (
                        id_value not in existing_ids
                        and (num_value >= MIN_POPULATION or need_finer_data(columns))
                        and loc not in existing_loc
                    ):
                        c += 1
                        append_f.write(line)
                        existing_ids.add(id_value)  # добавляем в множество существующих id
                        existing_loc.add(loc)

                logger.info(f"Всего добавлено {c} записей")
