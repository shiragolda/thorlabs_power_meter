"""
Simple interface to the Thorlabs PM16 power meter.

Tested on PM16-121, but likely works for all PM16 meters (and possibly
other Thorlabs power meters).

How to use:
>>> import PM16
>>> pm = PM16("/dev/usbtmc0") # Replace with whatever USBTMC port the meter is attached to
Current wavelength: 780 nm
>>> pm.set_wavelength(684) # Change wavelength to 684 nm
>>> pm.power() # Power as a float, in W
1.5692888e-02
>>> values = pm.stream() # Poll the power meter until keyboard interrupt
2.6368066 mW
2.7559481 mW
2.8252213 mW
...
# keyboard interrupt
>>> values
[0.0026368066, 0.0027559481, 0.00282522sudo13, ...]

Known issues: reads and writes to the power meter will sometimes start
timing out. The only solution to this seems to be to unplug and plug
back in the power meter and re-initialize the PM16 object.

Note: Thorlabs, as far as I can tell, doesn't publicly document the
USBTMC interface for their power meters. The USBTMC commands in this
class were copied from
https://github.com/djorlando24/pyLabDataLogger/blob/master/src/device/usbtmcDevice.py#L285.
"""

import time, os
import tkinter as tk
from tkinter import font
import numpy as np

os.chdir("/home/labuser/googledrive/Calcium/code/calcium_control")
from zmqPublisher import zmqPublisher
os.chdir("/home/labuser/googledrive/Calcium/code/calcium_control/thorlabs_power_meter")


class USBTMC:
    """
    Simple implememntation of a USBTMC device driver, in the style of
    visa.h
    """
    def __init__(self, device):
        self.device = device
        self.FILE = os.open(device, os.O_RDWR)

        # TODO: Test that the file opened

    def write(self, command):
        os.write(self.FILE, command.encode());

    def read(self, length = 4000):
        return os.read(self.FILE, length).decode("utf-8")

    def query(self, command, length = 4000):
        self.write(command)
        return self.read(length)

    def getName(self):
        self.write("*IDN?")
        return self.read(300)

    def sendReset(self):
        self.write("*RST")

    def close(self):
        os.close(self.FILE)

class PM16(USBTMC):
    """
    Simple interface to the Thorlabs PM16 power meter.
    """

    def __init__(self, device):
        super().__init__(device)
        time.sleep(1)
        print(self.set_auto_range())
        print("Current wavelength: {:.0f} nm".format(self.get_wavelength()))

        self.publisher_started = False


    def power(self):
        """Read the power from the meter in Watts."""
        return float(self.query("Read?"))


    def set_wavelength(self, wavelength):
        """
        Set the wavelength of the power meter. Acceptable range:
        400-1100 nm.
        """
        if not 400 <= wavelength <= 1100:
            raise ValueError("{} nm is not in [400, 1100] nm.".format(wavelength))

        self.write("SENS:CORR:WAV {}".format(wavelength))

    def get_wavelength(self):
        """Get the current wavelength of the power meter, in nm."""
        return float(self.query("SENS:CORR:WAV?"))

    def set_auto_range(self):
        """Set the power meter to auto-range mode."""
        self.write("SENS:CORR:RANG:AUTO 1")
        return "Auto-range on: %s"%(str(bool(float(self.query("SENS:CURR:RANG:AUTO?")))))

    def zero_powermeter(self):
        """Zero the power meter at its current reading. Returns some number that has to do with the zeroed value. Don't know the units yet. """
        self.write("SENS:CORR:COLL:ZERO:INIT")
        return(self.query("SENS:CORR:COLL:ZERO:MAGN?"))

    def set_range(self,range=4.95e-3):
        """Set the range on the power meter - I don't know what these units are yet."""
        self.write("SENS:CURR:RANG:AUTO 0")
        self.write("SENS:CURR:RANG: UPP {}".format(range))

    def start_publisher(self):
        self.publisher = zmqPublisher(5556,'power_meter')
        self.publisher_started = True

    def publish_data(self,data):
        if not self.publisher_started:
            self.start_publisher()
        #self.publisher = zmqPublisher(5556,'power_meter')
        self.publisher.publish_data(data)

    def launch_gui(self):
        gui = PowerMeterGUI(self)



