# immich-geodata-ru — Russian localization of Immich reverse geocoding

[🇷🇺 Русский](README.md) | **🇬🇧 English**

This project adds **Russian-language** support to the reverse-geocoding feature of Immich. It solves the problem that photo locations are recognized only in English / the original language, and also optimizes the result.

- **Place localization**: for the 15 former Soviet Union countries (Russia, Belarus, Ukraine, Kazakhstan, Uzbekistan, Armenia, Azerbaijan, Georgia, Kyrgyzstan, Tajikistan, Turkmenistan, Moldova, Lithuania, Latvia, Estonia) administrative units (levels 1 through 4) are normalized and replaced with familiar Russian-language names. If there is no Russian name — the local (national) name of the place is used instead.
- **Address standardization**: through the Nominatim API, addresses are normalized into four levels — **1st, 2nd, 3rd, 4th administrative level**, to avoid the non-standard or little-known names that Immich uses by default. The granularity of the output can be chosen separately.
- **Auto-update**: the repository pulls fresh geolocation data weekly and publishes updates automatically.

Example "before / after" comparison:

### Localization comparison example

| Country | Default (English) | Russian localization |
| :--- | :--- | :--- |
| **Russia** | **Moscow**<br>Moscow<br>Russian Federation | **Москва**<br>Москва<br>Россия |
| **Russia** | **Novosibirsk**<br>Novosibirsk Oblast<br>Russian Federation | **Новосибирск**<br>Новосибирская область<br>Россия |
| **Belarus** | **Minsk**<br>Minsk City<br>Republic of Belarus | **Минск**<br>Минск<br>Беларусь |
| **Belarus** | **Gomel**<br>Gomel Oblast<br>Republic of Belarus | **Гомель**<br>Гомельская область<br>Беларусь |
| **Ukraine** | **Kyiv**<br>Kyiv<br>Ukraine | **Киев**<br>Киев<br>Украина |
| **Ukraine** | **Lviv**<br>Lviv Oblast<br>Ukraine | **Львов**<br>Львовская область<br>Украина |
| **Kazakhstan** | **Astana**<br>Astana<br>Kazakhstan | **Астана**<br>Астана<br>Казахстан |
| **Kazakhstan** | **Almaty**<br>Almaty<br>Kazakhstan | **Алматы**<br>Алматы<br>Казахстан |
| **Uzbekistan** | **Tashkent**<br>Tashkent<br>Uzbekistan | **Ташкент**<br>Ташкент<br>Узбекистан |
| **Georgia** | **Tbilisi**<br>Tbilisi<br>Georgia | **Тбилиси**<br>Тбилиси<br>Грузия |
| **Ukraine** | **Lviv**<br>Lviv City Council<br>Ukraine | **Львов**<br>Львівська міська громада *(fallback)*<br>Украина |
| **Lithuania** | **Vilnius**<br>Vilnius City Municipality<br>Lithuania | **Вильнюс**<br>Senamiesčio seniūnija *(fallback)*<br>Литва |
| **Estonia** | **Tallinn**<br>Tallinn<br>Estonia | **Таллинн**<br>Kesklinna linnaosa *(fallback)*<br>Эстония |

> **About the fallback**: names at the micro level (district, municipality) are not always available in Russian. If there is no Russian name, the local (national) one is used — for example, a Ukrainian hromada (`Львівська міська громада`), a Lithuanian seniūnija (`Senamiesčio seniūnija`) or an Estonian city district (`Kesklinna linnaosa`). The city and region names remain Russian.

# How to use

### 1. Download the data

