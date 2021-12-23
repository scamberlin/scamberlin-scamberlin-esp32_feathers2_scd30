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

#i2c = board.I2C()
i2c = busio.I2C(board.SCL, board.SDA, frequency=50000)
scd = adafruit_scd30.SCD30(i2c)
scd.self_calibration_enabled = True
scd.forced_recalibration_reference = 412

# The SCD30 reset generates a hiccup on the SCL and SDA lines
# which can end up not being handled well by different hosts.
scd.reset()

# The MCP2221 is known to not like the SCD30 reset hiccup.
# See below for more information:
# https://github.com/adafruit/Adafruit_CircuitPython_SCD30/issues/2
# Can get around it by resetting via this hack.
# pylint:disable=protected-access
if hasattr(i2c, "_i2c"):
  # we're using Blinka, check for MCP2221
  if hasattr(i2c._i2c, "_mcp2221"):
    # reset it
    i2c._i2c._mcp2221._reset()

w.feed()

displayio.release_displays()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 64
BORDER = 2

display = adafruit_displayio_sh1107.SH1107(display_bus, width=WIDTH, height=HEIGHT, rotation=0)
display.auto_refresh = True
font = terminalio.FONT
splash = displayio.Group()
display.show(splash)

def mqtt_on_connect(mqtt_client, userdata, flags, rc):
  print("Connected to MQTT Broker!")
  print("Flags: {0}\n RC: {1}".format(flags, rc))

def mqtt_on_disconnect(mqtt_client, userdata, rc):
  print("Disconnected from MQTT Broker!")

def mqtt_on_subscribe(mqtt_client, userdata, topic, granted_qos):
  print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def mqtt_on_unsubscribe(mqtt_client, userdata, topic, pid):
  print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def mqtt_on_publish(mqtt_client, userdata, topic, pid):
  print("Published to {0} with PID {1}".format(topic, pid))

def mqtt_on_message(client, topic, message):
  print("{0}:{1}".format(topic, message))

try:
  pool = socketpool.SocketPool(wifi.radio)
  mqtt_client = MQTT.MQTT(
    broker=config.mqtt_broker,
    port=config.mqtt_port,
    socket_pool=pool,
  )
#  mqtt_client.on_connect=mqtt_on_connect
#  mqtt_client.on_disconnect=mqtt_on_disconnect
#  mqtt_client.on_subscribe=mqtt_on_subscribe
#  mqtt_client.on_unsubscribe=mqtt_on_unsubscribe
#  mqtt_client.on_publish=mqtt_on_publish
  mqtt_client.on_message=mqtt_on_message
except Exception as e:
  print(e)

w.feed()

while True:
  try:
    if scd.data_available:
      print("-------------------------------------------------------------------------------")
      print("IP address:", wifi.radio.ipv4_address)
      print("Temperature:", scd.temperature, "degrees C")
      print("Humidity:", scd.relative_humidity, "%%rH")
      print("CO2:", scd.CO2, "PPM")
      # scd.temperature_offset = 10
      print("Temperature offset:", scd.temperature_offset)
      # scd.measurement_interval = 4
      print("Measurement interval:", scd.measurement_interval)
      # scd.self_calibration_enabled = True
      print("Self-calibration enabled:", scd.self_calibration_enabled)
      # scd.ambient_pressure = 1100
      print("Ambient Pressure:", scd.ambient_pressure)
      # scd.altitude = 100
      print("Altitude:", scd.altitude, "meters above sea level")
      # scd.forced_recalibration_reference = 409
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
    main_label = ""
    #main_label = label.Label(font, text="{:.1f} cel {:.1f} ppm".format(scd.temperature, scd.CO2), color=0xFFFFFF, scale=2, padding_top=2)
    main_label = label.Label(font, text="{:.1f} ppm".format(scd.CO2), color=0xFFFFFF, scale=2, padding_top=2)
    main_label.anchor_point = (0, 0)
    main_label.anchored_position = (14, 14)
    splash = main_label
    display.show(splash)
    mqtt_client.unsubscribe(config.mqtt_topic)
    mqtt_client.disconnect()
    w.feed()
    time.sleep(5)
  except Exception as e:
    print(e)
