##
## CircuitPython example script
##

# BME280 temperature / humidity / barometric pressures sensor connected over I2C on address 0x77
# LC709203F Battery Monitor reports voltage / charge percent over I2C on address 0x0B.


import board
import digitalio
import time

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

while True:
    print("Hello, CircuitPython!")
    led.value = True
    time.sleep(1)
    led.value = False
    time.sleep(1)
