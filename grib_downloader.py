"""
GRIB downloader.

Usage:
  grib_download latest [--city=<name>|--coordinates=<lat,lon>] --apikey=<key>
  grib_download web_location --apikey=<key>

Options:
  -h --help               Show this screen.
  --version               Show version.
  --city=<name>           Download forecasts around a city.
  --coordinates=<lat,lon> Download forecasts around given coordinates.
  --apikey=<key>          Key from FMI (something like cd598b0e-182e-4e6f-8dad-c55df7a42ce3)
"""

import xmltodict
import requests
import datetime
import os
import codecs
import sys
import csv
import threading
import webbrowser
from flask import Flask, request
from docopt import docopt
import progressbar
import progressbar.widgets


PORT = 5991

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

def search_city(keyword):
    keyword_lower = keyword.lower()
    matches = []
    with codecs.open("cities.csv", encoding="utf8") as cities:
        csvreader = unicode_csv_reader(cities, delimiter=";")
        for row in csvreader:
            if row[1].lower().startswith(keyword_lower):
                matches.append((row[0], row[1], float(row[3]), float(row[4])))
    return matches


class FmiGribLoader(object):
    ALL_PARAMS = set(["Pressure", "GeopHeight", "Temperature", "DewPoint", "Humidity", "WindUMS", "WindVMS", "PrecipitationAmount", "TotalCloudCover", "LowCloudCover", "MediumCloudCover", "HighCloudCover", "Precipitation1h", "MaximumWind", "WindGust", "RadiationGlobalAccumulation", "RadiationLWAccumulation", "RadiationNetSurfaceLWAccumulation", "RadiationNetSurfaceSWAccumulation", "VelocityPotential", "PseudoAdiabaticPotentialTemperature"])

    def __init__(self, apikey):
        self.apikey = apikey

    def get_latest_time(self):
        response = requests.get("http://data.fmi.fi/fmi-apikey/%s/wfs?request=GetFeature&storedquery_id=fmi::forecast::hirlam::surface::finland::grid" % self.apikey)
        data = response.text
        if response.status_code != 200:
            print("Unable to download forecast times. Invalid API key?")
            return None
        parsed_data = xmltodict.parse(data)
        latest = "0"
        for item in parsed_data["wfs:FeatureCollection"]["wfs:member"]:
          timestamp = item["omso:GridSeriesObservation"]["om:parameter"]["om:NamedValue"]["om:value"]["gml:TimeInstant"]["gml:timePosition"]
          if timestamp > latest:
            latest = timestamp
        if latest != "0":
            return latest

    def download_grib(self, out_file, origin_time, start_time, end_time, left_latitude, left_longitude, right_latitude, right_longitude, params = None):
        if not params:
            params = ["WindUMS", "WindVMS", "Pressure", "Temperature", "TotalCloudCover"]
        if not set(params).issubset(self.ALL_PARAMS):
            print("Invalid parameters set. Allowed parameters: %s." % ", ".join(sorted(self.ALL_PARAMS)))
            return
        formatted_params = ",".join(params)
        response = requests.get("http://data.fmi.fi/fmi-apikey/%s/download?producer=hirlam&param=%s&bbox=%s,%s,%s,%s&origintime=%s&starttime=%s&endtime=%s&format=grib2&projection=epsg:4326" % (self.apikey, formatted_params, left_longitude, left_latitude, right_longitude, right_latitude, origin_time, start_time, end_time), stream=True)
        total_size = 0
        bar = progressbar.ProgressBar(max_value=3500000, widgets=[
                progressbar.widgets.Percentage(),
                ' of ', progressbar.widgets.DataSize('max_value'),
                ' ', progressbar.widgets.Bar(),
                ' ', progressbar.widgets.Timer(),
                ' ', progressbar.FileTransferSpeed()
        ])
        bar.start()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                total_size += len(chunk)
                out_file.write(chunk)
                try:
                    bar.update(total_size)
                except ValueError:
                    bar.max_value = total_size + 1
                    bar.update(total_size)
        bar.finish()

    def overwrite_grib_file(self, filename):
        if not os.path.exists(filename):
            return True
        if os.stat(filename).st_size == 0:
            print("Datafile %s exists, but it is empty. Downloading a new version." % filename)
            return True
        with open(filename, "rb") as f:
            if f.read(4) != "GRIB":
                print("%s is not a grib file. Downloading a new version." % filename)
                return True
            f.seek(-4, os.SEEK_END)
            if f.read(4) != "7777":
                print("%s is not a complete grib file. Downloading a new version." % filename)
                return True
        print("Datafile %s exists and seems to be valid grib2. Skipping download." % filename)
        return False

    def download_latest(self, coordinates):
        origin_time = self.get_latest_time()
        if not origin_time:
            print("No forecast origin time available.")
            return
        start_time = origin_time
        end_time = (datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        left_latitude = coordinates[0] - 1.5
        right_latitude = coordinates[0] + 1.5
        left_longitude = coordinates[1] - 3
        right_longitude = coordinates[1] + 3
        filename = "fmi-hirlam-%s-%s,%s.grb2" % (origin_time, coordinates[0], coordinates[1])
        if not self.overwrite_grib_file(filename):
            return
        print("Downloading grib with origin time %s and coordinates %s" % (origin_time, coordinates))
        self.download_grib(open(filename, "w"), origin_time, start_time, end_time, left_latitude, left_longitude, right_latitude, right_longitude)


app = Flask(__name__)
@app.route("/")
def frontpage():
    return open("location.html").read()

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route("/download")
def download_coordinates():
    latitude = float(request.args.get("latitude"))
    longitude = float(request.args.get("longitude"))
    app.fmi.download_latest((latitude, longitude))
    shutdown_server()
    return "ok"


if __name__ == '__main__':
    arguments = docopt(__doc__, version='GRIB downloader 0.1')
    a = FmiGribLoader(arguments["--apikey"])
    if arguments["latest"]:
        if arguments["--city"]:
            keyword = arguments["--city"].decode("utf-8")
            matches = search_city(keyword)
            if len(matches) > 1:
                for i, match in enumerate(matches):
                    print("%s: %s - %s: %s,%s" % (i, match[0], match[1], match[2], match[3]))
                selection = raw_input("Select one: ")
                try:
                    selection = int(selection)
                except ValueError:
                    print("Not a number.")
                    sys.exit(1)
                if selection >= 0 and selection < len(matches):
                    city = matches[selection]
                else:
                    print("Invalid selection")
                    sys.exit(1)
            elif len(matches) == 1:
                city = matches[0]
            else:
                print(u"No matching cities for keyword %s" % keyword)
                sys.exit(1)
            a.download_latest((city[2], city[3]))
        elif arguments["--coordinates"]:
            coordinates = map(float, arguments["--coordinates"].split(","))
            a.download_latest(coordinates)
    elif arguments["web_location"]:
        threading.Timer(1, lambda: webbrowser.open("http://localhost:%s/" % PORT)).start()
        app.fmi = a
        app.run(port=PORT)
