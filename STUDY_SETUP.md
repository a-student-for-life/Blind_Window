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

## 3. Earth Engine project

1. In the Earth Engine Code Editor or https://code.earthengine.google.com/register, register a
   Cloud project for **noncommercial / academic** use and note its **project id**.
2. On your laptop: `pip install earthengine-api` then `earthengine authenticate` (opens the browser).
3. Set the project id: `setx EE_PROJECT <project id>` (new terminals pick it up).

## Check

```
pip install -r requirements-study.txt
python -m study.creds
```

Every line should start with `OK`. The check prints no keys.
