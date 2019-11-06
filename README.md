# DD-Guard (Diabetes Data Guard)

## What it is

DD-Guard provides real time blood glucose and pump data for the "*[Medtronic Minimed 670G](https://www.medtronicdiabetes.com/products/minimed-670g-insulin-pump-system)*"  insulin pump system directly to your smart phone. It intends to be simple to use and easy to setup.

![ddguard-app-screen](img/ddguard-app-screen.png)

The 670G pump features continuous blood glucose measurements (CGM) via the "*Guardian Link 3*" sensor and stores the data on the device. The data can be viewed on the local display. However to date Medtronic provides no means of displaying the 670Gs real time data remotely on a mobile device. And that's exactly the functionality that DD-Guard adds to the system, so care givers can watch immediately the most important data from the sensor and the pump conveniently on their smart phones, wherever they are.

DD-Guard was inspired by the [NightScout](http://www.nightscout.info) project and the #WeAreNotWaiting community which promotes DIY efforts to take advantage of the latest technology to make life easier for people with Type-1 Diabetes and their care givers.



## Project Status

Currently I have implemented a working prototype of DD-Guard which I use in the real world to monitor my daughters blood glucose level and pump status at night when she is in her room where the gateway is located. On the app screen of my mobile phone I get updated data for blood glucose level (including history graph) and trend, remaining insulin units in the pumps tank and battery status. Basal rate and active insulin data could be added. The displayed data is color coded according to the actual conditions so it is immediately clear if there is anything critical which needs to be acted upon.

It would also be possible for my daughter to take the small gateway device with her when she is going to spend the night at a friends house, so I could still monitor her data. The gateway works as long as it has a power supply and a Wifi network connection.

At the moment the gateway is not mobile, so cannot provide the data when it is on the move. This is something I am planning to do.



## Screenshots

These are some typical screenshots form the smartphone app.

![Screenshots](img/ddguard-screenshots.png)



## How it works

The basic idea is to receive the real time data which was collected by the 670G with the DD-Guard gateway via the "*Contour Next Link* 2.4" glucose meter which operates as the radio bridge and then uploads the data to the cloud and a mobile device where it is eventually displayed with the DD-Guard app.

The DD-Guard gateway is a small single board computer, like the Raspberry Pi where the radio bridge is plugged into one of its USB ports. Cloud connection is established via the gateways Wifi.

![ddguard-overview](img/ddguard-overview.png)



## What hardware do you need

In order to use DD-Guard you need the following items:

- Medtronic Minimed 670G insulin pump
- Guardian Link blood glucose sensor and radio transmitter 
- Contour Next Link 2.4 blood glucose meter and radio bridge
- A single board computer with USB and Wifi like RaspberryPi 3 or similar as DD-Guard gateway
- A smartphone

If the person you build this system for is a T1D patient on insulin pump therapy you probably already have the first 3 items if you chose the Medtronic device. And chances are good you already have a smartphone.

So all you need to do is build your own gateway. It needs a USB port to connect to the radio bridge and Wifi to connect to the cloud.



![ddguard-gateway](img/ddguard-gw-sm.png)



## What software do you need

These are the logical software components which are needed to make it all work together:

- The **DD-Guard smartphone app** which receives the data from the cloud and displays it.
- The **Cloud service** which receives the data from the gateway and forwards it to the smartphone app
- The **DD-Guard gateway software** which periodically receives the data from the pump and uploads it to the cloud service



## Disclaimer

This project is not associated to or endorsed by [Medtronic](https://www.medtronicdiabetes.com). If you decide to use DD-Guard then you do this entirely at your own risk. I am not reliable for any damage it might cause. 