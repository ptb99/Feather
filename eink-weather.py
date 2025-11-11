##
## CircuitPython adaptation of:
## https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/EInk_Bonnet_Weather_Station
##

import time
import json
import adafruit_logging as logging

from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label
from adafruit_display_shapes.rect import Rect

import wifi
import ssl
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import adafruit_requests as requests

import board
import displayio
import adafruit_ssd1680


# release any previously configured displays
displayio.release_displays()


dummy_response = '{"coord":{"lon":-121.895,"lat":37.3394},"weather":[{"id":800,"main":"Clear","description":"clear sky","icon":"01n"}],"base":"stations","main":{"temp":284.12,"feels_like":282.89,"temp_min":280.29,"temp_max":287.65,"pressure":1021,"humidity":62},"visibility":10000,"wind":{"speed":0.89,"deg":38,"gust":1.34},"clouds":{"all":0},"dt":1669188468,"sys":{"type":1,"id":5845,"country":"US","sunrise":1669128869,"sunset":1669164804},"timezone":-28800,"id":5392171,"name":"San Jose","cod":200}'
dummy_data = json.loads(dummy_response)

# drawing parameters
DISPLAY_WIDTH  = 250
DISPLAY_HEIGHT = 122
DISPLAY_OFFSET = 8

#DRAW_BOXES = True
DRAW_BOXES = False

# Ours is a 3-color display
# BLACK, WHITE, RED (note red on this display is not vivid)
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Change text colors, choose from the following values:
FG_COLOR = BLACK
BG_COLOR = WHITE


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