class PowerMeterGUI():
    def __init__(self,power_meter):
        self.pm = power_meter

        self.root = tk.Tk()
        self.root.title("Power Meter")

        icon = tk.PhotoImage(file='power_meter_icon.png')
        self.root.iconphoto(False, icon)

        self.publish = tk.BooleanVar()
        self.publish.set(tk.FALSE)

        self.open_display()

    def open_display(self):

        self.window = tk.Frame(width=20,height=10)
        #self.window.grid_propagate(False)
        self.window.pack()

        self.wavelength_label_text = tk.StringVar()
        self.wavelength_label_text.set('Wavelength: %i nm'%self.pm.get_wavelength())
        self.wavelength_label=tk.Label(self.window,textvariable=self.wavelength_label_text,font=("Arial Bold", 20))
        self.wavelength_label.pack()

        self.power_font = ("Arial Bold", 60)
        start_power = 1e3*self.pm.power()
        self.power_label = tk.Label(self.window,text='%.6f mW'%start_power,font=self.power_font)
        self.power_font = font.Font(size=100)
        self.power_label.pack()


        self.wavelength_frame = tk.Frame()
        tk.Label(self.wavelength_frame,text="Enter wavelength in nm").pack()

        self.wavelength = tk.StringVar()

        tk.Entry(self.wavelength_frame,textvariable = self.wavelength).pack()
        tk.Button(self.wavelength_frame,text="Change Wavelength",command=self.handle_wavelength_button_click).pack()

        tk.Checkbutton(self.wavelength_frame,text="Publish values?",var=self.publish).pack()


        self.wavelength_frame.pack()

        self.create_font_size_array()

        self.root.after(100, self.refresh_power)
        self.root.after(1000,self.stream_publish_power)
        self.root.bind("<Configure>",self.font_resize)
        self.root.mainloop()

    def handle_wavelength_button_click(self):
        new_wavelength = float(self.wavelength.get())
        self.pm.set_wavelength(new_wavelength)
        self.wavelength_label_text.set('Wavelength: %i nm'%new_wavelength)
        self.wavelength.set("")

    def refresh_power(self):
        new_power = 1e3*self.pm.power()
        self.power_label.config(text='%.6f mW'%new_power)
        self.root.after(100, self.refresh_power)

    def stream_publish_power(self):
        if self.publish.get():
            self.pm.publish_data(1e3*self.pm.power())
        self.root.after(1000,self.stream_publish_power)

    def create_font_size_array(self):
        font_size_array = np.linspace(200,1,num=50,dtype=int)
        self.font_obj_list = [font.Font(size=i) for i in font_size_array]
        placeholder_text = '500.000000 mW'
        self.text_widths = [i.measure(placeholder_text) for i in self.font_obj_list]


    def calc_best_font_size(self,x):

        diff_array = [(x-i) for i in self.text_widths]
        item_index = diff_array.index(np.min([n for n in diff_array if n>0]))
        self.power_font = self.font_obj_list[item_index]
        #print(self.power_font['size'])

    def font_resize(self,event=None):
        x = self.root.winfo_width()
        y = self.root.winfo_height()
        xp = self.power_label.winfo_width()
        yp = self.power_label.winfo_height()
        #print('root: %i x %i, label: %i x %i'%(x,y,xp,yp))

        self.calc_best_font_size(x)
        self.power_label.config(font=self.power_font)

if __name__=='__main__':
    pm = PM16('/dev/PowerMeter')
    pm.launch_gui()

"""
Other commands: SENS:CORR:POW:PDI:RESP? returns a number
                SENS:CORR:COLL:ZERO:STATE? returns 0 or 1
                SENS:CURR:RANG:AUTO? returns 1 if auto-range enabled
                SENS:CORR:WAV?MAX ???
                SENS:CORR:WAV?MIN

"""