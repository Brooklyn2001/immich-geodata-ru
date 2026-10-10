# Adapting the project to your own country and/or language

[🇷🇺 Русский](adapting.md) | **🇬🇧 English**

This guide is for those who want to adapt the immich-geodata-ru project to their own country and, if needed, to a different localization language (not Russian).

> The project is focused on the Russian localization of the 15 former Soviet Union countries. The main `main` branch stays Russian. For your own country/language it is recommended to make a **separate fork or branch**, not to rewrite the Russian version.

---

## 1. What changes when adding a country (same language, Russian)

Countries are **not hardcoded anywhere** — they are defined by three lists and one profile. It is enough to bring them into alignment.

### 1.1 Country lists

All four places must contain the same set of country ISO codes:

1. `geodata/prepare_geoname_data.sh:16` — the list for downloading **full data** (`LIST=("RU" "BY" ... "EE")`).
2. `geodata/generate_data.sh:49` — the list of countries for **geocoding** via Nominatim (the same `LIST`).
3. `.github/workflows/download-geonames.yaml:26` — the country list in the CI workflow for downloading sources (if used).
4. `geodata/resolver-profiles.json` → the `countries.<CODE>` block — a **required** per-country profile (see below).

> If you only want to *add* a country to the existing ones — just put its code into these three lists and add the profile. If you want to *replace* — remove the old codes and profiles.

### 1.2 The country profile in `resolver-profiles.json`

This is a required part. Without a profile the country will not be geocoded correctly: the `admin_level` hierarchy in OSM/Nominatim is inconsistent across countries, so preferred levels for the `admin_1..admin_4` roles are defined per country.

```json
"XX": {
  "admin_levels": {
    "admin_1": [3, 4],
    "admin_2": [4, 5, 6],
    "admin_3": [6, 7, 8, 9],
    "admin_4": [8, 9, 10]
  },
  "country_code_verify": true
}
```

How to pick the sets: look at which `level3..level10` Nominatim actually returns for the target country, and what the name coverage is in the required language. The sets are tested on several cities. How the levels map to roles — see [patterns-granularity.md](patterns-granularity_EN.md).

### 1.3 Other

- Country names come from `i18n-iso-countries` (see section 2, "country language").
- If the country has poor point coverage with the basic `cities500`, `--full` (full country dumps) may be needed — already supported via `enhance_data.py`.

---

## 2. What changes when switching the language (not Russian)

Russian is "embedded" in several layers, so switching the language affects more places. The general idea: remove Russian from **all** inputs so that the name cascade (see item 2.4) works in the target language.

### 2.1 The language of the Nominatim request

`geodata/generate_geodata_nominatim.py:100`:

```python
params = { ..., "accept-language": "ru,ru-RU;q=0.9,en;q=0.8" }
```

Replace `ru` with the target language code (for example `en,en;q=0.9` or `de,de-DE...`). This affects which names the geocoder returns at the macro level (oblast/region).

### 2.2 The language priority in alternate names

`geodata/utils.py:63` in `load_alternate_name`:

```python
priority = ["ru"]   # list of languages by priority
```

Replace with the target language code. Also adjust the log texts ("Russian alternateName records" → neutral), that is cosmetic.

### 2.3 Detecting the "native" word for the fallback

`geodata/translate.py:136-143`, the `is_russian()` function:

```python
def is_russian(text):
    ...
    for char in text:
        lowercase = char.lower()
        if not ("\u0430" <= lowercase <= "\u044f" or lowercase == "\u0451"):
            return False
    return True
```

This function looks for "a word in the target language" among the point's candidate names as a fallback source. For another language it must be replaced with a detector of the target script (for example, Latin or specific letters). For Latin-script languages — a check against the `a–z` range (+ national letters).

### 2.4 The country language (i18n-iso-countries)

Immich reads the country name **hardcoded from `en.json`**, but the **data is taken from `ru.json`** (see `geodata/translate_country_info.py`). Do not confuse the source with the reading place:

- instead of `ru.json`, the source of country names will become the target-language JSON (for example `de.json`);
- `en.json` remains the **place** where Immich reads the locale — the names in the target language go there.

### 2.5 The semantics of the `--ru-pattern` flag

The flag/file names are focused on Russian (a legacy of the original `--cn-pattern`). This is cosmetic and does not need to be changed. Important: **do not roll back** the logic to the Chinese `cn`/`amap` solutions — this Russian implementation is already ported to Nominatim.

---

## 3. The name cascade and fallback — how it switches to the new language

The cascade in `geodata/translate.py:101-130` works by descending priority:

1. **From geodata** (`ru_pattern.format(...)`) — names already geocoded by Nominatim. They become the target language after the edit in item 2.1.
2. **From alternateNamesV2** (`alternate_name[geonameid]`) — after the edit in item 2.2.
3. **The "native" word from the candidates** (`is_russian`) — after the edit in item 2.3.
4. **Original without replacement** — the local/national name if the required language is not found anywhere.

That is, the logic itself will start working in the target language if the language is changed in **all three** inputs (2.1, 2.2, 2.3).

> **Integrity invariant**: if a point is in geodata but has no required `admin_2` — the row is skipped (`translate.py:87-92`), a partial result is not written. This holds for any language.

---

## 4. Coverage and verification

- For the former Soviet Union countries, Russian names exist in Nominatim (excellent for RU/BY, weak for the Baltics/Ukraine at the micro level).
- For a country outside the region, coverage in the target language in Nominatim / alternateNamesV2 may be absent — then the **fallback to local names** (step 4) will trigger more often. It is worth checking on real points before a full build.

### Verification

```bash
cd geodata
python -m py_compile *.py                       # syntax
python -m unittest discover -s tests -p "test_*.py"   # unit tests
```

Changes must not break the generation pipeline or the unit tests.
