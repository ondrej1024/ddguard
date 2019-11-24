#!/usr/bin/env python
###############################################################################
#  
#  Diabetes Data Guard (DD-Guard): Gateway module
#  
#  Description:
#
#    The DD-Guard gateway module periodically receives real time data from the 
#    Medtronic Minimed 670G insulin pump and uploads it to the cloud service
#  
#  Dependencies:
#
#    DD-Guard uses the Python driver by paazan for the "Contour Next Link 2.4" 
#    radio bridge to the Minimed 670G to download real time data from the pump.
#    https://github.com/pazaan/decoding-contour-next-link
#    
#    For the cloud connection and app communication the official Blynk Python
#    library is used.
#    https://github.com/blynkkk/lib-python
#
#  Author:
#
#    Ondrej Wisniewski (ondrej.wisniewski *at* gmail.com)
#  
#  Changelog:
#
#    23/09/2019 - Initial public release
#    13/10/2019 - Add handling of parameters from configuration file
#    24/10/2019 - Add handling of BGL status codes
#    24/10/2019 - Add handling of display colors according to limits
#    02/11/2019 - Run timer function as asynchronous thread
#    07/11/2019 - Add missing sensor exception codes
#    24/11/2019 - Integrate Nightscout uploader
#
#  TODO:
#    - Add some notification mechanism for alarms e.g. Telegram or Pushover message
#    - Upload data to Tidepool
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
import signal
import syslog
import sys
import time
import thread
import ConfigParser
import read_minimed_next24
import nightscoutlib


VERSION = "0.4"

UPDATE_INTERVAL = 300
MAX_RETRIES_AT_FAILURE = 3

# virtual pin definitions
VPIN_SENSOR  = 1
VPIN_BATTERY = 2
VPIN_UNITS   = 3
VPIN_ARROWS  = 4
VPIN_STATUS  = 5

# color definitions
BLYNK_GREEN  = "#23C48E"
BLYNK_BLUE   = "#04C0F8"
BLYNK_YELLOW = "#ED9D00"
BLYNK_RED    = "#D3435C"

# Sensor exception codes
SENSOR_OK                   = 0x0300                     
SENSOR_OK_STR               = "Sensor OK"
SENSOR_INIT                 = 0x0301 
SENSOR_INIT_STR             = "Sensor warming up"
SENSOR_CAL_NEEDED           = 0x0302 
SENSOR_CAL_NEEDED_STR       = "Calibrate sensor now "
SENSOR_ERROR                = 0x0303
SENSOR_ERROR_STR            = "Updating sensor"
SENSOR_CAL_ERROR            = 0x0304
SENSOR_CAL_ERROR_STR        = "Calibration error"
SENSOR_CHANGE_SENSOR        = 0x0305
SENSOR_CHANGE_SENSOR_STR    = "Change sensor"
SENSOR_END_OF_LIFE          = 0x0306 
SENSOR_END_OF_LIFE_STR      = "Sensor expired"
SENSOR_NOT_READY            = 0x0307
SENSOR_NOT_READY_STR        = "Sensor not ready"
SENSOR_READING_HIGH         = 0x0308
SENSOR_READING_HIGH_STR     = "Sensor reading too high"  
SENSOR_READING_LOW          = 0x0309
SENSOR_READING_LOW_STR      = "Sensor reading too low"
SENSOR_CAL_PENDING          = 0x030A
SENSOR_CAL_PENDING_STR      = "Calibrating sensor"
SENSOR_CHANGE_CAL_ERROR     = 0x030B
SENSOR_CHANGE_CAL_ERROR_STR = "Cal error - Change sensor"
SENSOR_TIME_UNKNOWN         = 0x030C
SENSOR_TIME_UNKNOWN_STR     = "Time unknown"

