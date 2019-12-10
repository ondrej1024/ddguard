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
#    03/12/2019 - Adapt to modified library names
#    03/12/2019 - Make Blynk uploader optional
#
#  TODO:
#    - Upload missed data when the pump returns into range
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
import cnl24driverlib
import nightscoutlib
from sensor_codes import SENSOR_EXCEPTIONS

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


sensor_exception_codes = {
    SENSOR_EXCEPTIONS.SENSOR_OK:               SENSOR_EXCEPTIONS.SENSOR_OK_STR,
    SENSOR_EXCEPTIONS.SENSOR_INIT:             SENSOR_EXCEPTIONS.SENSOR_INIT_STR,
    SENSOR_EXCEPTIONS.SENSOR_CAL_NEEDED:       SENSOR_EXCEPTIONS.SENSOR_CAL_NEEDED_STR,
    SENSOR_EXCEPTIONS.SENSOR_ERROR:            SENSOR_EXCEPTIONS.SENSOR_ERROR_STR,
    SENSOR_EXCEPTIONS.SENSOR_CAL_ERROR:        SENSOR_EXCEPTIONS.SENSOR_CAL_ERROR_STR,
    SENSOR_EXCEPTIONS.SENSOR_CHANGE_SENSOR:    SENSOR_EXCEPTIONS.SENSOR_CHANGE_SENSOR_STR,
    SENSOR_EXCEPTIONS.SENSOR_END_OF_LIFE:      SENSOR_EXCEPTIONS.SENSOR_END_OF_LIFE_STR,
    SENSOR_EXCEPTIONS.SENSOR_NOT_READY:        SENSOR_EXCEPTIONS.SENSOR_NOT_READY_STR,
    SENSOR_EXCEPTIONS.SENSOR_READING_HIGH:     SENSOR_EXCEPTIONS.SENSOR_READING_HIGH_STR,
    SENSOR_EXCEPTIONS.SENSOR_READING_LOW:      SENSOR_EXCEPTIONS.SENSOR_READING_LOW_STR,
    SENSOR_EXCEPTIONS.SENSOR_CAL_PENDING:      SENSOR_EXCEPTIONS.SENSOR_CAL_PENDING_STR,
    SENSOR_EXCEPTIONS.SENSOR_CHANGE_CAL_ERROR: SENSOR_EXCEPTIONS.SENSOR_CHANGE_CAL_ERROR_STR,
    SENSOR_EXCEPTIONS.SENSOR_TIME_UNKNOWN:     SENSOR_EXCEPTIONS.SENSOR_TIME_UNKNOWN_STR,
    SENSOR_EXCEPTIONS.SENSOR_WAITING:          SENSOR_EXCEPTIONS.SENSOR_WAITING_STR
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
   
   #TODO: check if file exists

   try:
      # Read Blynk parameters
      read_config.blynk_server    = config.get('blynk', 'server').split("#")[0].strip('"').strip("'").strip()
      read_config.blynk_token     = config.get('blynk', 'token').split("#")[0].strip('"').strip("'").strip()
      read_config.blynk_heartbeat = int(config.get('blynk', 'heartbeat').split("#")[0].strip('"').strip("'"))
   except ConfigParser.NoOptionError, ConfigParser.NoSectionError:
      syslog.syslog(syslog.LOG_ERR, "ERROR - Needed blynk option not found in config file")
      return False

   try:
      # Read Nightscout parameters
      read_config.nightscout_server     = config.get('nightscout', 'server').split("#")[0].strip('"').strip("'").strip()
      read_config.nightscout_api_secret = config.get('nightscout', 'api_secret').split("#")[0].strip('"').strip("'").strip()
   except ConfigParser.NoOptionError, ConfigParser.NoSectionError:
      syslog.syslog(syslog.LOG_ERR, "ERROR - Needed nightscout option not found in config file")
      return False

   try:
      # Read BGL parameters
      read_config.bgl_low_val      = int(config.get('bgl', 'bgl_low').split("#")[0].strip('"').strip("'"))
      read_config.bgl_pre_low_val  = int(config.get('bgl', 'bgl_pre_low').split("#")[0].strip('"').strip("'"))
      read_config.bgl_pre_high_val = int(config.get('bgl', 'bgl_pre_high').split("#")[0].strip('"').strip("'"))
      read_config.bgl_high_val     = int(config.get('bgl', 'bgl_high').split("#")[0].strip('"').strip("'"))
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

   try:
      blynk.disconnect()
   except:
      pass
   syslog.syslog(syslog.LOG_NOTICE, "Exiting DD-Guard daemon")
   sys.exit()


#########################################################
#
# Function:    blynk_upload()
# Description: Blynk uploader
# 
#########################################################
def blynk_upload(data):

   if data != None:
      print "Uploading data to Blynk"
       
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
# Function:    upload_live_data()
# Description: Read live data from pump and upload it 
#              to the enabled cloud services
#              This runs once at startup and then as a 
#              periodic timer every 5min
# 
#########################################################
def upload_live_data():
   
   # Guard against multiple threads
   if upload_live_data.active:
      return
    
   upload_live_data.active = True
   
   print "read live data from pump"
   hasFailed = True
   numRetries = MAX_RETRIES_AT_FAILURE
   while hasFailed and numRetries > 0:
      try:
         liveData = cnl24driverlib.readLiveData()
         hasFailed = False
      except:
         print "unexpected ERROR occured while reading live data"
         syslog.syslog(syslog.LOG_ERR, "Unexpected ERROR occured while reading live data")
         liveData = None
         numRetries -= 1
         if numRetries > 0:
            time.sleep(5)
    
   # Upload data to Blynk server
   if blynk != None:
      blynk_upload(liveData)

   # TEST
   #liveData = {"actins":0.5, 
               #"bgl":778,
               #"time":"111",
               #"trend":2,
               #"unit":60,
               #"batt":25
              #}

   # Upload data to Nighscout server
   if nightscout != None:
      nightscout.upload(liveData)
    
   upload_live_data.active = False


##########################################################           
# Setup
##########################################################           

# read configuration parameters
if read_config(CONFIG_FILE) == False:
   sys.exit()

blynk_enabled = (read_config.blynk_token != "") and (read_config.blynk_server != "")
nightscout_enabled = (read_config.nightscout_server != "") and (read_config.nightscout_api_secret != "")

# Init Blynk instance
if blynk_enabled:
   print "Blynk upload is enabled"
   blynk = blynklib.Blynk(read_config.blynk_token,
                          server=read_config.blynk_server.strip(),
                          heartbeat=read_config.blynk_heartbeat)

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
else:
   blynk = None

# Init Nighscout instance (if requested)
if nightscout_enabled:
   print "Nightscout upload is enabled"
   nightscout = nightscoutlib.nightscout_uploader(server = read_config.nightscout_server, 
                                                  secret = read_config.nightscout_api_secret)
else:
   nightscout = None

# Register timer function   
timer = blynktimer.Timer()
@timer.register(interval=5, run_once=True)
@timer.register(interval=UPDATE_INTERVAL, run_once=False)
def timer_function():
    # Run this as separate thread so we don't cause ping timeouts
    thread.start_new_thread(upload_live_data,())

   
##########################################################           
# Initialization
##########################################################           
syslog.syslog(syslog.LOG_NOTICE, "Starting DD-Guard daemon, version "+VERSION)

# Init signal handler
signal.signal(signal.SIGINT, on_sigterm)
signal.signal(signal.SIGTERM, on_sigterm)

upload_live_data.active = False


##########################################################           
# Main loop
##########################################################           
while True:
   if blynk_enabled:
      blynk.run()
   timer.run() 
