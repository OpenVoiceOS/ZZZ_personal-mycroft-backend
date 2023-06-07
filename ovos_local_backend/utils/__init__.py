# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import random

import flask
from ovos_utils.log import LOG

from ovos_local_backend.configuration import CONFIGURATION
from ovos_local_backend.session import SESSION as requests
from ovos_local_backend.utils.geolocate import get_timezone, Geocoder


def generate_code():
    k = ""
    while len(k) < 6:
        k += random.choice(["A", "B", "C", "D", "E", "F", "G", "H", "I",
                            "J", "K", "L", "M", "N", "O", "P", "Q", "R",
                            "S", "T", "U", "Y", "V", "X", "W", "Z", "0",
                            "1", "2", "3", "4", "5", "6", "7", "8", "9"])
    return k.upper()


def nice_json(arg):
    response = flask.make_response(json.dumps(arg, sort_keys=True, indent=4))
    response.headers['Content-type'] = "application/json"
    return response


def to_camel_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + ''.join(x.title() for x in components[1:])


def dict_to_camel_case(data):
    converted = {}
    for k, v in data.items():
        new_k = to_camel_case(k)
        if isinstance(v, dict):
            v = dict_to_camel_case(v)
        if isinstance(v, list):
            for idx, item in enumerate(v):
                if isinstance(item, dict):
                    v[idx] = dict_to_camel_case(item)
        converted[new_k] = v
    return converted


class ExternalApiManager:
    def __init__(self):
        self.config = CONFIGURATION.get("microservices", {})
        self.units = CONFIGURATION["system_unit"]

        self.wolfram_key = self.config.get("wolfram_key")
        self.owm_key = self.config.get("owm_key")
        self.geo = Geocoder()

    @property
    def _owm(self):
        return LocalWeather(self.owm_key)

    @property
    def _wolfram(self):
        return LocalWolfram(self.wolfram_key)

    def geolocate(self, address):
        return {"data": self.geo.get_location(address)}

    def wolfram_spoken(self, query, units=None, lat_lon=None):
        units = units or self.units
        if units != "metric":
            units = "imperial"
        if isinstance(self._wolfram, LocalWolfram):  # local
            # TODO - lat lon, not used? selene accepts it but....
            # https://products.wolframalpha.com/spoken-results-api/documentation/
            return self._wolfram.spoken(query, units)
        if hasattr(self._wolfram, "get_wolfram_spoken"):  # ovos api
            q = {"input": query, "units": units}
            return self._wolfram.get_wolfram_spoken(q)

    def wolfram_simple(self, query, units=None, lat_lon=None):
        units = units or self.units
        if units != "metric":
            units = "imperial"
        return self._wolfram.simple(query, units)

    def wolfram_full(self, query, units=None, lat_lon=None):
        units = units or self.units
        if units != "metric":
            units = "imperial"
        return self._wolfram.full(query, units)

    def wolfram_xml(self, query, units=None, lat_lon=None):
        units = units or self.units
        if units != "metric":
            units = "imperial"
        return self._wolfram.full(query, units, output="xml")

    def owm_current(self, lat, lon, units, lang="en-us"):
        return self._owm.current(lat, lon, units, lang)

    def owm_onecall(self, lat, lon, units, lang="en-us"):
        return self._owm.onecall(lat, lon, units, lang)

    def owm_hourly(self, lat, lon, units, lang="en-us"):
        return self._owm.hourly(lat, lon, units, lang)

    def owm_daily(self, lat, lon, units, lang="en-us"):
        return self._owm.daily(lat, lon, units, lang)


class LocalWeather:
    def __init__(self, key):
        self.key = key

    def current(self, lat, lon, units, lang):
        params = {
            "lang": lang,
            "units": units,
            "lat": lat, "lon": lon,
            "appid": self.key
        }
        url = "https://api.openweathermap.org/data/2.5/weather"
        return requests.get(url, params=params).json()

    def daily(self, lat, lon, units, lang):
        params = {
            "lang": lang,
            "units": units,
            "lat": lat, "lon": lon,
            "appid": self.key
        }
        url = "https://api.openweathermap.org/data/2.5/forecast/daily"
        return requests.get(url, params=params).json()

    def hourly(self, lat, lon, units, lang):
        params = {
            "lang": lang,
            "units": units,
            "lat": lat, "lon": lon,
            "appid": self.key
        }
        url = "https://api.openweathermap.org/data/2.5/forecast"
        return requests.get(url, params=params).json()

    def onecall(self, lat, lon, units, lang):
        params = {
            "lang": lang,
            "units": units,
            "lat": lat, "lon": lon,
            "appid": self.key
        }
        url = "https://api.openweathermap.org/data/2.5/onecall"
        return requests.get(url, params=params).json()


class LocalWolfram:
    def __init__(self, key):
        self.key = key

    def spoken(self, query, units):
        url = 'https://api.wolframalpha.com/v1/spoken'
        params = {"appid": self.key,
                  "i": query,
                  "units": units}
        answer = requests.get(url, params=params).text
        return answer

    def simple(self, query, units):
        url = 'https://api.wolframalpha.com/v1/simple'
        params = {"appid": self.key,
                  "i": query,
                  "units": units}
        answer = requests.get(url, params=params).text
        return answer

    def full(self, query, units, output="json"):
        url = 'https://api.wolframalpha.com/v2/query'
        params = {"appid": self.key,
                  "input": query,
                  "output": output,
                  "units": units}
        answer = requests.get(url, params=params).json()
        return answer
