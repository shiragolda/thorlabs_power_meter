# thorlabs_power_meter
Python code to control Thorlabs Power Meter PM16

GUI displays current power reading in mW in large font. The wavelength can be changed via the GUI. 
Power meter readings can be optionally published to a zmq socket. 

Tested on PM16-121, but likely works for all PM16 meters (and possibly
other Thorlabs power meters).

The USBTMC commands in this
class were copied from
https://github.com/djorlando24/pyLabDataLogger/blob/master/src/device/usbtmcDevice.py#L285.
