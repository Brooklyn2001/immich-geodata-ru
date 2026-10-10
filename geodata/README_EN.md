# How the data is generated

[🇷🇺 Русский](README.md) | **🇬🇧 English**

The following scripts and directories are used in this project to generate and update geographic data:

- `data/` — stores the results of mapping coordinates to locations per country (CSV).
- `dict.txt` — a dictionary of place names applied manually.
- `enhance_data.py` — complements the data with full GeoNames data (e.g. `RU.txt`), improving accuracy.
- `generate_geodata_nominatim.py` — performs reverse geocoding via the **Nominatim API** over `cities500.txt` data for the required countries and writes CSV files to the `data/` directory.
- `prepare_geoname_data.sh` — downloads fresh source data from GeoNames (e.g. `cities500.txt`).
- `release.sh` — the main build/release script: runs everything and packs the full data set.
- `translate.py` — translates (localizes) the generated geodata.
- `update.sh` — a script to automatically download and update geodata; it can be run on a schedule for automation.

To generate the data, just run `bash release.sh`. Example:

```bash
# Preparing GeoNames data
bash prepare_geoname_data.sh
# Generating data
# ru-pattern: controls the format of the local data, {} are replaced with values;
#             allowed values admin_1,admin_2,admin_3,admin_4 — different administrative unit levels
# output: output file
# full: whether to use the extended data
bash generate_data.sh --ru-pattern "{admin_2} {admin_3}" --output "output/geodata.zip" --full
```

If you need to add more regions, change the parameters in the scripts:

- The list of countries for the **extended** data: change `LIST` in `prepare_geoname_data.sh` (line ~16).
- The list of countries to be geocoded via Nominatim: change `LIST` in `generate_data.sh`.

If you need customization, read on.

## How Immich works

Before understanding how the data is generated, you need to understand the reverse-geocoding principle of Immich.

> More about the principle can be read in [this article](../docs/immich_reverseGeocode_EN.md).

Immich uses the following files for reverse geocoding (they sit in the `/build/geodata` folder):

- `admin1CodesASCII.txt`: list of 1st-level administrative units (`id | name | name ascii | geoname id`)
- `admin2Codes.txt`: list of 2nd-level administrative units (`id | name | name ascii | geoname id`)
- `cities500.txt`: list of all cities with a population of over 500 people
- `geodata-date.txt`: data update date
- `ne_10m_admin_0_countries.geojson`: Natural Earth country division, [more](https://github.com/nvkelso/natural-earth-vector/tree/master)

Immich turns the photo coordinates into **country, region, city** (three levels). The process is:

- it finds the nearest point in `cities500.txt` and takes its name as the **city**;
- from the `admin1Code` field of this point it finds the **region** name in `admin1CodesASCII.txt`;
- from the `countryCode` field of the point it gets the **country** name via the [node-i18n-iso-countries](https://github.com/michaelwittig/node-i18n-iso-countries) library.

> Yes, `admin2Name` is not used at all, nor is `admin2Codes.txt`.

Therefore, for localization it is enough to:

- replace the names in `cities500.txt` and `admin1CodesASCII.txt` with Russian;
- replace the data in the [node-i18n-iso-countries](https://github.com/michaelwittig/node-i18n-iso-countries) library with Russian.

In the [Immich code](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L131) the country-code conversion is hardcoded to `'en'`, so the only option is to replace `en.json` from [node-i18n-iso-countries](https://github.com/michaelwittig/node-i18n-iso-countries) with Russian data. The resulting file is [here](https://github.com/Brooklyn2001/immich-geodata-ru/blob/main/i18n-iso-countries/langs/en.json).

## Localizing the geodata

The source geographic data comes from GeoNames; you can download it [here](https://download.geonames.org/export/dump/).

The general process:

```bash
# Get fresh data
bash prepare_geoname_data.sh
# Enhance the source data (for the countries in LIST: all 15 former Soviet Union countries)
python enhance_data.py
# Reverse geocoding via the Nominatim API
LIST=("RU" "BY" "UA" "KZ" "UZ" "AM" "AZ" "GE" "KG" "TJ" "TM" "MD" "LT" "LV" "EE")
for item in "${LIST[@]}"; do
    python generate_geodata_nominatim.py --country-code "$item"
done
# Localizing the files
python translate.py
```

### Localizing admin1ASCII.txt

> `translate_admin1()` in `translate.py`

This part of the data is relatively simple and stable: GeoNames provides [alternateNamesV2.zip](https://download.geonames.org/export/dump/alternateNamesV2.zip), which contains alternative names of all places. It is enough to find the Russian names of the corresponding places (language field `ru`) in it and replace the originals with them.

Of course, Russian names in alternateNamesV2 are not available for all units, but for large countries there is usually enough data. If you have more complete translation data or improvement ideas — welcome, create an issue or PR.

Although `admin2.txt` is not used, it is localized in the same way.

### Localizing cities500.txt

> `translate_cities500()` in `translate.py`

The original names in the file are too detailed — many go down to the rural-soviet level, which is very inconvenient for searching. Therefore, during localization everything is brought to the three levels of **country, 1st level, 2nd level**, for example:

- Russia, Moscow Oblast, Moscow
- Belarus, Minsk Oblast, Minsk
- Ukraine, Kyiv Oblast, Kyiv

These data are obtained during reverse geocoding; the `data` folder stores the data of all points and the 4th level. If you need to change the granularity — change the data level in `translate.py`.

`cities500` are cities with a population of more than 500 people, but the population data in it is not always accurate, which is why Immich can locate a place inaccurately. Fortunately, GeoNames provides full data for individual countries, and they can be added when needed. `enhance_data.py` can read full country data from `./geoname_data/extra_data` and add to `cities500.txt` entries with a population above 100 or specific entries (for example, for federal cities); the settings can be changed in the code. This way `cities500.txt` gets more detailed data.

Next, it remains to replace the data of the 2nd and 3rd columns in `cities500.txt` by an explicit cascade (each branch is logged with a reason, see below):

- if there is data for the country in the `data` folder — replace with the **2nd-level** name (the `--ru-pattern` pattern);
- if GeoNames alternateNamesV2 has a Russian name — replace with it;
- if a Russian name is found in the 4th column (alternate names) — replace with it;
- if nothing is found — keep the original (local/national) name.

**Integrity invariant**: if a point is in `data`, but it has no required pattern level
(for example, `admin_2`), the row is **skipped** — a partial result is not written. Otherwise
Immich would "remember" an incomplete name and not recalculate it later.

**Cascade diagnostics**: each branch logs the reason for choosing a name at the `DEBUG`
level (which branch fired and what was taken). To enable:
```bash
LOG_LEVEL=DEBUG python translate.py
```

A detailed breakdown of the granularity patterns (`--ru-pattern`), the selection of
`admin_1..admin_4` levels by the `resolver-profiles.json` profiles for all 15 countries, and
the effect of the fallback on the final names — in [docs/patterns-granularity.md](../docs/patterns-granularity_EN.md).
