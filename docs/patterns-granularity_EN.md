# Name granularity: `--ru-pattern` patterns and per-country levels

[🇷🇺 Русский](patterns-granularity.md) | **🇬🇧 English**

This document explains in detail how the project turns a geographic point into a location name in Immich: what the granularity patterns (`{admin_2}` etc.) are, how `admin_1..admin_4` levels are selected from country profiles, and how this affects the final names (including the fallback to local names).

> A short version for the user is in [README](../README_EN.md).
> The reverse-geocoding principle of Immich is in [immich_reverseGeocode.md](immich_reverseGeocode_EN.md).
> The pipeline description is in [geodata/README.md](../geodata/README_EN.md).
> How to adapt the project to your own country/language is in [adapting.md](adapting_EN.md).

---

## 1. What the "7 granularity patterns" are

`--ru-pattern` is a parameter that defines **which administrative levels go into the name** and in which order. All 7 variants are listed in `release.sh`:

```bash
LIST=("{admin_2}" "{admin_3}" "{admin_4}"
      "{admin_2} {admin_3}" "{admin_2} {admin_4}" "{admin_3} {admin_4}"
      "{admin_2} {admin_3} {admin_4}")
```

That is:

- **3 single** — only one level: `{admin_2}`, `{admin_3}`, `{admin_4}`;
- **3 pairwise** — two levels: `{admin_2} {admin_3}`, `{admin_2} {admin_4}`, `{admin_3} {admin_4}`;
- **1 full** — all three levels: `{admin_2} {admin_3} {admin_4}`.

> `admin_1` is never included in the pattern: it is the highest administrative level
> (okrug, county, federal city), which is not output into the name.

Each pattern is built **twice**: the normal version (based on the basic `cities500`) and the `--full` version (complemented with complete country dumps via `enhance_data.py`). In total the archive contains **14 zip files** (7 patterns × 2 variants). The default pattern — `{admin_2}` — is additionally copied to `geodata.zip` and `geodata_full.zip` (see `release.sh`).

Immich uses exactly one file. Choosing a file = choosing the name granularity.

## 2. What `admin_1..admin_4` are

These are the administrative levels inside a country (roles):

| Role | Meaning |
| :--- | :--- |
| `admin_1` | highest level (okrug, county, federal city) |
| `admin_2` | oblast / region |
| `admin_3` | district / municipality |
| `admin_4` | city / populated place |

Which exact levels go into each role is determined by **per-country profiles** in `resolver-profiles.json` (Variant C), not by a single global rule. The reason: the `admin_level` hierarchy in OSM/Nominatim is **inconsistent across countries**, and the coverage of Russian names also differs.

## 3. The level selection mechanism: `pick_admin_levels`

Code — `generate_geodata_nominatim.py:61-78`.

1. The geocoder calls Nominatim (`accept-language: ru`). The response contains an `admin` dictionary like `{ level3: "…", level4: "…", level6: "…", level8: "…", level10: "…" }` — these are **raw OSM/Nominatim levels**, and they are not required to be consecutive (level5 may be missing while level4 and level6 exist).
2. For **each role** `admin_1..admin_4` the function:
   - takes the candidate list `profile["admin_levels"][role]` (for example, for RU `admin_2: [4]`);
   - iterates the candidates in list order;
   - chooses **the first level that is present in the response and not yet taken** by the previous role (the `used` guard against duplicating one level across two roles);
   - puts it into `levels["admin_N"]`; if no suitable level exists — **an empty string**.

That is, the profile defines a set of "preferred" levels for each role, and the greedy selection algorithm picks up the nearest available one.

## 4. Final levels for all 15 countries

Below is the result of `pick_admin_levels` for two Nominatim response scenarios.

### 4.1 "Rich" response — all level3..10 present (large cities)

| Country | admin_1 | admin_2 | admin_3 | admin_4 |
| :--- | :---: | :---: | :---: | :---: |
| RU | l3 | l4 | l6 | l8 |
| BY | l4 | l6 | l9 | l10 |
| UA | l4 | l6 | l8 | l10 |
| KZ | l4 | l6 | l7 | l8 |
| UZ | l4 | l5 | l6 | l10 |
| AM | l4 | l5 | l7 | l8 |
| AZ | l6 | — | l8 | — |
| GE | l4 | l6 | l8 | l10 |
| KG | l4 | l6 | — | l7 |
| TJ | l4 | l6 | — | l7 |
| TM | l4 | l5 | l6 | l7 |
| MD | l4 | l8 | — | l9 |
| LT | l4 | l5 | l8 | l10 |
| LV | l5 | l8 | l9 | l10 |
| EE | l6 | l7 | l8 | l9 |

### 4.2 "Typical" response — only level3,4,6,8,10 (a common reality)

| Country | admin_1 | admin_2 | admin_3 | admin_4 |
| :--- | :---: | :---: | :---: | :---: |
| RU | l3 | l4 | l6 | l8 |
| BY | l4 | l6 | — | l10 |
| UA | l4 | l6 | l8 | l10 |
| KZ | l4 | l6 | — | l8 |
| UZ | l4 | l6 | — | l10 |
| AM | l4 | — | — | l8 |
| AZ | l6 | — | l8 | — |
| GE | l4 | l6 | l8 | l10 |
| KG | l4 | l6 | — | — |
| TJ | l4 | l6 | — | — |
| TM | l4 | — | l6 | — |
| MD | l4 | l8 | — | l10 |
| LT | l4 | — | l8 | l10 |
| LV | — | l8 | — | l10 |
| EE | l6 | — | l8 | l10 |

