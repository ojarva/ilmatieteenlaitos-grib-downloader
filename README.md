Ilmatieteenlaitos grib downloader
=================================

Finnish Meteorological Institute (FMI) offers local weather forecast models (hirlam) through their open data access. FMI's forecast is typically remarkably more accurate than GFS or ECMWF, especially close to shore and between islands. Forecasts are only available around Finland.

This is a simple script to download latest GRIB files easily. By default GRIB files only include fields used by [OpenCPN](https://opencpn.org/) weather plugin.

Installation
------------

* Install [pip](https://pypi.python.org/pypi/pip)
* Install dependencies: `pip install -r requirements.txt`

Registering API key
-------------------

1. Go to [registration page](https://ilmatieteenlaitos.fi/rekisteroityminen-avoimen-datan-kayttajaksi) (in Finnish only) to register.
2. Go to your email, and confirm registration.
3. You'll get a new email confirming the registration. It'll include API key, which is something like `36ad9771-b2e9-42da-b338-25075f1a82b0` (not a valid key).
4. Copy this key, and use it as a value for `--apikey` parameter.

Usage
-----

See `grib_downloader.py -h` for usage.

Typical usage patterns would be

a) Downloading forecasts around your current location:

```
grib_downloader.py latest --coordinates=60.1699,24.9384 --apikey=your_fmi_api_key
```

b) Downloading forecasts around specific city:

```
grib_downloader.py latest --city=Helsinki --apikey=your_fmi_api_key
```

c) Downloading forecasts based on your geolocation (typically only works when near fixed wifi installations):

```
grib_downloader.py web_location --apikey=your_fmi_api_key
```

This will open a simple web page to your browser and the browser will ask for a permission to locate you. After obtaining the location, downloading forecasts will take anything between a few seconds and a few minutes. There's no progress feedback on the web browser.
