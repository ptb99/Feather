# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import terminalio
from adafruit_display_text import label
#from fourwire import FourWire
from displayio import FourWire
from adafruit_st7789 import ST7789


## Not sure why this doesn't work:
display = board.DISPLAY

## Alternate init:
# spi = board.SPI() 
# #display_bus = FourWire(spi, command=board.TFT_DC, chip_select=board.TFT_CS)
# display_bus = FourWire(spi, chip_select=board.TFT_CS)
# display = ST7789(
#     display_bus, rotation=270, width=240, height=135, rowstart=40, colstart=53
# )


# Set text, font, and color
text = "HELLO WORLD"
font = terminalio.FONT
color = 0x0000FF

# Create the text label
text_area = label.Label(font, text=text, color=color)

# Set the location
text_area.x = 100
text_area.y = 80

# Show it
display.root_group = text_area
#display.show(text_area)

# Loop forever so you can enjoy your image
while True:
    pass
