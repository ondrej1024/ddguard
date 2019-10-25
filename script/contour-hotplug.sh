#! /bin/bash
##################################################################################
#
# Author:        Ondrej Wisniewski
#
# Description:   Perform required action when Contour Next USB stick 
#                is connected or removed
#
# Usage:         This script is called by udev from the rules file
#                /etc/udev/rules.d/30-contour.rules
#
# Note:          The environment variables $ACTION and $DEVNAME are passed from
#                udev to get detailed information on the device and event
#
# Last modified: 16/10/2019
#
##################################################################################

# Log messages go to syslog
LOGCMD="logger -i contour-hotplug"

$LOGCMD "Event for SUBSYSTEM: "$SUBSYSTEM", ACTION="$ACTION", DEVPATH="$DEVPATH", DEVNAME="$DEVNAME

case $ACTION in
   add)
      if [ ! -z "$DEVNAME" ]; then
         $LOGCMD "Contour stick connected"
         # Do something here
      fi
      ;;
   remove)
      if [ ! -z "$DEVNAME" ]; then
         $LOGCMD "Contour stick removed"
         
         # Reset USB ports (power off/on)
         service networking stop
         sleep 2
         $LOGCMD "Power USB ports OFF"
         echo 0 > /sys/devices/platform/soc/3f980000.usb/buspower
         sleep 3
         $LOGCMD "Power USB ports ON"
         echo 1 > /sys/devices/platform/soc/3f980000.usb/buspower
         sleep 2
         service networking start
      fi
      ;;
   *)
      $LOGCMD "Unknown action"
      ;;
esac

exit 0
