###############################################################################
#  
#  Diabetes Data Guard (DD-Guard): Nightscout uploader library
#  
#  Description:
#
#    This library implements the uploader of the live sensor and pump  
#    data to the Nightscout REST API
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
import syslog
import hashlib
import requests


class nightscout_uploader(object):
   
   def __init__(self, server, secret):
      self.ns_url     = "http://"+server.strip()
      self.api_secret = hashlib.sha1(secret.strip()).hexdigest()
      self.api_base   = "/api/v1/"
      self.device     = "medtronic-600://1234567890"
      self.headers    = {
                           "user-agent":"dd-guard",
                           "Content-Type":"application/json",
                           "api-secret": self.api_secret
                        }
      
   def direction_str(self, trend):
      if trend   == -3:
         return "TripleDown"
      elif trend == -2:
         return "DoubleDown"
      elif trend == -1:
         return "SingleDown"
      elif trend == 0:
         return "Flat"
      elif trend == 1:
         return "SingleUp"
      elif trend == 2:
         return "DoubleUp"
      elif trend == 3:
         return "TripleUp"
      else:
         return "Out of range"
      

   #########################################################
   #
   # Function:    upload_entries()
   # Description: Upload sensor data via the entries/ 
   #              API endpoint
   # 
   #########################################################
   def upload_entries(self, sgv, trend, date_str):

      rc = True
      url = self.ns_url + self.api_base + "entries.json"
      payload = {
            "device":self.device,
            "type":"sgv",
            "date":int(time.time()*1000), # TODO: send pump time
            "sgv":sgv,
            "direction":self.direction_str(trend)      
         }
      #print "url: " + url
      #print "headers: "+json.dumps(self.headers)
      #print "payload: "+json.dumps(payload)
      
      try:
         #print "Send API request"
         r = requests.post(url, headers = self.headers, data = json.dumps(payload))
         #print "API response: "+r.text
         if r.status_code != requests.codes.ok:
            syslog.syslog(syslog.LOG_ERR, "Uploading entries record returned error "+str(r.status_code))
            rc = False
      except:
         print "Uploading entries record failed with exception"
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
   def upload_devicestatus(self, battery, reservoir, iob):
   
      rc = True
      url = self.ns_url + self.api_base + "devicestatus.json"
      payload = {
            "device":self.device,
            #"created_at": int(time.time()*1000),
            #"uploaderBattery": 100,
            "pump": {
               "clock":int(time.time()*1000), # TODO: send pump time
               "reservoir":reservoir,
               "battery": {
                  "percent":battery
               },
               "iob": {
                  "timestamp":int(time.time()*1000), # TODO: send pump time
                  "bolusiob":iob
               }
            }
         }
      #print "url: " + url
      #print "payload: "+json.dumps(payload)
  
      try:
         #print "Send API request"
         r = requests.post(url, headers = self.headers, data = json.dumps(payload))
         #print "API response: "+r.text
         if r.status_code != requests.codes.ok:
            syslog.syslog(syslog.LOG_ERR, "Uploading entries record returned error "+str(r.status_code))
            rc = False
      except:
         print "Uploading entries record failed with exception"
         syslog.syslog(syslog.LOG_ERR, "Uploading entries record failed with exception")
         rc = False
   
      # TODO: delete old entries
   
      return rc
   

   #########################################################
   #
   # Function:    upload()
   # Description: Upload sensor and pump data to the 
   #              Nightscout REST API
   # 
   #########################################################
   def upload(self, data):
   
      rc = True
      if data != None:
         print "Uploading data to Nightscout"
         
         # Upload sensor data
         rc = self.upload_entries(data["bgl"], data["trend"], data["time"])
   
         # Upload pump data
         rc &= self.upload_devicestatus(data["batt"], data["unit"], data["actins"])

      return rc   