### How to read "—"

`—` means an **empty string**: the role was not filled because:

- the required level was not present in the Nominatim response; or
- the level was **already taken** by the previous role (the `used` guard).

Example — `AZ`: `admin_1: [6]` takes l6, while `admin_2: [6]` points to the same level → `admin_2` is empty.

### Key patterns

- **RU is the only country where all 4 slots are consistently filled** in both scenarios (l3/l4/l6/l8), so Russian names are covered at all levels.
- **BY, UA, GE, KZ** always fill `admin_1`+`admin_2`; `admin_3` depends on whether l8/l9 is present in the response.
- **Small/inconsistent countries** (AM, AZ, KG, TJ, TM, MD) often leave `admin_2` and/or `admin_3` empty — this is exactly where the fallback to local names shows up.
- **The Baltics (LT/LV/EE)** assign roles to high levels (l5–l10): Russian names there are often absent at the micro level → local names.

## 5. How a pattern becomes a name

The final string is assembled by `translate.py` (line `:93`):

```python
res = ru_pattern.format(**location)
```

`{admin_2}` is substituted with the value of the corresponding role; empty roles give empty substitutions.

### Example on real RU.csv data

Point: Voronezh Oblast, Voronezh Urban Okrug, Maloprivalovskoye Rural Settlement
(`admin_1` = Central Federal District, `admin_2` = Voronezh Oblast,
`admin_3` = Voronezh Urban Okrug, `admin_4` = Maloprivalovskoye Rural Settlement):

| Pattern | Final name |
| :--- | :--- |
| `{admin_2}` | Voronezh Oblast |
| `{admin_3}` | Voronezh Urban Okrug |
| `{admin_4}` | Maloprivalovskoye Rural Settlement |
| `{admin_2} {admin_3}` | Voronezh Oblast Voronezh Urban Okrug |
| `{admin_2} {admin_4}` | Voronezh Oblast Maloprivalovskoye Rural Settlement |
| `{admin_3} {admin_4}` | Voronezh Urban Okrug Maloprivalovskoye Rural Settlement |
| `{admin_2} {admin_3} {admin_4}` | Voronezh Oblast Voronezh Urban Okrug Maloprivalovskoye Rural Settlement |

This point has all levels filled, so all 7 patterns are meaningful — the difference is only in granularity: from "Voronezh Oblast" to a full three-level hierarchy.

### Empty levels produce "trailing spaces"

If a point has no `admin_4` (for example, "Moscow" / "Cheryomushki District" without a city-level entry), patterns with `{admin_4}` produce a trailing space:

| Pattern | Name |
| :--- | :--- |
| `{admin_2}` | Москва |
| `{admin_3}` | район Черёмушки |
| `{admin_4}` | *(empty)* |
| `{admin_2} {admin_3} {admin_4}` | `Москва район Черёмушки ` *(trailing space)* |

These "trailing spaces" do not end up in the production file (the default pattern `{admin_2}`).

## 6. Fallback to local names

### The name-selection cascade in `translate.py` (`:101-130`), by descending priority

1. **From geodata** (already geocoded via Nominatim, `ru`): `ru_pattern.format(...)`.
   If the point has no required `admin_2` — the row is **skipped** (integrity invariant, `:87-92`), not written partially.
2. **Russian name from `alternateNamesV2`** (priority `ru`): `alternate_name[geonameid]`.
3. **Russian word from the candidates** (`alternatenames` in cities500): the first word consisting only of Cyrillic (`is_russian`).
4. **Original without replacement**: if Russian is not found at any step — the **local (national) name** remains.

Step 4 is a **deliberate invariant from AGENTS.md**, not a bug: if there is no Russian name at the micro level, we do not invent or replace it, but keep the national one.

### Why the fallback appears

Russian names in Nominatim cover mainly the **macro level** (region/oblast) and cities. At the **micro level** in the Baltics (seniūnija, linnaosa) and Ukraine (hromada) Russian names are often absent — local names remain there.

Examples under the `{admin_2} {admin_3} {admin_4}` pattern (based on real country profiles):

| Country | Final name | Why |
| :--- | :--- | :--- |
| LV | `Vidzeme Cēsu novads Cēsu pilsēta` | no Russian at the micro level (novads) |
| EE | `Harju maakond Tallinna linn Nõmme linnaosa` | linnaosa/seniūnija — local |
| UA | `Вінницька область Вінницький район Агрономічне` | macro translated, micro (hromada) — local |
| KG | `Чүй облусу Аламүдүн району Лебединовка` | the level names are Kyrgyz (облусу/району) |
| RU | `Московская область Одинцовский городской округ Одинцово` | everything Russian — the fallback does not trigger |

### Practical conclusion

The more levels in the pattern (closer to `{admin_2} {admin_3} {admin_4}`), the more often a national word (novads, linnaosa, hromada, району) appears at the end of the name, because Russian names exist mainly at the macro level. Therefore the default pattern in Immich is `{admin_2}`: it produces clean Russian region names without traces of local micro levels.
