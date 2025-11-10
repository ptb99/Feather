##
## CircuitPython code for ESP32-S2 Feather w/ temp/humidity sensor
##


import time
import json
import adafruit_logging as logging
import traceback

import wifi
import ssl
import socketpool

from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label
#from adafruit_display_shapes.rect import Rect

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from adafruit_io.adafruit_io_errors import  AdafruitIO_MQTTError

import board
import displayio
import fourwire
import adafruit_ssd1680


# drawing parameters
DISPLAY_WIDTH  = 250
DISPLAY_HEIGHT = 122
DISPLAY_OFFSET = 8

# Ours is a 3-color display
# BLACK, WHITE, RED (note red on this display is not vivid)
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Change text colors, choose from the following values:
FG_COLOR = BLACK
BG_COLOR = WHITE

REFRESH_INTVL = 300
#LOCAL_TZ_HOURS = -8             # PST
LOCAL_TZ_HOURS = -7             # PDT

# enable extra logging:
DEBUG = False
# caching code seems to have unknown problems (ESP32-S3 CP beta bugs?)
CACHE_GROUPS = False


def create_display():
    # release any previously configured displays
    displayio.release_displays()

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
    display_bus = fourwire.FourWire(
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

    ## FIXME: should find a way to set DHCP name...
    wifi.radio.hostname = 'temp-display'
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
        keep_alive=120
    )

    # Initialize an Adafruit IO MQTT Client
    io = IO_MQTT(mqtt_client)
    return io


current_vals = {}

