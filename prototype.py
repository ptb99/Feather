##
## CircuitPython code for ESP32-S2 Feather w/ temp/humidity sensor
##


import time
import alarm
import board
import digitalio
import adafruit_logging as logging
import traceback

import wifi
import ssl
import socketpool

import adafruit_bme280.basic
import adafruit_sht31d
import adafruit_lc709203f

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


#print('code.py starting up...')

## some control params:
DEBUG = False
#UPDATE_INTVL = 60
UPDATE_INTVL = 300
#BATT_SIZE =  adafruit_lc709203f.PackSize.MAH400
BATT_SIZE =  adafruit_lc709203f.PackSize.MAH3000

logger = logging.getLogger('main')
logger.setLevel(logging.INFO)


class temp_sensor_bme280:
    """Reads multiple weather values (temp, humidity, pressure)"""

    def __init__(self, i2c, pressure_calib=None):
        """Set up Temp sensor"""
        super().__init__()
        self.bme280 = adafruit_bme280.basic.Adafruit_BME280_I2C(i2c)

        # change this to match the location's pressure (hPa) at sea level
        if (pressure_calib):
            self.bme280.sea_level_pressure = pressure_calib
        else:
            self.bme280.sea_level_pressure = 1013.25

    def get_temp_F(self):
        # convert C to F
        return self.bme280.temperature * 9/5 + 32

    def get_humidity(self):
        return self.bme280.relative_humidity

    def get_barometric(self):
        """return pressure in in-Hg"""
        # 1 in-Hg = 3,386.388640341 Pa = 33.8638864 hPa
        return self.bme280.pressure / 33.8638864 


class temp_sensor_sht30:
    """Reads multiple weather values (temp, humidity, pressure)"""

    def __init__(self, i2c):
        """Set up Temp sensor"""
        super().__init__()
        self.sensor = adafruit_sht31d.SHT31D(i2c)

        ## We'll be sampling this infrequently, so use High repeatability
        ## and single shot mode to let the sensor do the averaging.
        ## Unclear if clock_stretching is needed, but turn on just in case.
        self.sensor.mode = adafruit_sht31d.MODE_SINGLE
        self.sensor.repeatability = adafruit_sht31d.REP_HIGH
        self.sensor.clock_stretching = True

        logger = logging.getLogger('temp')
        logger.info(f"SHT30 serial num: {self.sensor.serial_number:#x}")

    def get_temp_F(self):
        # convert C to F
        return self.sensor.temperature * 9/5 + 32

    def get_humidity(self):
        return self.sensor.relative_humidity


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


class red_led:
    def __init__(self):
        super().__init__()
        self.led = digitalio.DigitalInOut(board.LED)
        self.led.direction = digitalio.Direction.OUTPUT

    def set_value(self, value):
        """Set value (T/F) for the red LED on the Feather"""
        self.led.value = value

    def blink(self, number=1):
        delay = 0.2
        for i in range(number):
            self.set_value(True)
            time.sleep(delay)
            self.set_value(False)
            time.sleep(delay)


class neo_led:
    # fill this in later...
    pass


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


logger.info("Connecting to Adafruit IO...")

try:
    logger.debug(f"Publishing a new message every {UPDATE_INTVL} seconds...")
    start_time = time.monotonic()

    # should also turn off red LED...
    led = red_led()
    led.set_value(False)

    i2c = board.I2C()   # uses board.SCL and board.SDA
    bme280 = temp_sensor_bme280(i2c)
    sht30 = temp_sensor_sht30(i2c)
    batt = batt_sensor(i2c, BATT_SIZE)

    ## Note: we grab values first to minimize CPU heating on temp value
    values = [('Alt-Temp', sht30.get_temp_F()),
              ('Alt-Humidity', sht30.get_humidity()),
              ('Pressure', bme280.get_barometric()),
              ('Battery-Charge', batt.get_level()),
              ]
    ## skip these in order to reduce battery consumption:
    #('Temp', bme280.get_temp_F()),
    #('Humidity', bme280.get_humidity()),
    #('Battery-V', batt.get_voltage()),
              

    ## for dev, can be handy to print values to console
    if DEBUG:
        tt = time.localtime() # not synced to real/NTP time...
        # returns (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec,
        #          tm_wday, tm_yday, tm_isdst)
        logger.debug(f"Publishing at {tt[0]}-{tt[1]}-{tt[2]} {tt[3]}:{tt[4]}:{tt[5]}", )
        for n,v in values:
            logger.debug(f"    {n}: {v}")


    # Connect to Adafruit IO
    io = get_network_io_handle()

    # Connect the callback methods defined above to Adafruit IO
    # io.on_connect = connected
    # io.on_disconnect = disconnected
    # io.on_subscribe = subscribe
    # io.on_unsubscribe = unsubscribe
    # io.on_message = message

    io.connect()
    io.publish_multiple(values)    
    logger.info("Successful publish to Adafruit IO...")


except Exception as e:
    # This doesn't work in adafruit_logger
    #logger.error('Failed to connect', exc_info=sys.exc_info())

    # Try this instead
    logger.error('Failed to connect: %s', e)
    traceback.print_exception()

    ## swallow the exception and proceed directly to finally clause...


finally:
    # deep-sleep regardless of exception or not
    # (and restart everyhing on wakeup)

    # Create an alarm that will trigger NN seconds from the start.
    wakeup_time = start_time + UPDATE_INTVL
    # wrap this in try-block or otherwise check wakeup_time is in the future
    time_alarm = alarm.time.TimeAlarm(monotonic_time=wakeup_time)

    # Exit the program, and then deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # Does not return, so we never get here.

