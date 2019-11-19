###############################################################################
#  
#  Diabetes Data Guard (DD-Guard): Nightscout uploader
#  
#  Description:
#
#    This module implements the uploader of the sensor and punp sata to the 
#    Nightscout REST API
#  
#  Author:
#
#    Ondrej Wisniewski (ondrej.wisniewski *at* gmail.com)
#  
#  Changelog:
#
#    19/09/2019 - Initial public release
#
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
import time
import json
import requests


ns_url     = "http://10.5.0.5:8080"
api_base   = "/api/v1/"
api_secret = "cc8a9a7c3670b6d3966fff040238f01a99da6b38"
device     = "medtronic-600://1234567890"

headers = {
      "user-agent":"dd-guard/0.3",
      "Content-Type":"application/json",
      "api-secret": api_secret
}


#########################################################
#
# Function:    upload_entries()
# Description: Upload sensor data via the entries/ 
#              API endpoint
# 
#########################################################
def upload_entries(sgv, trend, date_str):

   rc = True

   if trend   == -3:
      direction = "TripleDown"
   elif trend == -2:
      direction = "DoubleDown"
   elif trend == -1:
      direction = "SingleDown"
   elif trend == 0:
      direction = "Flat"
   elif trend == 1:
      direction = "SingleUp"
   elif trend == 2:
      direction = "DoubleUp"
   elif trend == 3:
      direction = "TripleUp"
   else:
      direction = "Out of range"

   payload = {
      "device":device,
      "type":"sgv",
      "date":int(time.time()*1000),
      "sgv":sgv,
      "direction":direction      
      }
   
   try:
      r = requests.post(ns_url+api_base+"entries.json", headers = headers, data = json.dumps(payload))
      #syslog.syslog(syslog.LOG_NOTICE, r.url)
      print "API response: "+r.text
      if r.status_code != requests.codes.ok:
         syslog.syslog(syslog.LOG_ERR, "Uploading entries record returned error "+str(r.status_code))
         rc = False
   except:
      syslog.syslog(syslog.LOG_ERR, "Uploading entries record failed with exception")
      rc = False
   
   return rc


#########################################################
#
# Function:    upload_devicestatus()
# Description: Upload pump data via the devicestatus/ 
#              API endpoint
# 
#########################################################
def upload_devicestatus(battery, reservoir, iob):
   
   rc = True
   
   payload = {
      "device":device,
      #"created_at": int(time.time()*1000),
      #"uploaderBattery": 100,
      "pump": {
         "clock":int(time.time()*1000),
         "reservoir": reservoir,
         "battery": {
            "percent": battery
         }
      }
   }
  
   try:
      r = requests.post(ns_url+api_base+"devicestatus.json", headers = headers, data = json.dumps(payload))
      #syslog.syslog(syslog.LOG_NOTICE, r.url)
      print "API response: "+r.text
      if r.status_code != requests.codes.ok:
         syslog.syslog(syslog.LOG_ERR, "Uploading entries record returned error "+str(r.status_code))
         rc = False
   except:
      syslog.syslog(syslog.LOG_ERR, "Uploading entries record failed with exception")
      rc = False
   
   # TODO: delete old entries
   
   return rc
   

#########################################################
#
# Function:    nightscout_uploader()
# Description: Upload sensor and pump data to the 
#              Nightscout REST API
# 
#########################################################
def nightscout_uploader(data):
   
   # Upload sensor data
   rc = upload_entries(data["bgl"], data["trend"], data["time"])
   
   # Upload pump data
   rc &= upload_devicestatus(data["batt"], data["unit"], data["actins"])

   return rc   


# TEST
#upload_entries(95, 2, "111")   
#upload_devicestatus(80, 130, 11)

d = {"actins":5.0, 
     "bgl":111,
     "time":"111",
     "trend":-1,
      "unit":55,
      "batt":99
     }

nightscout_uploader(d)
