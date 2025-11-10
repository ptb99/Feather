##
## CircuitPython code for ESP32-S2 Feather w/ temp/humidity sensor
##


import time
import alarm
import board
import adafruit_logging as logging


import wifi
import ssl
import socketpool

import adafruit_bme280.basic
import adafruit_lc709203f

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


def init_bme280(pressure_calib=None):
    """Set up Temp sensor, using default I2C bus"""
    i2c = board.I2C()   # uses board.SCL and board.SDA
    bme280 = adafruit_bme280.basic.Adafruit_BME280_I2C(i2c)

    # change this to match the location's pressure (hPa) at sea level
    if (pressure_calib):
        bme280.sea_level_pressure = pressure_calib
    else:
        bme280.sea_level_pressure = 1013.25

    return bme280


def init_batt_sensor():
    """Set up LC709204f sensor on default I2C bus"""
    i2c = board.I2C()   # uses board.SCL and board.SDA
    sensor = adafruit_lc709203f.LC709203F(i2c)
    sensor.pack_size = adafruit_lc709203f.PackSize.MAH400

    logger = logging.getLogger('battery')
    logger.info(f"Battery IC version: {sensor.ic_version:#x}")
    #print("Battery IC version:", hex(sensor.ic_version))
    return sensor


def get_network_io_handle():
    """Configure wifi network and Adafruit_IO handle"""

    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        print("WiFi connect failed: no secrets.py file")
        raise

    logger = logging.getLogger('wifi')
    logger.setLevel(logging.INFO)
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


#print('code.py starting up...')

bme280 = init_bme280()
batt = init_batt_sensor()

# Connect to Adafruit IO
io = get_network_io_handle()

# Connect the callback methods defined above to Adafruit IO
# io.on_connect = connected
# io.on_disconnect = disconnected
# io.on_subscribe = subscribe
# io.on_unsubscribe = unsubscribe
# io.on_message = message

logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
logger.info("Connecting to Adafruit IO...")

try:
    io.connect()
except Exception as e:
    # This doesn't work in adafruit_logger
    #logger.error('Failed to connect', exc_info=e)

    # Try this instead
    logger.error('Failed to connect: %s', e)

    # should prob deep-sleep here


# Below is an example of manually publishing a new  value to Adafruit IO.
UPDATE_INTVL = 30
DEBUG = False
logger.debug(f"Publishing a new message every {UPDATE_INTVL} seconds...")

while True:
    values = []

    temp = bme280.temperature * 9/5 + 32
    values.append(('Temp', temp))

    humid = bme280.relative_humidity
    values.append(('Humidity', humid))

    pressure = bme280.pressure / 33.8638864 
    # 1 in-Hg = 3,386.388640341 Pa = 33.8638864 hPa
    values.append(('Pressure', pressure))

    batt_level = batt.cell_percent
    values.append(('Battery-Charge', batt_level))

    batt_volts = batt.cell_voltage
    values.append(('Battery-V', batt_volts))

    # batt_temp = batt.cell_temperature
    # values.append(('Battery-Temp', batt_temp))

    ## Maybe this printout should be inside a debug flag?
    if DEBUG:
        tt = time.localtime() # not synced to real/NTP time...
        # returns (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
        logger.debug(f"Publishing at {tt[0]}-{tt[1]}-{tt[2]} {tt[3]}:{tt[4]}:{tt[5]}", )
        for n,v in values:
            logger.debug(f"    {n}: {v}")

    io.publish_multiple(values)

    #time.sleep(UPDATE_INTVL)

    # Create an alarm that will trigger NN seconds from now.
    wakeup_time = time.monotonic() + UPDATE_INTVL
    time_alarm = alarm.time.TimeAlarm(monotonic_time=wakeup_time)

    # Do a light sleep until the alarm wakes us.
    #alarm.light_sleep_until_alarms(time_alarm)

    # Exit the program, and then deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # Does not return, so we never get here.

