##
## from: https://github.com/adafruit/Adafruit_CircuitPython_EPD/README.rst
##

import time
import board
#import digitalio
import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label
import adafruit_ssd1680


# release any previously configured displays
displayio.release_displays()

# create the spi device and pins we will need
spi = board.SPI()  # Uses SCK and MOSI

DISPLAY_WIDTH  = 250
DISPLAY_HEIGHT = 122

epd_cs = board.D9
epd_dc = board.D10
# can be None to not use these pins
#epd_rst = board.D5
#epd_busy = board.D6
epd_rst = None
epd_busy = None
epd_srcs = None

# Ours is a 3-color display
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Change text colors, choose from the following values:
# BLACK, WHITE, RED (note red on this display is not vivid)
FG_COLOR = BLACK
BG_COLOR = WHITE


# give them all to our driver
print("Creating display")

display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_rst, baudrate=1000000
)
time.sleep(1)

display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    busy_pin=epd_busy,
    highlight_color=0xFF0000,
    rotation=270,
)

## TODO: print out display.time_to_refresh (min refresh frequency)
#print('display refresh= ', display.time_to_refresh)

g = displayio.Group()

# Set a background
print("Set background")
# add extra height to work around "noise pixels" at bottom of display
background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT+10, 1)
palette = displayio.Palette(1)
palette[0] = BG_COLOR

# Put the background into the display group
bg_sprite = displayio.TileGrid(background_bitmap, pixel_shader=palette,
                               x=0, y=0)
g.append(bg_sprite)

# display.pixel(10, 100, Adafruit_EPD.BLACK)

print("Draw Rectangles")
rect1 = Rect(105, 75, 10, 10, fill=RED)
g.append(rect1)
rect2 = Rect(100, 70, 40, 30, outline=BLACK, stroke=3)
g.append(rect2)

## Not sure what the bug is, but instead of y values from 0 to 121, the
## display seems to work from 8 to 127 (making a size of 250x120).  
## There are also 2 rows of random dots at the bottom of the display.
print("Draw lines")
line = Line(0, 10, DISPLAY_WIDTH-1, 10, color=BLACK)
g.append(line)
line = Line(0, 20, DISPLAY_WIDTH-1, 20, color=BLACK)
g.append(line)
line = Line(0, 115, DISPLAY_WIDTH-1, 115, color=BLACK)
g.append(line)
line = Line(0, 125, DISPLAY_WIDTH-1, 125, color=BLACK)
g.append(line)
line = Line(0, 8, DISPLAY_WIDTH-1, 8, color=RED)
g.append(line)
line = Line(0, 127, DISPLAY_WIDTH-1, 127, color=RED)
g.append(line)
line = Line(0, 1, 0, DISPLAY_HEIGHT+4, color=RED)
g.append(line)
line = Line(249, 1, 249, DISPLAY_HEIGHT+4, color=RED)
g.append(line)

print("Draw text")
# Draw simple text using the built-in font into a displayio group
text_group = displayio.Group(scale=1, x=20, y=40)
#font = terminalio.FONT
## alt approach with bitmap font:
#font = bitmap_font.load_font("/fonts/LeagueSpartan-Bold-16.bdf")
font = bitmap_font.load_font("fonts/DejaVuSans-Bold24.pcf")
text_area = Label(font, text="Hello World!", color=FG_COLOR)
text_group.append(text_area)  # Add this text to the text group
g.append(text_group)
 
display.show(g)
print("display.show()")
time.sleep(10)

# Refresh the display to have everything show on the display
# NOTE: Do not refresh eInk displays more often than 180 seconds!
display.refresh()
print("refreshed")

# (optional) wait until display is fully updated
while display.busy:
    time.sleep(1)
print('display is now updated')

time.sleep(180)
print('refresh limit now reached (looping)')
# endless loop here so that we don't hit "Code done running."
while True:
    time.sleep(1)
