######################################
# thermometer_client.py
######################################
#
# Requires a 3.x Blue Gecko NCP device and pybgapi
# Looks for a device advertising the health thermometer service (like the
# soc-thermometer example project included in Silicon Labs Bluetooth SDKs),
# connects, enables indications, and then prints temperature measurement data
# to the console along with the RSSI of the link.
#
# Usage: python thermometer_client.py <serial_port_name>
#
######################################
# SPDX-License-Identifier: Zlib
#
# The licensor of this software is Silicon Laboratories Inc.
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#########################################

import sys
import bgapi

def sl_bt_on_event(node, evt):
  # This is the pybgapi event handler

  global state
  global service
  global characteristic
  global rssi

  if evt == 'bt_evt_system_boot':
    print("Boot event received! Major version: {}, minor version:{}".format(
        evt.major, evt.minor))
    node.bt.scanner.start(1, 2)
  elif evt == 'bt_evt_scanner_scan_report':
    i = 0
    while i < len(evt.data):
      field_len = evt.data[i]
      field_type = evt.data[i+1]
      if (field_type == 0x02) or (field_type == 0x03):
        if (evt.data[i+2 : i+field_len+1] == thermoService):
          print("Health thermometer service found - connecting...")
          # Stop scanning and connect to device
          node.bt.scanner.stop()
          node.bt.connection.open(evt.address, evt.address_type, 1)
      i = i + field_len + 1 # Parse next field
  elif evt == 'bt_evt_connection_opened':
    print("connection opened")
  elif evt == 'bt_evt_gatt_mtu_exchanged':
    state = 'service_discovery' # Kick off discovery state machine
    node.bt.gatt.discover_primary_services(evt.connection)
  elif evt == 'bt_evt_gatt_service':
    if (evt.uuid == thermoService):
      print("Service found...")
      service = evt.service
  elif evt == 'bt_evt_gatt_characteristic':
    if (evt.uuid == thermoChar):
      print("Characteristic found...")
      characteristic = evt.characteristic
  elif evt == 'bt_evt_gatt_procedure_completed':
    if (state == 'service_discovery'):
      node.bt.gatt.discover_characteristics(evt.connection, service)
      state = 'characteristic_discovery' # Advance to next state in the discovery state machine
    elif (state == 'characteristic_discovery'):
      # enable indications (0x02)
      node.bt.gatt.set_characteristic_notification(evt.connection,
        characteristic, 0x02);
  elif evt == 'bt_evt_gatt_characteristic_value':
    temperature = evt.value[1] + (evt.value[2] << 8) + (evt.value[3] << 16)
    print("Temperature: {}.{} C".format(int(temperature / 1000), int((temperature/10) % 100)))
    # Send confirmation of the received indication
    node.bt.gatt.send_characteristic_confirmation(evt.connection)
    # Read RSSI
    node.bt.connection.get_rssi(evt.connection)
  elif evt == 'bt_evt_connection_rssi':
      # Report RSSI of the connection
    print("RSSI = {} dBm".format(evt.rssi))
  else:
    print("Unhandled event: {}".format(evt))

# Main functionality
thermoService = bytes.fromhex("0918") # 0x1809, little endian
thermoChar = bytes.fromhex("1c2a") # 0x2a1c, little endian

# Open serial port from first command line parameter
connection = bgapi.SerialConnector(sys.argv[1])

# Use xapi from second command line parameter
node = bgapi.BGLib(connection, sys.argv[2])
node.open()
node.bt.system.reset(0)

state = None
service = None
characteristic = None

while True:
  try:
    evt = node.get_events(max_events = 1)
    if evt:
      sl_bt_on_event(node, evt[0])
  except (KeyboardInterrupt, SystemExit) as e:
    if node.is_open():
      # Send reset to stop doing whatever the NCP is doing
      node.bt.system.reset(0)
      node.close()
    print("Exiting...")
    sys.exit(1)
