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
#    19/11/2019 - Initial public release
#    25/11/2019 - Add exception code handling
#    29/11/2019 - Upload of real device serial and pump date
#    13/12/2019 - Check for "lost sensor" condition
#    14/04/2020 - Adapt to new data format from CNL driver
#    27/04/2020 - Add pump status handling
#    28/06/2020 - Syntax updates for Python3
#    02/01/2021 - Upload latest bolus
#
#  Copyright 2019-2020, Ondrej Wisniewski 
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
import json
import syslog
import hashlib
import requests
from sensor_codes import SENSOR_EXCEPTIONS


# Nightscout error codes
class NS_ERROR:
   SENSOR_NOT_ACTIVE     = 1  # "?SN"
   MINIMAL_DEVIATION     = 2  # "?MD"
   NO_ANTENNA            = 3  # "?NA"
   SENSOR_NOT_CALIBRATED = 5  # "?NC"
   COUNTS_DEVIATION      = 6  # "?CD"
   ABSOLUTE_DEVIATION    = 9  # "?AD"
   POWER_DEVIATION       = 10 # "???"
   BAD_RF                = 12 # "?RF"

# Nightscout trend codes
class NS_TREND:
   NONE                  = "NONE"
   TRIPLE_UP             = "TripleUp"
   DOUBLE_UP             = "DoubleUp"
   SINGLE_UP             = "SingleUp"
   FOURTY_FIVE_UP        = "FortyFiveUp"
   FLAT                  = "Flat"
   FOURTY_FIVE_DOWN      = "FortyFiveDown"
   SINGLE_DOWN           = "SingleDown"
   DOUBLE_DOWN           = "DoubleDown"
   TRIPLE_DOWN           = "TripleDown"
   NOT_COMPUTABLE        = "NOT COMPUTABLE"
   RATE_OUT_OF_RANGE     = "RATE OUT OF RANGE"
   NOT_SET               = "NONE"