class Weather_Graphics:
    # parameters:
    SMALL_FONT =  "fonts/DejaVuSans-Bold16.pcf"
    MEDIUM_FONT = "fonts/DejaVuSans20.pcf"
    LARGE_FONT =  "fonts/DejaVuSans-Bold24.pcf"
    #ICON_FONT =   "fonts/meteocons.ttf"
    ICON_FONT =   "fonts/Meteocons48.pcf"

    def __init__(self, *, am_pm=True, celsius=True):
        self.am_pm = am_pm
        self.celsius = celsius

        self.small_font = bitmap_font.load_font(self.SMALL_FONT)
        self.medium_font = bitmap_font.load_font(self.MEDIUM_FONT)
        self.large_font = bitmap_font.load_font(self.LARGE_FONT)
        self.icon_font = bitmap_font.load_font(self.ICON_FONT)

        # use this to cache the group of labels:
        self.display_group = None

        self._weather_icon = None
        self._city_name = None
        self._main_text = None
        self._temperature = None
        self._description = None
        self._time_text = None

    def update_weather(self, weather):
        """Pass in dict with parsed response from OWM and update graphics"""
        #weather = json.loads(data)

        # set the icon/background
        self._weather_icon = ICON_MAP[weather["weather"][0]["icon"]]

        city_name = weather["name"] + ", " + weather["sys"]["country"]
        #print(city_name)
        self._city_name = city_name

        main = weather["weather"][0]["main"]
        #print(main)
        self._main_text = main

        temperature = weather["main"]["temp"] - 273.15  # its...in kelvin
        #print(temperature)
        if self.celsius:
            self._temperature = "%d °C" % temperature
        else:
            self._temperature = "%d °F" % ((temperature * 9 / 5) + 32)

        description = weather["weather"][0]["description"]
        description = description[0].upper() + description[1:]
        #print(description)
        self._description = description
        # "thunderstorm with heavy drizzle"

    def update_time(self, now=None, tz=0):
        # allow for current time to be passed in, otherwise use now()
        if not now:
            ## CircuitPython doesn't have a time.now() method
            #now = time.now()
            now = time.time()
        # very hackish!  But no zoneinfo infrastructure in CircuitPython...
        ts = time.localtime(now + tz)
        hour = ts.tm_hour
        am_pm = ''
        if self.am_pm:
            am_pm = 'AM'
            if hour >= 12:
                am_pm = 'PM'
                hour -= 12
            elif hour == 0:
                hour = 12
        self._time_text = f'{hour:2d}:{ts.tm_min:02d}{am_pm}'
        #self._time_text = now.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")

    def get_display_group(self, display_width, display_height):
        if not self.display_group:
            # First time through, create a group for all the labels
            g = displayio.Group()

            self.display_group = g
            self.disp_width = display_width
            self.disp_height = display_height


            # add extra height to work around "noise pixels" at bottom of display
            background_bitmap = displayio.Bitmap(self.disp_width, 
                                                 self.disp_height+10, 1)
            palette = displayio.Palette(1)
            palette[0] = BG_COLOR

            # Put the background into the display group
            bg_tile = displayio.TileGrid(background_bitmap, pixel_shader=palette,
                                         x=0, y=0)
            g.append(bg_tile)

            # box at limits of display
            if DRAW_BOXES:
                g.append(Rect(0, 0+DISPLAY_OFFSET, 
                              self.disp_width, self.disp_height,
                              outline=BLACK, stroke=3))

            # Draw the Icon
            self.icon_text = Label(self.icon_font, text=self._weather_icon, 
                                   color=FG_COLOR)
            (x, y, w, h) = self.icon_text.bounding_box
            #font_width = self.icon_text.width
            #font_height = self.icon_text.height
            #icon_text.x = self.disp_width // 2 - font_width // 2
            #icon_text.y = self.disp_height // 2 #- font_height // 2 - 5
            self.icon_text.x = self.disp_width - w - 10
            self.icon_text.y = 25
            ## alternately, could use icon_text.anchor_point = (0.5, 0.5)
            # print('icon BB = ', self.icon_text.bounding_box)
            # print('icon w,h = ', self.icon_text.width, self.icon_text.height)
            if DRAW_BOXES:
                g.append(Rect(self.icon_text.x+x, self.icon_text.y+y, w-x, h-y, 
                              outline=BLACK, stroke=1))
            g.append(self.icon_text)

            # Draw the city
            self.city_text = Label(self.medium_font, text=self._city_name, 
                                   color=FG_COLOR)
            self.city_text.x = 5
            self.city_text.y = 25
            if DRAW_BOXES:
                (x, y, w, h) = self.city_text.bounding_box
                g.append(Rect(self.city_text.x+x, self.city_text.y+y, w, h, 
                              outline=BLACK, stroke=1))
            g.append(self.city_text)

            # Draw the time
            # (Maybe put time upper right and weather_icon in middle?)
            self.time_text = Label(self.medium_font, text=self._time_text, 
                                   color=FG_COLOR)
            self.time_text.x = 5
            self.time_text.y = self.time_text.height * 2 + 5
            if DRAW_BOXES:
                (x, y, w, h) = self.time_text.bounding_box
                g.append(Rect(self.time_text.x+x, self.time_text.y+y, w, h, 
                              outline=BLACK, stroke=1))
            g.append(self.time_text)

            # Draw the main text
            self.main_text = Label(self.large_font, text=self._main_text, 
                                   color=FG_COLOR)
            self.main_text.x = 5
            self.main_text.y = self.disp_height - self.main_text.height * 2 + 10
            # print('main BB = ', self.main_text.bounding_box)
            # print('main w,h = ', self.main_text.width, self.main_text.height)
            if DRAW_BOXES:
                (x, y, w, h) = self.main_text.bounding_box
                g.append(Rect(self.main_text.x+x, self.main_text.y+y, w, h, 
                              outline=BLACK, stroke=1))
            g.append(self.main_text)

            # Draw the description
            self.desc_text = Label(self.small_font, text=self._description, 
                                   color=FG_COLOR)
            self.desc_text.x = 5
            self.desc_text.y = self.disp_height - self.desc_text.height + 5
            if DRAW_BOXES:
                (x, y, w, h) = self.desc_text.bounding_box
                g.append(Rect(self.desc_text.x+x, self.desc_text.y+y, w, h, 
                              outline=BLACK, stroke=1))
            g.append(self.desc_text)

            # Draw the temperature
            self.temp_text = Label(self.large_font, text=self._temperature, 
                                   color=FG_COLOR)
            font_width = self.temp_text.width
            font_height = self.temp_text.height
            self.temp_text.x = self.disp_width - font_width - 10
            self.temp_text.y = self.disp_height - font_height * 2 + 15
            if DRAW_BOXES:
                (x, y, w, h) = self.temp_text.bounding_box
                g.append(Rect(self.temp_text.x+x, self.temp_text.y+y, w, h, 
                              outline=BLACK, stroke=1))
            g.append(self.temp_text)

        else:
            # don't create a new group, just update the labels
            self.icon_text.text = self._weather_icon
            self.city_text.text = self._city_name
            self.time_text.text = self._time_text
            self.main_text.text = self._main_text
            self.desc_text.text = self._description
            self.temp_text.text = self._temperature

        # return the cached groups
        return self.display_group

