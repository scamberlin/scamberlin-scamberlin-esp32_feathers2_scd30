import time, gc, os
import board
import busio
import wifi
import ssl
import displayio
import terminalio
import ipaddress
import socketpool
import microcontroller

import feathers2
import adafruit_dotstar
import adafruit_displayio_sh1107
import adafruit_scd30
import adafruit_minimqtt.adafruit_minimqtt as MQTT

from adafruit_display_text import label
from terminalio import *
import config

try:
  from watchdog import WatchDogMode
  w = microcontroller.watchdog
  w.timeout = 10.0
  w.mode = WatchDogMode.RESET
  w.feed()
  microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
except Exception as e:
  print(e)

feathers2.enable_LDO2(True)
dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.5, auto_write=True)
feathers2.led_set(True)
flash = os.statvfs('/')
flash_size = flash[0] * flash[2]
flash_free = flash[0] * flash[3]

print("\nHello from FeatherS2!")
print("---------------------\n")
print("Memory Info - gc.mem_free()")
print("---------------------------")
print("{} Bytes\n".format(gc.mem_free()))
print("Flash - os.statvfs('/')")
print("---------------------------")
print("Size: {} Bytes\nFree: {} Bytes\n".format(flash_size, flash_free))
w.feed()

for network in wifi.radio.start_scanning_networks():
  print(network, network.ssid, network.channel)
wifi.radio.stop_scanning_networks()

try:
  wifi.radio.connect(ssid=config.ssid,password=config.passwd)
except Exception as e:
  print(e)
w.feed()

i2c = busio.I2C(board.SCL, board.SDA, frequency=50000)
while not i2c.try_lock():
  pass
print("I2C address: {}".format([hex(x) for x in i2c.scan()]))
i2c.unlock()
w.feed()

scd = adafruit_scd30.SCD30(i2c)
scd.self_calibration_enabled = True
scd.forced_recalibration_reference = 412
try:
  scd.reset()
except Exception as e:
  print(e)
w.feed()

WIDTH = 128
HEIGHT = 64
BORDER = 2

try:
  displayio.release_displays()
  display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)
  display = adafruit_displayio_sh1107.SH1107(display_bus, width=WIDTH, height=HEIGHT, rotation=0)
  display.auto_refresh = True
  font = terminalio.FONT
  splash = displayio.Group()
  display.show(splash)
except Exception as e:
  print(e)

def mqtt_on_message(client, topic, message):
  print("{0}:{1}".format(topic, message))

try:
  pool = socketpool.SocketPool(wifi.radio)
  mqtt_client = MQTT.MQTT(
    broker=config.mqtt_broker,
    port=config.mqtt_port,
    socket_pool=pool,
  )
  mqtt_client.on_message=mqtt_on_message
except Exception as e:
  print(e)
w.feed()

while True:
  if scd.data_available:
    try:
      print("-------------------------------------------------------------------------------")
      print("IP address:", wifi.radio.ipv4_address)
      print("Temperature:", scd.temperature, "degrees C")
      print("Humidity:", scd.relative_humidity, "%%rH")
      print("CO2:", scd.CO2, "PPM")
      print("Temperature offset:", scd.temperature_offset)
      print("Measurement interval:", scd.measurement_interval)
      print("Self-calibration enabled:", scd.self_calibration_enabled)
      print("Ambient Pressure:", scd.ambient_pressure)
      print("Altitude:", scd.altitude, "meters above sea level")
      print("Forced recalibration reference:", scd.forced_recalibration_reference)
      print("")
      w.feed()
    except Exception as e:
      print(e)
    try:
      mqtt_client.connect()
      mqtt_client.subscribe(config.mqtt_topic)
      payload = '{"location":"' + config.mqtt_location + '","cel":{:.1f}'.format(scd.temperature) + ',"rh":{:.1f}'.format(scd.relative_humidity) + ',"hpa":{:.1f}'.format(scd.ambient_pressure) + ',"ppm":{:.1f}'.format(scd.CO2)  + '}'
      mqtt_client.publish(config.mqtt_topic, payload)
      mqtt_client.unsubscribe(config.mqtt_topic)
      mqtt_client.disconnect()
      w.feed()
    except Exception as e:
      print(e)
    try:
      main_label = ""
      main_label = label.Label(font, text="{:.1f} ppm".format(scd.CO2), color=0xFFFFFF, scale=2, padding_top=2)
      main_label.anchor_point = (0, 0)
      main_label.anchored_position = (14, 14)
      splash = main_label
      display.show(splash)
      w.feed()
    except Exception as e:
      print(e)
  time.sleep(5)

