#! /usr/bin/python3

##
## run OpenWeather stuff on devel host (not CircuitPython)
##

#import time
import datetime
import urllib.request
import urllib.parse
import json


# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = "San Jose, US"
#LOCATION = "Santa Fe, US"
DATA_SOURCE_URL = "http://api.openweathermap.org/data/2.5/weather"
# lat/long of home
#37.302371680390905, -121.97163794306131

# You'll need to get a token from openweathermap.org, put it here:
OPEN_WEATHER_TOKEN = "10622dd1ce944ff03dac594f29908373"

if len(OPEN_WEATHER_TOKEN) == 0:
    raise RuntimeError(
        "You need to set your token first. If you don't already have one, you can register for a free account at https://home.openweathermap.org/users/sign_up"
    )


# Set up where we'll be fetching data from
params = {"q": LOCATION, "appid": OPEN_WEATHER_TOKEN}
data_source = DATA_SOURCE_URL + "?" + urllib.parse.urlencode(params)


# Map the OpenWeatherMap icon code to the appropriate font character
# See http://www.alessioatzeni.com/meteocons/ for icons
ICON_MAP = {
    "01d": "B",
    "01n": "C",
    "02d": "H",
    "02n": "I",
    "03d": "N",
    "03n": "N",
    "04d": "Y",
    "04n": "Y",
    "09d": "Q",
    "09n": "Q",
    "10d": "R",
    "10n": "R",
    "11d": "Z",
    "11n": "Z",
    "13d": "W",
    "13n": "W",
    "50d": "J",
    "50n": "K",
}

def convert_icon(input):
    return ICON_MAP[input]


# Sample response should look like:
## {
##     "coord": {
##         "lon": -121.895,
##         "lat": 37.3394
##     },
##     "weather": [
##         {
##             "id": 800,
##             "main": "Clear",
##             "description": "clear sky",
##             "icon": "01n"
##         }
##     ],
##     "base": "stations",
##     "main": {
##         "temp": 284.12,
##         "feels_like": 282.89,
##         "temp_min": 280.29,
##         "temp_max": 287.65,
##         "pressure": 1021,
##         "humidity": 62
##     },
##     "visibility": 10000,
##     "wind": {
##         "speed": 0.89,
##         "deg": 38,
##         "gust": 1.34
##     },
##     "clouds": {
##         "all": 0
##     },
##     "dt": 1669188468,
##     "sys": {
##         "type": 1,
##         "id": 5845,
##         "country": "US",
##         "sunrise": 1669128869,
##         "sunset": 1669164804
##     },
##     "timezone": -28800,
##     "id": 5392171,
##     "name": "San Jose",
##     "cod": 200
## }


def main():
    response = urllib.request.urlopen(data_source)
    if response.getcode() == 200:
        value = response.read()
        #print("Response is", value)
        weather = json.loads(value.decode('utf-8'))
        now = datetime.datetime.now()
        print(now.strftime("%I:%M %p").lstrip("0").replace(" 0", " "))
        icon = weather["weather"][0]["icon"]
        print("icon= '{0:s}' -> '{1:s}'".format(icon, convert_icon(icon)))
        print("city= ", weather["name"] + ", " + weather["sys"]["country"])
        print("main= ", weather["weather"][0]["main"])
        temp_C = weather["main"]["temp"] - 273.15
        temp_F = temp_C *9/5 + 32
        print("temp= {0:.2f} C / {1:.1f} F".format(temp_C, temp_F)) #in deg K
        print("humid= ", weather["main"]["humidity"], '%')
        print("barom= {:.2f}".format(weather["main"]["pressure"] / 33.8638864))
        print("desc= ", weather["weather"][0]["description"])
        
    else:
        print("Unable to retrieve data at {}".format(data_source))


if __name__ == '__main__':
    main()
