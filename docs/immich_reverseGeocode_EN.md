# How reverse geocoding works in Immich and the Russian localization approach

[🇷🇺 Русский](immich_reverseGeocode.md) | **🇬🇧 English**

By default Immich determines photo locations quite strangely: not only in English, but also using unusual names. This creates big problems when sorting and searching photos. Over the weekend I studied in detail how exactly Immich implements reverse geocoding and tried to localize it. If you are here to implement localization of place names, skip straight to [this project](https://github.com/Brooklyn2001/immich-geodata-ru).

## How reverse geocoding works in Immich

To achieve the localization goal, you first need to understand how Immich performs reverse geocoding locally.

### Reverse geocoding

Let's look at the example of v1.124.2. Reverse geocoding in Immich is implemented in the [`reverseGeocode`](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L108) function. It receives a `GeoPoint` object, which is essentially a longitude and latitude. Then the following SQL query is run for these coordinates:

```sql
SELECT * FROM geodata_places
WHERE earth_box(ll_to_earth_public(${point.latitude}, ${point.longitude}), 25000) @> ll_to_earth_public(latitude, longitude)
ORDER BY earth_distance(ll_to_earth_public(${point.latitude}, ${point.longitude}), ll_to_earth_public(latitude, longitude))
LIMIT 1;
```

Here:
- `earth_box` creates a spherical region centered on the given point.
- `ll_to_earth_public` converts geographic coordinates (latitude and longitude) into a point on a three-dimensional sphere.
- The `WHERE` clause selects geographic points within 25,000 meters (25 km) of the input point.
- `ORDER BY` sorts them by distance from nearest to farthest.

In other words, it finds the closest geographic point in the `geodata_places` table to the input point. After finding the nearest point, it extracts `{ countryCode, name: city, admin1Name }` — the country code, the name, and the name of the first-level administrative unit. Then the order is aligned and the country code is converted into a country name. This corresponds to the three location levels of a photo in Immich: **country, province, city**.

The name and the first-level administrative unit name are taken directly from the database table, while the country name is obtained from the country code using the `getName` method of the [`node-i18n-iso-countries`](https://github.com/michaelwittig/node-i18n-iso-countries) library. However, in the Immich code the call looks like `getName(countryCode, 'en')` — the language is hardcoded to `'en'`, so the result is always in English, and no i18n mechanism is provided.

If the above search returns nothing, another SQL query is run:

```sql
SELECT * FROM naturalearth_countries
WHERE coordinates @> point(:longitude, :latitude)
LIMIT 1;
```

This query looks for records in the `naturalearth_countries` table whose coordinates contain the input coordinates, that is, it determines the country by the country borders in the Natural Earth dataset. If this path is used, the more detailed determination of province and city is no longer performed.

In short: Immich prepares many geographic names in advance in the database, then matches the photo coordinates to the nearest name in the database and uses it as the place name. If nothing is found, it falls back to using only country information based on its administrative division.

### Building the data

The next important question: where does the data in the database come from? All of Immich's reverse-geocoding data comes from [GeoNames](https://www.geonames.org/) and is placed in the `/build/geodata` folder. With every release the freshest data is [downloaded](https://download.geonames.org/export/dump/) from there.

The folder contains the following files:
- `admin1CodesASCII.txt`: list of first-level administrative units (id | name | name ascii | geoname id)
- `admin2Codes.txt`: list of second-level administrative units (id | name | name ascii | geoname id)
- `cities500.txt`: list of all cities with a population of more than 500 people
- `geodata-date.txt`: data update date
- `ne_10m_admin_0_countries.geojson`: Natural Earth country borders, [more details here](https://github.com/nvkelso/natural-earth-vector/tree/master)

The import entry point is the [`init`](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L41C1-L42C1) function. First it checks the `reverse-geocoding-state` value in `system-metadata`, which stores the `lastUpdate` time — the time of the last data import. This time is compared with the time in the `geodata-date.txt` file. If the file time is newer, there is updated data and the import starts; otherwise it is skipped to avoid re-importing.

The import logic is in [`importGeodata`](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L207). Besides the table creation logic, the key function is [`loadCities500`](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L226C3-L226C11). The `cities500.txt` file has a CSV-like format with `\t` as the separator. The conversion to database content follows these rules:

```javascript
id: Number.parseInt(lineSplit[0]),
name: lineSplit[1],
alternateNames: lineSplit[3],
latitude: Number.parseFloat(lineSplit[4]),
longitude: Number.parseFloat(lineSplit[5]),
countryCode: lineSplit[8],
admin1Code: lineSplit[10],
admin2Code: lineSplit[11],
modificationDate: lineSplit[18],
admin1Name: admin1Map.get(`${lineSplit[8]}.${lineSplit[10]}`) ?? null,
admin2Name: admin2Map.get(`${lineSplit[8]}.${lineSplit[10]}.${lineSplit[11]}`) ?? null,
```

Here `admin1Map` and `admin2Map` are the mappings from id to name obtained by reading the `admin1CodesASCII.txt` and `admin2Codes.txt` files.

Combined with the reverse-coding logic described above, this means that by latitude and longitude the nearest point is found, then its `countryCode`, `admin1Name` and `name` are taken — and this information becomes the geographic location of the photo.

Correct, `admin2Name` is not used at all, and `admin2Codes.txt` is not used either.

## The localization approach

Immich splits the geographic information of a photo into three levels: **country, province, city**. Let's summarize the roles of the files once more:
- From `cities500.txt` the nearest point is found, and its name is taken as the **city**.
- From the `admin1Code` of this point, the **province** name is found in the `admin1CodesASCII.txt` file.
- From the `countryCode` of this point, the **country** name is obtained via [`node-i18n-iso-countries`](https://github.com/michaelwittig/node-i18n-iso-countries).

Now that the roles are clear, the localization approach becomes obvious.

### Country

This step mostly depends on the [`node-i18n-iso-countries`](https://github.com/michaelwittig/node-i18n-iso-countries) library, and in the [code](https://github.com/immich-app/immich/blob/1311189fab958bea2177a92e1cc1b7ebb1822bd8/server/src/repositories/map.repository.ts#L131) the target conversion language is hardcoded to `en`. Changing the target language is not possible, so the only option is to work with this library's data. The library's data is also implemented as static files, the contents of which can be viewed [here](https://github.com/michaelwittig/node-i18n-iso-countries/tree/master/langs). The `en.json` file is the data source for conversion to `'en'`. We just need to rewrite it into Russian, while the Russian information is in `ru.json`. We simply replace the file as shown [here](https://github.com/Brooklyn2001/immich-geodata-ru/blob/main/i18n-iso-countries/langs/en.json). As a result, the modified file replaces the original one in the Immich image.

### Province

Province names are in the `admin1CodesASCII.txt` file. Fortunately, [GeoNames](https://download.geonames.org/export/dump/) provides the `alternateNamesV2.zip` file, which contains the names of many places in different languages. Using this information, you can directly translate by replacing the original names. The implementation is [here](https://github.com/Brooklyn2001/immich-geodata-ru/blob/main/geodata/translate.py#L119).

### City

The main goal for the `cities500.txt` file is to translate the `name` field. However, when examining this file, you may notice that its granularity is very high: it includes not only cities, but also districts, counties, and very old names, which makes it hardly usable. To solve this problem, it is possible to re-identify these places through the reverse-geocoding API of map providers and obtain standard names of the first- and second-level administrative units. Implemented here for [using Nominatim](https://github.com/Brooklyn2001/immich-geodata-ru/blob/main/geodata/generate_geodata_nominatim.py).

In addition, because of the limited amount of data in the standard `cities500.txt` file, some regions may have few points, which leads to errors during reverse geocoding in Immich. In fact, [GeoNames](https://download.geonames.org/export/dump/) also provides complete geographic point information per country, for example `RU.zip`, which can be added to `cities500.txt` as enhancement. The implementation is [here](https://github.com/Brooklyn2001/immich-geodata-ru/blob/main/geodata/enhance_data.py). However, given the huge amount of data, only large cities are added by default; others can be added as needed.

## Conclusion

The above explains the reverse-geocoding principles in Immich and the approach to its localization. The code is in this [repository](https://github.com/Brooklyn2001/immich-geodata-ru), which also contains ready-to-use solutions.
