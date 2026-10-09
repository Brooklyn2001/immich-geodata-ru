import logging
import os
import csv
import pickle

logger = logging.getLogger("logger")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))  # минимальный уровень логирования

console_handler = logging.StreamHandler()

# 设置日志格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# 添加处理器到 logger
logger.addHandler(console_handler)

GEODATA_HEADER = [
    "longitude",
    "latitude",
    "country",
    "admin_1",
    "admin_2",
    "admin_3",
    "admin_4",
]


def load_geo_data(file_path):
    result = {}
    if os.path.exists(file_path):
        # 读取 CSV 文件
        with open(file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # 遍历每行数据
            for row in reader:
                # 获取 (lon, lat) 作为键
                key = (str(row["longitude"]), str(row["latitude"]))

                # 将其他字段作为值存入字典
                value = {
                    "country": row["country"],
                    "admin_1": row["admin_1"],
                    "admin_2": row["admin_2"],
                    "admin_3": row["admin_3"],
                    "admin_4": row["admin_4"],
                }

                result[key] = value

    return result


def ensure_folder_exists(file_path):
    folder = os.path.dirname(file_path)
    if folder:
        os.makedirs(folder, exist_ok=True)


def load_alternate_name(file_path):
    # список языков по приоритету: чем меньше индекс, тем выше приоритет (ru — русский)
    priority = ["ru"]
    # mapping хранит: номер -> (название, приоритет, id, prefer)
    mapping = {}
    count = 0

    if os.path.exists(file_path + ".pkl"):
        with open(file_path + ".pkl", "rb") as f:
            mapping = pickle.load(f)
        logger.info(f"Загружено из кэша {len(mapping)} русских alternateName-записей")
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                count += 1
                if count % 1000000 == 0:
                    logger.info(f"Обработано {count} alternateName-записей")
                parts = line.split("\t")
                if len(parts) < 5:
                    continue  # пропускаем неверно отформатированные строки

                alt_id, number, lang, name, prefer = parts[:5]
                alt_id = int(alt_id)

                if lang not in priority:
                    continue

                current_priority = priority.index(lang)
                # если номер ещё не записан, сохраняем напрямую
                if number not in mapping:
                    mapping[number] = (name, current_priority, alt_id, prefer)
                else:
                    stored_name, stored_priority, stored_id, stored_prefer = mapping[
                        number
                    ]
                    # если приоритет текущей записи выше, обновляем (независимо от prefer)
                    if current_priority < stored_priority:
                        mapping[number] = (name, current_priority, alt_id, prefer)
                    # при одинаковом приоритете делаем доп. проверку
                    elif current_priority == stored_priority:
                        # если у сохранённой записи prefer=1, её нельзя перезаписывать
                        if stored_prefer == "1":
                            continue
                        else:
                            # если prefer новой записи равен "1", у неё выше приоритет — обновляем
                            if prefer == "1":
                                mapping[number] = (
                                    name,
                                    current_priority,
                                    alt_id,
                                    prefer,
                                )
                            # иначе (без prefer) при разных id обновляем: считаем это новой записью
                            elif alt_id >= stored_id:
                                mapping[number] = (
                                    name,
                                    current_priority,
                                    alt_id,
                                    prefer,
                                )
                            # иначе (id совпадает и нет prefer) сохраняем прежнюю запись
        logger.info(f"Загружено всего {len(mapping)} русских alternateName-записей")
        with open(file_path + ".pkl", "wb") as f:
            pickle.dump(mapping, f)
    # возвращаем итоговый словарь: только номер -> русское название
    d = {key: value[0] for key, value in mapping.items()}

    with open("./dict.txt") as f:
        for l in f:
            if len(l) == 0:
                continue
            id, name = l.strip().split("\t")
            d[id] = name

    return d
