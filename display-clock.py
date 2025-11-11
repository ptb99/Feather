##
## CircuitPython code for a basic clock on TFT display
##

import time
import board
import adafruit_logging as logging
import traceback

import wifi
import socketpool
import adafruit_ntp
import adafruit_connection_manager
import adafruit_requests

#import terminalio
#from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label


## config knobs;
DEBUG = False
#DEBUG = True

TZ_OFFSET = 0 ## use AF service to get offset
#TZ_OFFSET = -7 # for PDT
#TZ_OFFSET = -8 # for PST

LARGE_FONT =  "fonts/DejaVuSans-Bold-36.pcf"
FG_COLOR = 0x0000FF


## UI buttons
BUTTON_UP = board.D0
BUTTON_DOWN = board.D2


def get_time_string(ts):
    return f'{ts.tm_hour:02d}:{ts.tm_min:02d}:{ts.tm_sec:02d}'


## Network setup and ntp object
def get_ntp_handle(*, dhcpname=None, tz_offset=0):
    logger = logging.getLogger('main')

    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        logger.error("WiFi secrets are kept in secrets.py, please add them there!")
        raise

    mac = ':'.join(f'{i:02x}' for i in wifi.radio.mac_address)
    logger.info(f"My MAC addr: {mac}")

    if dhcpname:
        wifi.radio.hostname = dhcpname
    wifi.radio.connect(secrets["ssid"], secrets["password"])

    logger.info("Connected to %s!"%secrets["ssid"])
    logger.info(f"My IP address is {wifi.radio.ipv4_address}")

    # create socket pool
    pool = socketpool.SocketPool(wifi.radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)

    # get DST-adjusted offset from Adafruit service
    if tz_offset == 0:
        requests = adafruit_requests.Session(pool, ssl_context)
        url = f'https://io.adafruit.com/api/v2/{secrets["aio_username"]}/' + \
            f'integrations/time/strftime?x-aio-key={secrets["aio_key"]}&fmt=%25z'
        with requests.get(url) as response:
            logger.info(f"strftime call returned: {response.status_code}")
            # check status_code == 200??
            val = int(response.text)/100
            logger.info(f"tz_offset: {response.text} ->  {val}")
            tz_offset = int(val)

    # NTP handle
    ntp = adafruit_ntp.NTP(pool, tz_offset=tz_offset, cache_seconds=600)
          # default server = "0.adafruit.pool.ntp.org"
          # cache_seconds = poll NTP no more often than (what is optimal?)
    return ntp


class MyDisplay:
    def __init__(self, disp, font, fgcolor):
        self.display = disp
        time_text = '00:00:00'

        self.font = bitmap_font.load_font(font)

        # Create the text label
        self.text_area = Label(self.font, text=time_text, color=fgcolor)

        # Set the location
        self.text_area.x = 40
        self.text_area.y = 70

        # display.show() is now replaced by setting .root_group
        self.display.root_group = self.text_area

    def update_text(self, text):
        self.text_area.text = text
        self.display.refresh()


## main program
def main():
    ntp_hndl = get_ntp_handle(dhcpname='esp32clock')
    disp = MyDisplay(board.DISPLAY, LARGE_FONT, FG_COLOR)
    logger = logging.getLogger('main')

    while True:
        try:
            #now = time.localtime()
            now = ntp_hndl.datetime
            time_text = get_time_string(now)
            logger.debug(f'Time = {time_text}')
            disp.update_text(time_text)
            time.sleep(1)

        except OSError as e:
            # NTP error
            logger.error(f'OSError: {e}')
            # prob a timeout to NTP server, just try again

        except Exception as e:
            # This works to print a stack trace
            logger.error(f'Unexpected exception: {e}')
            traceback.print_exception(e)
            # re-raise the error and hang the program
            raise


## actual exec here:
if __name__ == '__main__':
    logger = logging.getLogger('main')
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    main()
