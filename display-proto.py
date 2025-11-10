##
## CircuitPython code for ESP32-S3 Feather w/ eInk display
##


import time
import alarm
import board
#import digitalio
import adafruit_logging as logging

import wifi
import ssl
import socketpool

import adafruit_lc709203f
import adafruit_ssd1680

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


## some control params:
DEBUG = False
UPDATE_INTVL = 60
BATT_SIZE =  adafruit_lc709203f.PackSize.MAH400

logger = logging.getLogger('main')
logger.setLevel(logging.INFO)


class batt_sensor:
    def __init__(self, i2c, pack_size):
        """Set up LC709204f sensor on default I2C bus"""
        super().__init__()
        self.sensor = adafruit_lc709203f.LC709203F(i2c)
        self.sensor.pack_size = pack_size

        logger = logging.getLogger('battery')
        logger.info(f"Battery IC version: {self.sensor.ic_version:#x}")

    def get_voltage(self):
        return self.sensor.cell_voltage

    def get_level(self):
        return self.sensor.cell_percent


def get_network_io_handle():
    """Configure wifi network and Adafruit_IO handle"""

    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        print("WiFi connect failed: no secrets.py file")
        # maybe flash neopixel with some pattern?
        raise

    logger = logging.getLogger('wifi')
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


#logger.info("Connecting to Adafruit IO...")

try:
    logger.debug(f"Publishing a new message every {UPDATE_INTVL} seconds...")

    i2c = board.I2C()   # uses board.SCL and board.SDA
    batt = batt_sensor(i2c, BATT_SIZE)

    # # Connect to Adafruit IO
    # io = get_network_io_handle()

    # io.connect()
    # io.publish_multiple(values)    
    # logger.info("Successful publish to Adafruit IO...")


except Exception as e:
    # This doesn't work in adafruit_logger
    #logger.error('Failed to connect', exc_info=e)

    # Try this instead
    logger.error('Failed to connect: %s', e)

    ## swallow the exception and proceed directly to finally clause...


finally:
    # deep-sleep regardless of exception or not
    # (and restart everyhing on wakeup)

    # Create an alarm that will trigger NN seconds from now.
    wakeup_time = time.monotonic() + UPDATE_INTVL
    time_alarm = alarm.time.TimeAlarm(monotonic_time=wakeup_time)

    # Exit the program, and then deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # Does not return, so we never get here.
    


