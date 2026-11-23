# Study setup: accounts and keys

The study pipeline (`study/`) needs three accounts. Keys live in your home folder or in
environment variables, **never in this repository** (`.gitignore` blocks the usual file names).

The data servers are reached from your laptop: the cloud container used to write this code
cannot reach EWDS, ECMWF, ASF or SentiWiki.

## 1. EWDS token (GloFAS reanalysis, forecasts, thresholds)

1. Sign in at https://ewds.climate.copernicus.eu with your ECMWF account.
2. Open your profile page and copy the **API token**.
3. Accept the licence on each dataset page: *GloFAS historical*, *GloFAS forecast*
   (scroll to "Terms of use" and press Accept).
4. Create the file `C:\Users\<you>\.cdsapirc` with two lines:

   ```
   url: https://ewds.climate.copernicus.eu/api
   key: <your token>
   ```

## 2. ECMWF Web API key (TIGGE cloud forecasts)

1. Signed in to ECMWF, open https://api.ecmwf.int/v1/key/ and copy the JSON it shows.
2. Save it as `C:\Users\<you>\.ecmwfapirc`.
3. Accept the TIGGE licence once: open the TIGGE dataset page on apps.ecmwf.int and accept the terms.

## 3. Earth Engine key file

The usual browser login (`earthengine authenticate`) can be blocked by Google with "This app is
blocked". A key file avoids that login entirely and needs only clicks in the browser.

1. Open https://console.cloud.google.com and pick your Earth Engine project at the top of the page.
2. Menu (three lines, top left) > **IAM & Admin** > **Service accounts** > **+ Create service
   account**. Name: `blind-window`. Press **Create and continue**.
3. Under "Grant this service account access", add two roles: **Earth Engine Resource Viewer**
   and **Service Usage Consumer**. Press **Continue**, then **Done**.
4. Click the new account in the list > **Keys** tab > **Add key** > **Create new key** > **JSON** >
   **Create**. A file downloads.
5. Rename it to `ee-key.json` and move it to `C:\Users\<you>\` (the same folder as the other
   two files). Do not share it or upload it anywhere: it works like a password.

The pipeline finds the key file and the project id inside it by itself.

## Check

```
pip install -r requirements-study.txt
python -m study.creds
```

Every line should start with `OK`. The check prints no keys.