sensor_exception_codes = {   
    SENSOR_OK:               SENSOR_OK_STR,
    SENSOR_INIT:             SENSOR_INIT_STR,
    SENSOR_CAL_NEEDED:       SENSOR_CAL_NEEDED_STR,
    SENSOR_ERROR:            SENSOR_ERROR_STR,
    SENSOR_CAL_ERROR:        SENSOR_CAL_ERROR_STR,
    SENSOR_CHANGE_SENSOR:    SENSOR_CHANGE_SENSOR_STR,
    SENSOR_END_OF_LIFE:      SENSOR_END_OF_LIFE_STR,
    SENSOR_NOT_READY:        SENSOR_NOT_READY_STR,
    SENSOR_READING_HIGH:     SENSOR_READING_HIGH_STR,
    SENSOR_READING_LOW:      SENSOR_READING_LOW_STR,
    SENSOR_CAL_PENDING:      SENSOR_CAL_PENDING_STR,
    SENSOR_CHANGE_CAL_ERROR: SENSOR_CHANGE_CAL_ERROR_STR,
    SENSOR_TIME_UNKNOWN:     SENSOR_TIME_UNKNOWN_STR
}

is_connected = False

CONFIG_FILE = "/etc/ddguard.conf"


#########################################################
#
# Function:    read_config()
# Description: Read parameters from config file
# 
#########################################################
def read_config(cfilename):
   
   # Parameters from global config file
   config = ConfigParser.ConfigParser()
   config.read(cfilename)

   try:
      # Read Blynk parameters
      read_config.blynk_server    = config.get('blynk', 'server').strip('"').strip("'").split("#")[0]
      read_config.blynk_token     = config.get('blynk', 'token').strip('"').strip("'").split("#")[0]
      read_config.blynk_heartbeat = int(config.get('blynk', 'heartbeat').strip('"').strip("'").split("#")[0])
   except ConfigParser.NoOptionError, ConfigParser.NoSectionError:
      syslog.syslog(syslog.LOG_ERR, "ERROR - Needed blynk option not found in config file")
      return False

   try:
      # Read Nightscout parameters
      read_config.nightscout_server     = config.get('nightscout', 'server').strip('"').strip("'").split("#")[0]
      read_config.nightscout_api_secret = config.get('nightscout', 'api_secret').strip('"').strip("'").split("#")[0]
   except ConfigParser.NoOptionError, ConfigParser.NoSectionError:
      syslog.syslog(syslog.LOG_ERR, "ERROR - Needed nightscout option not found in config file")
      return False

   try:
      # Read BGL parameters
      read_config.bgl_low_val      = int(config.get('bgl', 'bgl_low').strip('"').strip("'").split("#")[0])
      read_config.bgl_pre_low_val  = int(config.get('bgl', 'bgl_pre_low').strip('"').strip("'").split("#")[0])
      read_config.bgl_pre_high_val = int(config.get('bgl', 'bgl_pre_high').strip('"').strip("'").split("#")[0])
      read_config.bgl_high_val     = int(config.get('bgl', 'bgl_high').strip('"').strip("'").split("#")[0])
   except ConfigParser.NoOptionError, ConfigParser.NoSectionError:
      syslog.syslog(syslog.LOG_ERR, "ERROR - Needed bgl option not found in config file")
      return False

   print ("Blynk server:    %s" % read_config.blynk_server)
   print ("Blynk token:     %s" % read_config.blynk_token)
   print ("Blynk heartbeat: %d" % read_config.blynk_heartbeat)
   print
   print ("Nightscout server:     %s" % read_config.nightscout_server)
   print ("Nightscout api_secret: %s" % read_config.nightscout_api_secret)
   print
   print ("BGL low:      %d" % read_config.bgl_low_val)
   print ("BGL pre low:  %d" % read_config.bgl_pre_low_val)
   print ("BGL pre high: %d" % read_config.bgl_pre_high_val)
   print ("BGL high:     %d" % read_config.bgl_high_val)
   print
   return True

    
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