On the [Release](https://github.com/Brooklyn2001/immich-geodata-ru/releases/latest) page, download and unpack the `geodata.zip` and `i18n-iso-countries.zip` files.

Releases are of two types:
- 🔄 [**Auto-updated version**](https://github.com/Brooklyn2001/immich-geodata-ru/releases/tag/auto-release): updated more often, recommended for use. However, due to possible changes in data sources, the generated files can occasionally be unusable. If you run into issues, switch to the manual version and open an issue.
- 🛠️ [**Manual version**](https://github.com/Brooklyn2001/immich-geodata-ru/releases): more stable, good as a fallback.

Versions with the `_full` suffix contain more data — they recognize locations at borders more accurately, but may slow down geocoding.

<details>

<summary>The different `geodata` file suffixes correspond to different accuracy of administrative units (e.g. 3rd or 4th level). Click to see an example, or refer to the Release page.</summary>

Using `Russia, Moscow Oblast, Ramensky District, Ramenskoye` as an example:

|Example|Corresponding file|Extended data<br>more data, more accurate, but slower geocoding|
|:---|:---|:---|
|Moscow Oblast|geodata.zip<br>geodata_admin_2.zip|geodata_full.zip<br>geodata_admin_2_full.zip|
|Ramensky District|geodata_admin_3.zip|geodata_admin_3_full.zip|
|Ramenskoye|geodata_admin_4.zip|geodata_admin_4_full.zip|
|Moscow Oblast, Ramensky District|geodata_admin_2_admin_3.zip|geodata_admin_2_admin_3_full.zip|
|Moscow Oblast, Ramenskoye|geodata_admin_2_admin_4.zip|geodata_admin_2_admin_4_full.zip|
|Ramensky District, Ramenskoye|geodata_admin_3_admin_4.zip|geodata_admin_3_admin_4_full.zip|
|Moscow Oblast, Ramensky District, Ramenskoye|geodata_admin_2_admin_3_admin_4.zip|geodata_admin_2_admin_3_admin_4_full.zip|

</details>

> **Note**: the country name is always shown in Russian (taken from the Russian `ru.json`), and the granularity from `admin_1` downwards is determined by the chosen file. If there is no Russian name for a place, its local (national) name is used — for example, at the micro level in the Baltics and Ukraine Russian names exist for cities and regions, but district/municipal units may stay local (seniūnija, hromada, etc.).

### 2. Configure the Docker container mount

Edit your `docker-compose.yaml`, adding the following volumes (or replace the target folders to match your deployment method):

If you use the official `immich-app/immich-server` image, the paths are:

```yaml
# immich versions >= 1.136.0
volumes:
  - ./geodata:/build/geodata
  - ./i18n-iso-countries/langs:/usr/src/app/server/node_modules/i18n-iso-countries/langs

# immich versions < 1.136.0 (not including)
volumes:
  - ./geodata:/build/geodata
  - ./i18n-iso-countries/langs:/usr/src/app/node_modules/i18n-iso-countries/langs
```

If you use the `imagegenius/immich` image, the paths are (thanks to huazhaozhe [#18](https://github.com/ZingLix/immich-geodata-cn/discussions/18)):

```
volumes:
  - ./geodata:/app/immich/data/geodata
  - ./i18n-iso-countries/langs:/app/immich/server/node_modules/i18n-iso-countries/langs
```

### 3. Restart Immich

Run `docker compose down && docker compose up` to restart Immich.
- If the startup logs contain something like `10000 geodata records imported` — the geodata was successfully updated.
- If there is no such log, try changing the date in the `geodata/geodata-date.txt` file to the current time: Immich updates data only if the file date is newer than the time of the last load.
  ![](./image/importlog.jpg)

### 4. Update metadata

> **Warning**: this step is only needed the first time you use geodata from this project — it updates the positions of all existing photos. It does not need to be repeated for new photos.

Go to "Administration — Jobs", click "Extract metadata" → "All" to run the position update for all photos. When it finishes, all photos will show their location in Russian and support searching in Russian.

# How to update

Simply download the files from the latest Release page again, replace the old ones and restart Immich.

For a quick update you can use the automatic download-and-replace script:

```bash
# cd geodata   — run in the geodata directory

# Download the script
curl -o update.sh https://raw.githubusercontent.com/Brooklyn2001/immich-geodata-ru/refs/heads/main/geodata/update.sh

# Run the update script; the parameter is the desired version, e.g. geodata_admin_2
bash update.sh geodata_admin_2
```

After updating, restart Immich so the data is reloaded. To make the restart automatic, you can add a command like `docker restart immich_server` at the end of the script, or run the update and restart together on a schedule, for example:

```bash
5 5 * * 6 bash /immich_data/geodata/update.sh && docker restart immich_server
```

# How the data is generated

You can learn how it works, or how to generate your own data, [here](https://github.com/Brooklyn2001/immich-geodata-ru/tree/main/geodata).

A detailed breakdown of the granularity patterns (`{admin_2}` etc.), which levels map to `admin_1..admin_4` for each of the 15 countries, and how the fallback to local names works — in [docs/patterns-granularity.md](docs/patterns-granularity_EN.md).

Instructions on adapting the project to your own country and/or language — in [docs/adapting.md](docs/adapting_EN.md).

# License

GPL

# 💖 Support the project

The project promises to remain **free forever**. If it helped you, you can buy the author a coffee ☕ — this helps maintain the project and add new features!

<img src="image/sponsor.jpg" alt="Sponsorship" width="400" />