## Notes on text label placement:
# icon BB =  (12, -23, 36, 24) = (x, y, w, h) 
# icon w,h =  24 47
# w = BB[2] - BB[0], h = BB[3] - BB[1]
# BB is relative to x,y origin, bounds the inked space


def create_display():

    # create the spi device and pins we will need
    spi = board.SPI()  # Uses SCK and MOSI

    epd_cs = board.D9
    epd_dc = board.D10
    # set to None for Featherwing display
    #epd_rst = board.D5
    #epd_busy = board.D6
    epd_rst = None
    epd_busy = None
    #epd_srcs = None

    #print("Creating display")
    display_bus = displayio.FourWire(
        spi, command=epd_dc, chip_select=epd_cs, reset=epd_rst, baudrate=1000000
    )
    time.sleep(1)

    display = adafruit_ssd1680.SSD1680(
        display_bus,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        busy_pin=epd_busy,
        highlight_color=RED,
        rotation=270,
    )
    return display

    ## Note: display.time_to_refresh (min refresh frequency) is not set
    #print('display refresh= ', display.time_to_refresh)


def get_network_io_handle():
    """Configure wifi network and Adafruit_IO handle"""
    logger = logging.getLogger('wifi')

    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        #print("WiFi connect failed: no secrets.py file")
        logger.error("WiFi connect failed: no secrets.py file")
        # maybe flash neopixel with some pattern?
        raise

    mac = ':'.join(f'{i:02x}' for i in wifi.radio.mac_address)
    logger.info(f"My MAC addr: {mac}")

    wifi.radio.connect(secrets["ssid"], secrets["password"])

    logger.info("Connected to %s!"%secrets["ssid"])
    logger.info(f"My IP address is {wifi.radio.ipv4_address}")

    # Create a socket pool
    pool = socketpool.SocketPool(wifi.radio)

    # Initialize a new MQTT Client object
    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        port=1883,
        username=secrets["aio_username"],
        password=secrets["aio_key"],
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
    )

    # Initialize an Adafruit IO MQTT Client
    io = IO_MQTT(mqtt_client)
    return io


def get_weather_info():
    logger = logging.getLogger('weather')

    # Use cityname, country code where countrycode is ISO3166 format.
    # E.g. "New York, US" or "London, GB"
    LOCATION = "San Jose, US"
    DATA_SOURCE_URL = "http://api.openweathermap.org/data/2.5/weather"

    # You'll need to get a token from openweathermap.org, put it here:
    OPEN_WEATHER_TOKEN = ''
    try:
        from secrets import secrets
        OPEN_WEATHER_TOKEN = secrets['open_weather_token']
    except ImportError:
        logger.error("Weather token failed: no secrets.py file")
        raise

    if len(OPEN_WEATHER_TOKEN) == 0:
        raise RuntimeError(
            "You need to set your token first. If you don't already have one, you can register for a free account at https://home.openweathermap.org/users/sign_up"
        )

    # Set up where we'll be fetching data from
    #params = {"q": LOCATION, "appid": OPEN_WEATHER_TOKEN}
    #DATA_SOURCE = DATA_SOURCE_URL + "?" + urllib.urlencode(params)
    quoted_location = LOCATION.replace(' ', '+')
    DATA_SOURCE = ( DATA_SOURCE_URL + "?" + "q=" + quoted_location +
                    "&appid=" + OPEN_WEATHER_TOKEN )

    # Create a socket pool
    pool = socketpool.SocketPool(wifi.radio)

    server = requests.Session(pool, ssl.create_default_context())
    response = server.get(DATA_SOURCE).json()

    return response


def main(owm_data):
    display = create_display()
    weather = Weather_Graphics(celsius=False, am_pm=True)
    REFRESH_INTVL = 300

    dt = owm_data['dt']
    tz = owm_data['timezone']
    #print('main called at dt= ', dt)

    while True:
        weather.update_weather(owm_data)
        weather.update_time(dt, tz)
        display.show(weather.get_display_group(DISPLAY_WIDTH, DISPLAY_HEIGHT))
        display.refresh()
        while display.busy:
            time.sleep(1)
        time.sleep(REFRESH_INTVL)
        print('refresh-limit timer reached (looping)')


## actual exec here:
if __name__ == '__main__':
    io = get_network_io_handle()
    weather = get_weather_info()
    #print(weather)
    #weather = dummy_data
    main(weather)
