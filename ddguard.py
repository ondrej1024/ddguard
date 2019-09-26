#!/usr/bin/env python
###############################################################################
#  
#  Diabetes Data Guard (DD-Guard): Gateway module
#  
#  Description:
#    The DD-Guard gateway software periodically receives real time data from 
#    the Minimed 670G pump and uploads it to the cloud service
#  
#  Dependencies:
#    DD-Guard uses the Python driver by paazan for the "Contour Next Link 2.4" 
#    radio bridge to the Minimed 670G to download real time data from the pump.
#    https://github.com/pazaan/decoding-contour-next-link
#
#  Author:
#    Ondrej Wisniewski (ondrej.wisniewski *at* gmail.com)
#  
#  Last modified:
#    23/09/2019
# 
#  Copyright 2019, Ondrej Wisniewski 
#  
#  This file is part of the DD-Guard project.
#  
#  DD-Guard is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with crelay.  If not, see <http://www.gnu.org/licenses/>.
#  
###############################################################################

import blynklib
import blynktimer
import time
import signal
import syslog
import sys
import read_minimed_next24


VERSION = "0.1"

UPDATE_INTERVAL = 300
MAX_RETRIES_AT_FAILURE = 3

# virtual pin definitions
VPIN_SENSOR  = 1
VPIN_BATTERY = 2
VPIN_UNITS   = 3
VPIN_ARROWS  = 4
VPIN_TIME    = 5

# color definitions
BLYNK_GREEN  = "#23C48E"
BLYNK_BLUE   = "#04C0F8"
BLYNK_YELLOW = "#ED9D00"
BLYNK_RED    = "#D3435C"


BLYNK_AUTH =  # insert your Auth Token here
BLYNK_HEARTBEAT = 30

blynk = blynklib.Blynk(BLYNK_AUTH, heartbeat=BLYNK_HEARTBEAT)
timer = blynktimer.Timer()

is_connected = False

@blynk.handle_event("connect")
def connect_handler():
   global is_connected
   if not is_connected:
      is_connected = True
      print('Connected to cloud server')
      syslog.syslog(syslog.LOG_NOTICE, "Connected to cloud server")

@blynk.handle_event("disconnect")
def disconnect_handler():
   global is_connected
   if is_connected:
      is_connected = False
      print('Disconnected from cloud server')
      syslog.syslog(syslog.LOG_NOTICE, "Disconnected from cloud server")


#########################################################
#
# Function:    send_pump_data()
# Description: Read data from pump and send it to cloud
#              This runs once at startup and then as a 
#              periodic timer every 5min
# 
#########################################################
@timer.register(interval=5, run_once=True)
@timer.register(interval=UPDATE_INTERVAL, run_once=False)
def send_pump_data():
   
    print "read data from pump"
    hasFailed = True
    numRetries = MAX_RETRIES_AT_FAILURE
    while hasFailed and numRetries > 0:
       try:
          pumpData = read_minimed_next24.readPumpData()
          hasFailed = False
       except:
          print "unexpected ERROR occured"
          syslog.syslog(syslog.LOG_ERR, "Unexpected ERROR occured")
          pumpData = None
          numRetries -= 1
          time.sleep(5)
    
    if pumpData != None:
       print "send data to cloud backend"
       # Set sensor data
       blynk.virtual_write(VPIN_SENSOR,  pumpData["bgl"] if pumpData["bgl"] != 770 else None)
       blynk.virtual_write(VPIN_ARROWS, pumpData["trend"])
       blynk.virtual_write(VPIN_TIME, str(pumpData["time"]).split(' ')[1].split('.')[0])
       blynk.set_property(VPIN_TIME, "color", BLYNK_GREEN)
       # Set pump data
       blynk.virtual_write(VPIN_BATTERY, pumpData["batt"])
       blynk.virtual_write(VPIN_UNITS,   pumpData["unit"])
    else:
       syslog.syslog(syslog.LOG_ERR, "Unable to get data from pump")
       # Clear sensor data
       blynk.virtual_write(VPIN_SENSOR, None)
       blynk.virtual_write(VPIN_ARROWS, 0)
       blynk.set_property(VPIN_TIME, "color", BLYNK_RED)
       # Clear pump data
       blynk.virtual_write(VPIN_BATTERY, 0)
       blynk.virtual_write(VPIN_UNITS, 0)
       
    print
    
#########################################################
#
# Function:    on_sigterm()
# Description: signal handler for the TERM and INT signal
# 
#########################################################
def on_sigterm(signum, frame):

   blynk.disconnect()
   syslog.syslog(syslog.LOG_NOTICE, "Exiting DD-Guard daemon")
   sys.exit()


##########################################################           
# Initialization
##########################################################           
syslog.syslog(syslog.LOG_NOTICE, "Starting DD-Guard daemon, version "+VERSION)

# Init signal handler
signal.signal(signal.SIGINT, on_sigterm)
signal.signal(signal.SIGTERM, on_sigterm)


##########################################################           
# Main loop
##########################################################           
while True:
   blynk.run()
   timer.run() 