# pylint: disable=unused-argument
def recv_vals(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    logger = logging.getLogger('recv_vals')
    #logger.info(f'MQTT msg: {feed_id} = {payload}')

    if feed_id == 'seconds':
        # for the time updates, can just insert the (integer) value
        secs = int(payload)
        current_vals[feed_id] = secs
        if secs % 60 == 0:
            # print times only 1/min
            logger.info(f'MQTT time: {feed_id} = {secs}')

    elif feed_id == 'Porch':
        data = json.loads(payload)
        for key,val in data['feeds'].items():
            logger.info(f'MQTT update: {key} = {val}')
            current_vals[key] = float(val)

    else:
        logger.warning(f'MQTT unknown: {feed_id} = {payload}')


class MyGraphics:
    # parameters
    SMALL_FONT =  "fonts/DejaVuSans-Bold-16.pcf"
    MEDIUM_FONT = "fonts/DejaVuSans-20.pcf"
    LARGE_FONT =  "fonts/DejaVuSans-Bold-24.pcf"

    def __init__(self, *, am_pm=True, celsius=False, tz_offset=0):
        self.logger = logging.getLogger('MyGraphics')
        self.am_pm = am_pm
        self.celsius = celsius
        self.tz_offset_seconds = tz_offset

        self.large_font = bitmap_font.load_font(self.LARGE_FONT)
        self.medium_font = bitmap_font.load_font(self.MEDIUM_FONT)
        self.small_font = bitmap_font.load_font(self.SMALL_FONT)
        self._time_str = ''
        self._temp_str = ''
        self._humid_str = ''
        self._barom_str = ''
        self._batt_str = ''

        # use this to cache the group of labels:
        self.display_group = None

    def update_values(self, val_map):
        self.logger.info('Update: current_vals =')
        for k,v in val_map.items():
            self.logger.info(f'    {k} = {v}')

        mytime = val_map['seconds']
        self.update_time(now=mytime, tz_offset=self.tz_offset_seconds)

        temp = val_map.get('alt-temp', 100)
        self.update_temp(temp)

        humid = val_map.get('alt-humidity', 10)
        self._humid_str = f'{humid:.1f}% RH'

        barom = val_map.get('pressure', 30)
        self._barom_str = f'{barom:.1f} in-Hg'

        batt = val_map.get('battery-charge', 0)
        self._batt_str = f'Batt: {batt:.1f}%'

    def update_time(self, now=None, tz_offset=0):
        # allow for current time to be passed in, otherwise use now()
        if not now:
            ## CircuitPython doesn't have a time.now() method
            #now = time.now()
            now = time.time()
        # very hackish!  But no zoneinfo infrastructure in CircuitPython...
        ts = time.localtime(now + tz_offset)
        hour = ts.tm_hour
        am_pm = ''
        if self.am_pm:
            am_pm = 'AM'
            if hour >= 12:
                am_pm = 'PM'
                hour -= 12
            if hour == 0:
                hour = 12
        self._time_str = f'{hour:2d}:{ts.tm_min:02d}{am_pm}'
        #self._time_str = now.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")

    def update_temp(self, temperature):
        # temp value from MQTT is in F
        #print(temperature)
        #Alt:  deg = '\u00B0'
        if self.celsius:
            self._temp_str = "%.1f °C" % ((temperature - 32) * 5 / 9)
        else:
            self._temp_str = "%.1f °F" % temperature
        
    def get_display_group(self, display_width, display_height):
        if not CACHE_GROUPS or not self.display_group:
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

            self.time_text = Label(self.large_font, text=self._time_str, 
                                   color=FG_COLOR)
            font_height = self.time_text.height
            self.time_text.x = 5
            self.time_text.y = 5 + font_height + DISPLAY_OFFSET
            g.append(self.time_text)

            self.temp_text = Label(self.large_font, text=self._temp_str, 
                                   color=FG_COLOR)
            font_width = self.temp_text.width
            font_height = self.temp_text.height
            self.temp_text.x = self.disp_width - font_width - 10
            self.temp_text.y = 5 + font_height + DISPLAY_OFFSET
            g.append(self.temp_text)

            self.humid_text = Label(self.medium_font, text=self._humid_str,
                                    color=FG_COLOR)
            font_width = self.humid_text.width
            font_height = self.humid_text.height
            self.humid_text.x = self.disp_width - font_width - 10
            self.humid_text.y = (self.disp_height - 2*font_height + 
                                 DISPLAY_OFFSET - 10)
            g.append(self.humid_text)

            self.barom_text = Label(self.medium_font, text=self._barom_str,
                                    color=FG_COLOR)
            font_width = self.barom_text.width
            font_height = self.barom_text.height
            self.barom_text.x = self.disp_width - font_width - 10
            self.barom_text.y = self.disp_height - font_height + DISPLAY_OFFSET
            g.append(self.barom_text)
            
            self.batt_text = Label(self.small_font, text=self._batt_str,
                                   color=RED)
            font_width = self.batt_text.width
            font_height = self.batt_text.height
            #self.batt_text.x = self.disp_width - font_width - 10
            self.batt_text.x = 5
            self.batt_text.y = self.disp_height - 3*font_height + DISPLAY_OFFSET
            g.append(self.batt_text)

        else:
            # don't create a new group, just update the labels
            self.time_text.text = self._time_str
            self.temp_text.text = self._temp_str
            self.humid_text.text = self._humid_str
            self.barom_text.text = self._barom_str
            self.batt_text.text = self._batt_str
            ## FIXME: what about resetting the x pos of the right-col labels?
            
        # return the cached groups
        if DEBUG:
            self.logger.debug('time_text = (%d, %d)', 
                              self.time_text.x,self.time_text.y)
            self.logger.debug('temp_text = (%d, %d)', 
                              self.temp_text.x,self.temp_text.y)
            self.logger.debug('batt_text = (%d, %d)', 
                              self.batt_text.x,self.batt_text.y)
        return self.display_group

    
def main(vals_dict):
    display = create_display()
    state = MyGraphics(celsius=False, tz_offset=LOCAL_TZ_HOURS*3600)

    # Connect to Adafruit IO
    io = get_network_io_handle()

    # Connect the callback method defined above to Adafruit IO
    io.on_message = recv_vals
    io.connect()

    # use time subscription vs NTP or something else
    io.subscribe_to_time("seconds")
    #io.subscribe_to_time("iso")

    ## alt idea:
    #tm_struct = io.receive_time()

    # Subscribe to Group
    io.subscribe(group_key='Porch')

    last_time = 0
    #last_time = time.monotonic()
    while True:
        t = time.monotonic()
        # make sure to wait until we get one MQTT time update
        ready = ('seconds' in vals_dict)
        if  ( (last_time == 0 and ready) or 
              (last_time > 0 and (t - last_time) > REFRESH_INTVL) ):
            last_time = t
            state.update_values(vals_dict)
            group = state.get_display_group(DISPLAY_WIDTH, DISPLAY_HEIGHT)
            #display.show(group)  ## old syntax
            display.root_group = group ## new syntax (CP >= 9.0)
            display.refresh()
            while display.busy:
                time.sleep(1)

        # otherwise just loop receiving MQTT messages
        io.loop(timeout=5)
        #time.sleep(1)


## actual exec here:
if __name__ == '__main__':
    logger = logging.getLogger('main')
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # loop in order to retry main() after an exception
    while True:
        try:
            main(current_vals)

        except MQTT.MMQTTException as e:
            ## apparently, protocol exceptions happen fairly frequently
            logger.error('MQTT exception: %s', e)
            ## swallow this exception and try another round at main()
            pass

            #wifi.reset()
            #wifi.connect()
            #io.reconnect()

        except AdafruitIO_MQTTError as e:
            ## apparently, connection exceptions also happen fairly frequently
            logger.error('MQTT exception: %s', e)
            ## swallow this exception and try another round at main()
            pass

        except Exception as e:
            # This doesn't work in adafruit_logger
            #logger.error('Failed to connect', exc_info=sys.exc_info())
            #logger.error(e, exc_info=True)

            # Try this instead:
            logger.error('Failed to connect: %s', e)
            traceback.print_exception(e)

            # re-raise the error and hang the program
            raise

