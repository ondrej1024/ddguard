#! /bin/bash

BINDIR="/usr/local/bin"

if [ $UID -ne 0 ]; then 
   echo "Please run as root"
   exit
fi

echo "Installing program files"
cp ddguard.py $BINDIR
cp helpers.py $BINDIR
cp sensor_codes.py $BINDIR
cp cnl24driverlib.py $BINDIR
cp nightscoutlib.py $BINDIR

echo "Installing udev scripts"
cp script/30-contour.rules /etc/udev/rules.d/
cp script/contour-hotplug.sh $BINDIR

echo "Installing configuration file"
cp conf/ddguard.conf /etc/

echo "Enable and start daemon"
cp init.d/ddguard /etc/init.d/
systemctl enable ddguard.service
systemctl start ddguard.service
sleep 2

if [ $(systemctl is-active ddguard.service) == "active" ]; then 
   echo "Install successful" 
else
   echo "ERROR: Install failed"
fi

exit 0
