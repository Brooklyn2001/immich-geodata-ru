import requests
import os
import csv
import json
from utils import logger, GEODATA_HEADER, load_geo_data
from requests.adapters import HTTPAdapter, Retry
import argparse
from ratelimit import limits, sleep_and_retry

parser = argparse.ArgumentParser()

parser.add_argument(
    "--data-file",
    type=str,
    default="./geoname_data/cities500.txt",
    help="входной файл geodata",
)

parser.add_argument(
    "--country-code", type=str, default="RU", help="код страны для генерации"
)
# Разбор аргументов
args = parser.parse_args()

NOMINATIM_QPS = int(os.environ.get("NOMINATIM_QPS", "1"))

GEONAME_DATA_FILE = args.data_file

s = requests.Session()

retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[403, 500, 502, 503, 504])

s.mount("https://", HTTPAdapter(max_retries=retries))
s.headers.update(
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Referer": "https://jfioasdfo.com",
    }
)

# Загружаем профили разрешения названий по странам
_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "resolver-profiles.json")
try:
    with open(_PROFILES_PATH, encoding="utf-8") as _pf:
        PROFILES = json.load(_pf)
except FileNotFoundError:
    PROFILES = {
        "default": {"admin_levels": {}, "country_code_verify": False},
        "countries": {},
    }


def get_profile(country_code):
    """Профиль страны: default, переопределяемый записями по стране."""
    profile = dict(PROFILES.get("default", {}))
    profile.update(PROFILES.get("countries", {}).get(country_code, {}))
    return profile


def pick_admin_levels(admin, profile):
    """Для ролей admin_1..admin_4 выбираем первый уровень из набора профиля,
    присутствующий в ответе и ещё не занятый предыдущей ролью."""
    levels = {}
    used = []
    for num in range(1, 5):
        role = f"admin_{num}"
        candidates = profile.get("admin_levels", {}).get(role, [])
        chosen = None
        for lvl in candidates:
            key = f"level{lvl}"
            if key in admin and key not in used:
                chosen = lvl
                break
        levels[role] = admin.get(f"level{chosen}") if chosen else ""
        if chosen:
            used.append(f"level{chosen}")
    return levels


def country_mismatch(returned_code, expected_code):
    """True, если возвращённый страной ISO-код не совпадает с ожидаемым.

    Проверка по ISO-коду (country_code) надёжнее, чем по имени: имена стран в
    Nominatim (accept-language: ru) расходятся с ru.json (например, Кыргызстан/
    Киргизия, Туркмения/Туркменистан, Беларусь/Белоруссия), а код всегда тот же.
    """
    return (returned_code or "").strip().upper() != (expected_code or "").strip().upper()


@sleep_and_retry
@limits(calls=NOMINATIM_QPS, period=1)
def get_loc_from_locationiq(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"

    params = {
        "lat": lat,
        "lon": lon,
        "format": "geocodejson",
        "accept-language": "ru,ru-RU;q=0.9,en;q=0.8",
    }

    try:
        response = s.get(url, params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(e)
        logger.error(f"{lat},{lon} не удалось получить местоположение")
        pass
    return None


def process_file(file_path, country_code, output_file, existing_data={}):
    # Открываем и читаем файл
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            fields = line.strip().split("\t")

            # Проверяем код страны
            if len(fields) > 17 and fields[8] == country_code:
                loc = {"lon": str(fields[5]), "lat": str(fields[4])}
                if (loc["lon"], loc["lat"]) in existing_data:
                    continue
                query_and_store(loc, output_file, country_code)


def query_and_store(coordinate, output_file, country_code):
    response = get_loc_from_locationiq(coordinate["lat"], coordinate["lon"])
    profile = get_profile(country_code)

    if response and "features" in response and len(response["features"]) > 0:
        address = response["features"][0]["properties"]["geocoding"]
        admin = address["admin"]

        # Проверка принадлежности стране (если включена в профиле) —
        # сравниваем по ISO-коду, который возвращает Nominatim, а не по имени
        if profile.get("country_code_verify", True):
            returned_code = address.get("country_code") or ""
            if returned_code and country_mismatch(returned_code, country_code):
                logger.warning(
                    f"{coordinate['lat']},{coordinate['lon']}: страна "
                    f"'{returned_code}' не совпадает с ожидаемой '{country_code}', "
                    f"запись пропущена"
                )
                return

        levels = pick_admin_levels(admin, profile)
        record = {
            "latitude": coordinate["lat"],
            "longitude": coordinate["lon"],
            "country": address["country"],
            "admin_1": levels["admin_1"],
            "admin_2": levels["admin_2"],
            "admin_3": levels["admin_3"],
            "admin_4": levels["admin_4"],
        }
    else:
        # Выводим неудачные координаты
        logger.error(f"Ошибка запроса, координаты: {coordinate}")
        record = {
            "latitude": coordinate["lat"],
            "longitude": coordinate["lon"],
            "country": "",
            "admin_1": "",
            "admin_2": "",
            "admin_3": "",
            "admin_4": "",
        }

    with open(output_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=GEODATA_HEADER)

        # Если файл пуст, записываем заголовок
        if file.tell() == 0:
            writer.writeheader()

        # Записываем данные
        writer.writerows([record])


def main():
    country_code = args.country_code
    logger.info(f"Обрабатываемый код страны: {country_code}")
    if not os.path.isfile(GEONAME_DATA_FILE):
        raise Exception(f"Файл '{GEONAME_DATA_FILE}' не существует, скачайте и повторите.")
    output_file = os.path.join("data", f"{country_code}.csv")
    os.makedirs("data", exist_ok=True)
    existing_data = load_geo_data(output_file)
    process_file(
        GEONAME_DATA_FILE, country_code, output_file, existing_data=existing_data
    )


if __name__ == "__main__":
    main()
