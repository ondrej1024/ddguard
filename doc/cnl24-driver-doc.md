# CNL2.4 Driver documentation

This is an attempt to write some comprehensible documentation about the inner workings of the CNL2.4 Python driver originally written by [Lennart Goedhart](https://github.com/pazaan). It should help people digging into the core functionality and be able to fix bugs and implement improvements.



## Communication procedure sequence

### Init the driver class
    mt = Medtronic600SeriesDriver()

### Open the USB device
    mt.openDevice()

### Get device info (CNL serial number)
    mt.getDeviceInfo()

### Enter CNL control mode
    mt.enterControlMode()

### Enter CNL passthrough mode
    mt.enterPassthroughMode()

### Request open connection to pump
    mt.openConnection()

### Read info from pump (link and pump MAC)
    mt.readInfo()

### Read link encryption key from pump
    mt.readLinkKey()

### Negotiate communication channel with pump
    mt.negotiateChannel()

### Begin Extended High Speed Mode Session 
    mt.beginEHSM()

### Read pump time <sup>[1]</sup><sup>
    mt.getPumpTime()

### Read pump status info (bat, sgv, iob, ...) <sup>[1]</sup><sup>
    mt.getPumpStatus()

### Finish session
    mt.finishEHSM()
    mt.closeConnection()
    mt.exitPassthroughMode()
    mt.exitControlMode()
    mt.closeDevice()



## Notes

#### Note [1]

Information is requested from the pump via the following sequence of MiniMed messages:

    send BayerBinaryMessage(0x12, ...)  # operation SEND_MESSAGE
    receive BayerBinaryMessage(0x81)    # operation SEND_MESSAGE_RESPONSE
    receive getBayerBinaryMessage(0x80) # operation RECEIVE_MESSAGE


​    
#### Note [2]

The sequence is implemented in the Android source in `medtronic/service/MedtronicCnlService.java`
which calls the functions defined in `medtronic/MedtronicCnlReader.java`
which calls the low level functions defined in `medtronic/message/ContourNextLinkMessage.java`



## References

[1] [Medtronic 600-series message structure](https://github.com/tidepool-org/uploader/blob/master/lib/drivers/medtronic600/docs/packetStructure.md)

[2] [Original CNL2.4 Python diver](https://github.com/pazaan/decoding-contour-next-link)