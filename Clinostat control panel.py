import tkinter as tk
import tkinter.scrolledtext
import serial.tools
from serial.tools import list_ports
import clin_comm


def getPorts() -> list:

    return [str(port).split(" ")[0] for port in serial.tools.list_ports.comports()]

def makeHeadline(direction:str):
    pass


class serialConsole(tk.scrolledtext.ScrolledText):

    def __init__(self,parent,**kwargs):
        tk.scrolledtext.ScrolledText.__init__(self,parent,**kwargs)
        self.tag_config("headline",foreground="green")
        self.tag_config("error",foreground="red")
        self.configure(state="disabled",width=70)


    def writeRow(self,headline,string):
        self.configure(state="normal")
        self.insert("end",headline,"headline")
        self.insert("end",string + '\n',"message")
        self.configure(state="disabled")
        #todo: Add logging to textfile

class SerialConfig(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.available_ports = getPorts()

        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_option_var = tk.StringVar(self)
        self.port_option_var.set("Select serial port")

        self.port_description = tk.StringVar()
        self.port_description.set("Select serial port:")

        self.serial_label = tk.Label(self, textvariable=self.port_description)

        self.port_menu = tk.OptionMenu(self, self.port_option_var, *self.available_ports)
        self.port_menu.config(width= 15)

        self.refresh_button = tk.Button(self, command=self.refreshPorts,text="Refresh")
        self.refresh_button.config(width=17)

        self.connect_button = tk.Button(self, command=self.connectToPort, text="Connect")
        self.connect_button.config(width=17)

        self.console = serialConsole(self)

        self.serial_label.grid(row=0, column=0,pady=10)
        self.port_menu.grid(row=1, column=0,padx=5)
        self.refresh_button.grid(row=2, column=0,padx=5)
        self.connect_button.grid(row=3, column=0,padx=5)
        self.console.grid(row=1,column=1,rowspan=3)

    def refreshPorts(self) -> None:

        self.available_ports = getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_menu['menu'].delete(0, "end")
        for port in self.available_ports:
            self.port_menu['menu'].add_command(label=port, command=tk._setit(self.port_option_var, port))

    def connectToPort(self):

        potential_port = self.port_option_var.get()

        # if clin_comm.tryConnection(potential_port):
        #     parent.device = clin_comm.Clinostat(port)
        # else:
        #     console.print("Connection")


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

        self.serial_config = SerialConfig(self).pack(side="left",fill="both",expand=True)
        self.mode_options = ModeOptions(self).pack(side="bottom",fill="y",expand=True)
        self.data_embed = DataEmbed(self).pack(side="right",fill="both",expand=True)
        self.device = None


if __name__ == "__main__":
    root = tk.Tk()
    ClinostatControlSystem(root).pack(side="top", fill="both", expand=True)
    root.mainloop()