#########################################################
#
# Function:    on_sigterm()
# Description: signal handler for the TERM and INT signal
# 
#########################################################
def blynk_upload(data):

   if data != None:
      print "send data to cloud backend"
       
      # Send sensor data
      if data["bgl"] in sensor_exception_codes:
         # Special status code
         blynk.virtual_write(VPIN_SENSOR, None)
         blynk.virtual_write(VPIN_ARROWS, "--")
         blynk.virtual_write(VPIN_STATUS, sensor_exception_codes[data["bgl"]])
         blynk.set_property(VPIN_STATUS, "color", BLYNK_RED)
      else:
         # Regular BGL data
         blynk.virtual_write(VPIN_SENSOR, data["bgl"])
         if data["bgl"] < read_config.bgl_low_val:
            blynk.set_property(VPIN_SENSOR, "color", BLYNK_RED)
         elif data["bgl"] < read_config.bgl_pre_low_val:
            blynk.set_property(VPIN_SENSOR, "color", BLYNK_YELLOW)
         elif data["bgl"] < read_config.bgl_pre_high_val:
            blynk.set_property(VPIN_SENSOR, "color", BLYNK_GREEN)
         elif data["bgl"] < read_config.bgl_high_val:
            blynk.set_property(VPIN_SENSOR, "color", BLYNK_YELLOW)
         else:
            blynk.set_property(VPIN_SENSOR, "color", BLYNK_RED)             
         blynk.virtual_write(VPIN_ARROWS, str(data["trend"])+" / "+str(data["actins"]))
         blynk.virtual_write(VPIN_STATUS, "Last update "+str(data["time"]).split(' ')[1].split('.')[0])
         blynk.set_property(VPIN_STATUS, "color", BLYNK_GREEN)
       
      # Send pump data
      blynk.virtual_write(VPIN_BATTERY, data["batt"])
      if data["batt"] <= 25:
         blynk.set_property(VPIN_BATTERY, "color", BLYNK_RED)
      elif data["batt"] <= 50:
         blynk.set_property(VPIN_BATTERY, "color", BLYNK_YELLOW)
      else:
         blynk.set_property(VPIN_BATTERY, "color", BLYNK_GREEN)
      blynk.virtual_write(VPIN_UNITS,   data["unit"])
      if data["unit"] <= 25:
         blynk.set_property(VPIN_UNITS, "color", BLYNK_RED)
      elif data["unit"] <= 75:
         blynk.set_property(VPIN_UNITS, "color", BLYNK_YELLOW)
      else:
         blynk.set_property(VPIN_UNITS, "color", BLYNK_GREEN)
   else:
      syslog.syslog(syslog.LOG_ERR, "Unable to get data from pump")
      blynk.set_property(VPIN_STATUS, "color", BLYNK_RED)


#########################################################
#
# Function:    send_pump_data()
# Description: Read data from pump and send it to cloud
#              This runs once at startup and then as a 
#              periodic timer every 5min
# 
#########################################################
def send_pump_data():
   
   # Guard against multiple threads
   if send_pump_data.active:
      return
    
   send_pump_data.active = True
   
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
         if numRetries > 0:
            time.sleep(5)
    
   # Upload data to Blynk server
   blynk_upload(pumpData)

   # TEST
   #pumpData = {"actins":1.5, 
               #"bgl":82,
               #"time":"111",
               #"trend":0,
               #"unit":63,
               #"batt":75
              #}

   # Upload data to Nighscout server
   if nightscout != None:
      nightscout.upload(pumpData)
    
   send_pump_data.active = False


##########################################################           
# Setup
##########################################################           

# read configuration parameters
if read_config(CONFIG_FILE) == False:
   sys.exit()

# Init Blynk instance
blynk = blynklib.Blynk(read_config.blynk_token,
                       server=read_config.blynk_server.strip(),
                       heartbeat=read_config.blynk_heartbeat)
timer = blynktimer.Timer()

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


@timer.register(interval=5, run_once=True)
@timer.register(interval=UPDATE_INTERVAL, run_once=False)
def timer_function():
    # Run this as separate thread so we don't cause ping timeouts
    thread.start_new_thread(send_pump_data,())

# Init Nighscout instance (if requested)
if read_config.nightscout_server != "" and read_config.nightscout_api_secret != "":
   print "Nightscout upload is enabled"
   nightscout = nightscoutlib.nightscout_uploader(server = read_config.nightscout_server, 
                                                  secret = read_config.nightscout_api_secret)
else:
   nightscout = None
   
   
##########################################################           
# Initialization
##########################################################           
syslog.syslog(syslog.LOG_NOTICE, "Starting DD-Guard daemon, version "+VERSION)

# Init signal handler
signal.signal(signal.SIGINT, on_sigterm)
signal.signal(signal.SIGTERM, on_sigterm)

send_pump_data.active = False

##########################################################           
# Main loop
##########################################################           
while True:
   blynk.run()
   timer.run() 