# Nightscout uploader class
class nightscout_uploader(object):
   
   def __init__(self, server, secret):
      if "http" in server.strip():
         self.ns_url  = server.strip()
      else:
         self.ns_url     = "http://"+server.strip()
      self.api_secret = hashlib.sha1(str(secret.strip()).encode('utf-8')).hexdigest()
      self.api_base   = "/api/v1/"
      self.device     = "medtronic-600://"
      self.headers    = {
                           "user-agent":"dd-guard",
                           "Content-Type":"application/json",
                           "api-secret":self.api_secret
                        }
      self.latest_bolus = 0
      
   # Trend mapping
   def direction_str(self, trend):
      if trend   == -3:
         return NS_TREND.TRIPLE_DOWN
      elif trend == -2:
         return NS_TREND.DOUBLE_DOWN
      elif trend == -1:
         return NS_TREND.SINGLE_DOWN
      elif trend == 0:
         return NS_TREND.FLAT
      elif trend == 1:
         return NS_TREND.SINGLE_UP
      elif trend == 2:
         return NS_TREND.DOUBLE_UP
      elif trend == 3:
         return NS_TREND.TRIPLE_UP
      else:
         return NS_TREND.RATE_OUT_OF_RANGE
      
   # Exception code mapping
   def exception_code(self, sgv):
      if sgv in [SENSOR_EXCEPTIONS.SENSOR_CAL_NEEDED]:
         return NS_ERROR.SENSOR_NOT_CALIBRATED,NS_TREND.NOT_COMPUTABLE 
      elif sgv in [SENSOR_EXCEPTIONS.SENSOR_CHANGE_CAL_ERROR, 
                   SENSOR_EXCEPTIONS.SENSOR_CHANGE_SENSOR,
                   SENSOR_EXCEPTIONS.SENSOR_END_OF_LIFE]:
         return NS_ERROR.SENSOR_NOT_ACTIVE,NS_TREND.NOT_COMPUTABLE
      elif sgv in [SENSOR_EXCEPTIONS.SENSOR_READING_LOW]:
         return 40,NS_TREND.RATE_OUT_OF_RANGE
      elif sgv in [SENSOR_EXCEPTIONS.SENSOR_READING_HIGH]:
         return 400,NS_TREND.RATE_OUT_OF_RANGE
      elif sgv in [SENSOR_EXCEPTIONS.SENSOR_CAL_PENDING, 
                   SENSOR_EXCEPTIONS.SENSOR_INIT, 
                   SENSOR_EXCEPTIONS.SENSOR_TIME_UNKNOWN, 
                   SENSOR_EXCEPTIONS.SENSOR_NOT_READY, 
                   SENSOR_EXCEPTIONS.SENSOR_ERROR]:
         return NS_ERROR.NO_ANTENNA,NS_TREND.NOT_COMPUTABLE
      
      
   #########################################################
   #
   # Function:    upload_entries()
   # Description: Upload sensor data via the entries/ 
   #              API endpoint
   # 
   #########################################################
   def upload_entries(self, data):

      rc = True
      url = self.ns_url + self.api_base + "entries.json"
      sgv = data["sensorBGL"]
      trend = data["trendArrow"]
      date = data["sensorBGLTimestamp"]
      
      # Check for "lost sensor" condition
      # We don't upload any sensor data in this case
      if (sgv == 0) and (trend == -3): # and (date.strftime("%c").find("01:00:00 1970") != -1):
         print("Sensor lost, not uploading SGV data")
         return False
      
      # Check for exception codes
      if sgv >= 0x0300:
         sgv,trend_str = self.exception_code(sgv)
      else:
         trend_str = self.direction_str(trend)
      
      payload = {
            "device":self.device+data["serial"],
            "type":"sgv",
            "dateString":date.isoformat(),
            "date":int(date.strftime("%s"))*1000,
            "sgv":sgv,
            "direction":trend_str
         }
      #print("url: " + url)
      #print("headers: "+json.dumps(self.headers))
      #print("payload: "+json.dumps(payload))
      
      try:
         #print "Send API request"
         r = requests.post(url, headers = self.headers, data = json.dumps(payload))
         #print "API response: "+r.text
         if r.status_code != requests.codes.ok:
            syslog.syslog(syslog.LOG_ERR, "Uploading entries record returned error "+str(r.status_code))
            rc = False
      except:
         #print "Uploading entries record failed with exception"
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
   def upload_devicestatus(self, data):
   
      rc = True
      url = self.ns_url + self.api_base + "devicestatus.json"
      date = data["pumpTime"]
      
      # Build pump status
      if data["pumpStatus"]["cgmActive"]:
         status = " | "
         if data["sensorStatus"]["exception"]==0:
            status = status + str(data["sensorBatteryLevelPercentage"]) + "% "
         if data["sensorCalMinutesRemaining"]>0:
            status = status + "{0}:{1:02d}h".format(int(data["sensorCalMinutesRemaining"]/60),data["sensorCalMinutesRemaining"]%60)
      else:
         status = ""
      
      payload = {
            "device":self.device+data["serial"],
            "created_at": int(date.strftime("%s"))*1000,
            "uploaderBattery":100, # FIXME
            "pump": {
               "clock":int(date.strftime("%s"))*1000,
               "reservoir":data["insulinUnitsRemaining"],
               "battery": {
                  "percent":data["batteryLevelPercentage"]
               },
               "iob": {
                  "timestamp":int(date.strftime("%s"))*1000,
                  "bolusiob":data["activeInsulin"]
               },
               "status": {
                  "bolusing":True if (data["pumpStatus"]["bolusingNormal"]|data["pumpStatus"]["bolusingSquare"]|data["pumpStatus"]["bolusingDual"]) else False,
                  "suspended":True if data["pumpStatus"]["suspended"] else False,
                  "status":status
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
         #print "Uploading entries record failed with exception"
         syslog.syslog(syslog.LOG_ERR, "Uploading entries record failed with exception")
         rc = False
   
      # TODO: delete old entries
   
      return rc


   #########################################################
   #
   # Function:    upload_bolus()
   # Description: Upload last bolus data via the
   #              treatments/API endpoint.
   # 
   #########################################################
   def upload_bolus(self, data):

      rc = True

      if self.latest_bolus == data["lastBolusReference"]:
          # latest bolus entry already uploaded -> skipping upload
          return rc

      url = self.ns_url + self.api_base + "treatments"
      date = data["lastBolusTime"]

      # TODO: send carbs and decide between correction- and
      #        "meals bolus" as eventType
      payload = {
         "eventType": "Correction Bolus",
         "created_at": int(date.strftime("%s"))*1000,
         "glucose": data["recentBGL"] or None,
         "insulin": data["lastBolusAmount"],
         "device": self.device+data["serial"],
      }

      #print("url: " + url)
      #print("payload: "+json.dumps(payload))

      try:
         #print "Send API request"
         r = requests.post(url, headers = self.headers, data = json.dumps(payload))
         #print(r)
         #print "API response: "+r.text
         if r.status_code != requests.codes.ok:
            syslog.syslog(syslog.LOG_ERR, "Uploading bolus record returned error "+str(r.status_code))
            rc = False
            pass
         else:
            self.latest_bolus = data["lastBolusReference"]
            print("...uploaded new bolus entry")
            pass
      except:
         #print("Uploading bolus record failed with exception")
         syslog.syslog(syslog.LOG_ERR, "Uploading bolus record failed with exception")
         rc = False
   
      # TODO: retrive old entries

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
         print("Uploading data to Nightscout")
         
         # Upload sensor data
         rc = self.upload_entries(data)
   
         # Upload pump data
         rc &= self.upload_devicestatus(data)

         # Upload last bolus
         rc &= self.upload_bolus(data)


      return rc   
