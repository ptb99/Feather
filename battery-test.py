# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import time
import board

USE_MAX1704 = True
if USE_MAX1704:
    from adafruit_max1704x import MAX17048
    chip_type = 'MAX1704x'
else:
    from adafruit_lc709203f import LC709203F
    chip_type = 'LC709203F'

print(f"{chip_type} simple test")
print("Make sure LiPoly battery is plugged into the board!")

if USE_MAX1704:
    sensor = MAX17048(board.I2C())
    print("IC version:", hex(sensor.chip_version))
else:
    sensor = LC709203F(board.I2C())
    print("IC version:", hex(sensor.ic_version))

while True:
    print(
        "Battery: %0.3f Volts / %0.1f %%" % (sensor.cell_voltage, sensor.cell_percent)
    )
    time.sleep(1)
