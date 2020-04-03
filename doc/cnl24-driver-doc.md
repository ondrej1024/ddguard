# CNL2.4 Driver documentation

This is an attempt to write some comprehensible documentation about the inner workings of the CNL2.4 Python driver originally written by [Lennart Goedhart](https://github.com/pazaan). It should help people digging into the core functionality and be able to fix bugs and implement improvements.



## Communication procedure sequence

### Init the driver class
    mt = Medtronic600SeriesDriver()

### Open the USB device
    mt.openDevice()

Just opens the HID communication device with the CNLs USB vendor and product ID

### Get device info (CNL serial number)

    mt.getDeviceInfo()

* Send control character `'X' (0x58)`
* Receive ASTM message containing CNL info
* Receive control character `ENQ (0x05)`

### Enter CNL control mode

    mt.enterControlMode()

* Send control character `NAK (0x15)`
* Receive control character `EOT (0x04)`
* Send control character `ENQ (0x05)`
* Receive control character `ACK (0x06)`

### Enter CNL passthrough mode

    mt.enterPassthroughMode()

* Send control character `'W|'`
* Receive control character `ACK (0x06)`
* Send control character `'Q|'`
* Receive control character `ACK (0x06)`
* Send control character `'1|'`
* Receive control character `ACK (0x06)`

### Request open connection to pump

    mt.openConnection()

Send a MiniMed message with operation `OPEN_CONNECTION (0x10)`

### Read info from pump (link and pump MAC)

    mt.readInfo()

Send a MiniMed message with operation `READ_INFO (0x14)`

### Read link encryption key from pump

    mt.readLinkKey()

Send a MiniMed message with operation `REQUEST_LINK_KEY (0x16)`

### Negotiate communication channel with pump

    mt.negotiateChannel()

Send an NGP message with command `JOIN_NETWORK (0x03)` for all possible radio channels

### Begin Extended High Speed Mode Session 

    mt.beginEHSM()

Send an NGP message with command `TRANSMIT_PACKET (0x05)` and command `0x0412` in payload

### Read pump time <sup>[1]</sup><sup>

    mt.getPumpTime()

Send an NGP message with command `TRANSMIT_PACKET (0x05)` and command `0x0403` in payload

### Read pump status info (bat, sgv, iob, ...) <sup>[1]</sup><sup>

    mt.getPumpStatus()

Send an NGP message with command `TRANSMIT_PACKET (0x05)` and command `0x0112` in payload

### Finish session

    mt.finishEHSM()
    mt.closeConnection()
    mt.exitPassthroughMode()
    mt.exitControlMode()
    mt.closeDevice()



## Error handling

TODO



## Notes

#### Note [1]

Information is requested from the pump via the following sequence of MiniMed messages. The message handler methods are implemented in the class `Medtronic600SeriesDriver`:

    send BayerBinaryMessage(0x12, ...)  # operation SEND_MESSAGE
    receive getBayerBinaryMessage(0x81) # operation SEND_MESSAGE_RESPONSE
    receive getBayerBinaryMessage(0x80) # operation RECEIVE_MESSAGE


​    
#### Note [2]

The sequence is implemented in the Android source in [`medtronic/service/MedtronicCnlService.java`](https://github.com/pazaan/600SeriesAndroidUploader/blob/master/app/src/main/java/info/nightscout/android/medtronic/service/MedtronicCnlService.java)
which calls the functions defined in [`medtronic/MedtronicCnlReader.java`](https://github.com/pazaan/600SeriesAndroidUploader/blob/master/app/src/main/java/info/nightscout/android/medtronic/MedtronicCnlReader.java)
which calls the low level functions defined in [`medtronic/message/ContourNextLinkMessage.java`](https://github.com/pazaan/600SeriesAndroidUploader/blob/master/app/src/main/java/info/nightscout/android/medtronic/message/ContourNextLinkMessage.java)



## References

[1] [Medtronic 600-series message structure](https://github.com/tidepool-org/uploader/blob/master/lib/drivers/medtronic600/docs/packetStructure.md)

[2] [Original CNL2.4 Python diver](https://github.com/pazaan/decoding-contour-next-link)

[3] [Android uploader](https://github.com/pazaan/600SeriesAndroidUploader)