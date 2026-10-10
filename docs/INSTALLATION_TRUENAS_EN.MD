# Adding Russian-language reverse geocoding to Immich on TrueNAS

[🇷🇺 Русский](INSTALLATION_TRUENAS.MD) | **🇬🇧 English**

This guide assumes that Immich is already installed and running on your TrueNAS (SCALE). We will add support for Russian-language place names using the `immich-geodata-ru` project.

## What will change

After following the instructions, photo locations in Immich will be displayed in Russian (for example, "Москва, Россия" instead of "Moscow, Russian Federation"), and you will also be able to search photos by Russian geographic names.

## Step 1: Downloading the data

1. Go to the project's release page:  
   [https://github.com/Brooklyn2001/immich-geodata-ru/releases/latest](https://github.com/Brooklyn2001/immich-geodata-ru/releases/latest)

2. Download two archives:
   - `geodata.zip` — data about cities and administrative units
   - `i18n-iso-countries.zip` — country data in Russian

   > **Important:** Choose the file with the accuracy you need. The `_admin_2`, `_admin_3`, `_admin_4` suffixes and their combinations determine the level of detail (region, district, city). Files with `_full` contain more data, but work slower. If you are not sure — start with the regular `geodata.zip`.

3. Unpack both archives into a separate folder on your TrueNAS. It is recommended to create it inside the dataset used to store the Immich configuration. For example:

   ```bash
   mkdir -p /mnt/ваш-пул/immich/immich-geodata-ru/geodata
   mkdir -p /mnt/ваш-пул/immich/immich-geodata-ru/i18n-iso-countries/langs
   ```

   Unpack `geodata.zip` into the `geodata` folder, and `i18n-iso-countries.zip` into `i18n-iso-countries` (a `langs` subfolder should appear inside).

   In the end, the structure should look like this:

   ```
   /mnt/ваш-пул/immich/immich-geodata-ru/
   ├── geodata/
   │   ├── cities500.txt
   │   ├── admin1CodesASCII.txt
   │   ├── ... (other files)
   │   └── geodata-date.txt
   └── i18n-iso-countries/
       └── langs/
           ├── ru.json
           └── ... (other languages)
   ```

## Step 2: Adding the mount to the Immich container

The method depends on how exactly you deployed Immich on TrueNAS.

### Option A: Immich installed via Custom App (Docker Compose)

If you installed Immich via **Custom App** using YAML (as described in the official TrueNAS documentation), find your application's `docker-compose.yml` file. It is usually located at `/mnt/ваш-пул/apps/immich/docker-compose.yml` or a similar location.

Open the file and add two lines to the `volumes` section of the `immich-server` service. The paths on the left are your local folders, on the right — the target paths inside the container. For the official `immich-app/immich-server` image of version **1.136.0 and above**, use these target paths:

```yaml
services:
  immich-server:
    # ... (rest of the configuration)
    volumes:
      # ... (existing volumes)
      - /mnt/ваш-пул/immich/immich-geodata-ru/geodata:/build/geodata
      - /mnt/ваш-пул/immich/immich-geodata-ru/i18n-iso-countries/langs:/usr/src/app/server/node_modules/i18n-iso-countries/langs
```

> **Note:** If you use the `imagegenius/immich` image (often found in TrueNAS community apps), the paths are different:
> ```yaml
> - /mnt/ваш-пул/immich/immich-geodata-ru/geodata:/app/immich/data/geodata
> - /mnt/ваш-пул/immich/immich-geodata-ru/i18n-iso-countries/langs:/app/immich/server/node_modules/i18n-iso-countries/langs
> ```

### Option B: Immich installed via the built-in TrueNAS app

If Immich was installed as a regular app through the **Apps** catalog in the TrueNAS web interface, adding extra volumes may be impossible without recreating the application. In this case:

1. Make a backup of the Immich configuration and database.
2. Delete the Immich app (data on the datasets will be preserved).
3. Reinstall Immich via **Custom App** → **Install via YAML**, adding the required volumes as described in option A.

> This is the only reliable way to add arbitrary mounts to an app installed through the standard TrueNAS installer.

## Step 3: Restarting Immich

After changing `docker-compose.yml`, restart the Immich containers:

```bash
cd /mnt/ваш-пул/apps/immich
docker compose down
docker compose up -d
```

If you use a Custom App through the TrueNAS web interface, simply restart the app via the **Restart** button in the Apps interface.

## Step 4: Verifying the geodata import

After startup, check the `immich-server` container logs:

```bash
docker logs immich-server 2>&1 | grep -i geodata
```

On a successful import you should see a message similar to:

```
10000 geodata records imported
```

If there is no such message, the problem is most often that Immich does not consider the data "new". Immich updates geodata only if the date in the `geodata-date.txt` file is newer than the time of the last import. Open the file `/mnt/ваш-пул/immich/immich-geodata-ru/geodata/geodata-date.txt` and change the date to the current one (or any future one), then restart the container.

## Step 5: Updating the metadata of existing photos

> **Warning:** This step is only needed the first time you use geodata from the project. It does not need to be repeated for new photos.

1. Log into the Immich web interface as an administrator.
2. Go to **Administration** → **Jobs**.
3. Find the **"Extract metadata"** job and click **"All"**.
4. Wait for the job to finish. Depending on the library size, this can take a while.

After it finishes, all geotagged photos will show their locations in Russian, and searching by Russian names will start to work.

## Updating the data

The `immich-geodata-ru` repository is updated weekly. To get fresh data:

1. Download the new archives from the release page.
2. Replace the contents of the `geodata` and `i18n-iso-countries/langs` folders with the new files.
3. Restart Immich (`docker compose down && docker compose up -d`).

The repository also has an `update.sh` script for automatic updates, which can be run on a schedule through the built-in TrueNAS task scheduler.

## Possible issues

| Problem | Solution |
|---|---|
| No geodata import message in the logs | Change the date in `geodata-date.txt` to the current one and restart the container |
| Russian names not displayed after updating metadata | Make sure the volumes are mounted correctly (check `docker inspect immich-server` and the paths inside the container) |
| The container does not start after adding volumes | Check the folder permissions on the host — they must be readable by the user that Immich runs as |
| Names partially in English | Choose a `geodata` file with higher accuracy (for example, `geodata_admin_2_admin_3_admin_4.zip`) |

## Additional resources

- [The immich-geodata-ru repository](https://github.com/Brooklyn2001/immich-geodata-ru)
- [Official Immich documentation on reverse geocoding](https://docs.immich.app/features/reverse-geocoding/)
