import tkinter as tk
import serial
from serial

class SerialConfig(tk.Frame):
    def __init__(self,parent,*args,**kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.port_var = tk.StringVar(self)
        self.port_var.set("Select serial port")
        self.port_option = tk.OptionMenu(self,self.port_var,*options_list)
        self.port_option.pack()

    def refreshPorts(self):
        #update port list
        pass


class ModeOptions(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

class DataEmbed(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)

class ClinostatControlSystem(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.serial_config = SerialConfig(self).pack(side="left",expand=True)
        self.mode_options = ModeOptions(self).pack(side="bottom",fill="y",expand=True)
        self.data_embed = DataEmbed(self).pack(side="right",fill="both",expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    ClinostatControlSystem(root).pack(side="top", fill="both", expand=True)
    root.mainloop()