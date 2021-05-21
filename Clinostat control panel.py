import tkinter as tk
import tkinter.scrolledtext
import serial.tools
from serial.tools import list_ports
import clin_comm
from datetime import datetime


def getPorts() -> list:

    return [str(port).split(" ")[0] for port in serial.tools.list_ports.comports()]

def makeHeadline(direction:str):
    pass


class serialConsole(tk.scrolledtext.ScrolledText):

    def __init__(self,parent,**kwargs):
        tk.scrolledtext.ScrolledText.__init__(self,parent,**kwargs)
        self.tag_config("MESSAGE",foreground="green")
        self.tag_config("ERROR",foreground="red")
        self.tag_config("CCS", foreground="red")
        self.tag_config("DIRECTION", foreground="red")
        self.tag_config("CONTROLLER", foreground="red")
        self.configure(state="disabled")

    def println(self,string,headline=None,msg_type="MESSAGE"):
        self.configure(state="normal")
        time = datetime.now()
        if headline is not None:
            headline = time.strftime("%Y/%m/%d %H:%M:%S ") + headline
        else:
            headline = time.strftime("%Y/%m/%d %H:%M:%S: ")

        self.insert("end",headline,msg_type)
        self.insert("end",string + '\n',"TEXT")
        self.configure(state="disabled")
        self.see("end")
        #todo: Add logging to textfile


class SerialConfig(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.available_ports = getPorts()

        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_option_var = tk.StringVar(self)
        self.port_option_var.set("Select serial port")

        self.port_description = tk.StringVar()
        self.port_description.set("Select serial port:")

        self.port_menu_frame = tk.Frame(self)
        self.port_label = tk.Label(self.port_menu_frame, textvariable=self.port_description)
        self.port_menu = tk.OptionMenu(self.port_menu_frame, self.port_option_var, *self.available_ports)
        self.refresh_button = tk.Button(self.port_menu_frame, command=self.refreshPorts, text="Refresh")
        self.refresh_button.config(width=17)
        self.port_menu.config(width=14)
        self.port_label.grid(row=0,column=0)
        self.port_menu.grid(row=1, column=0,pady=2)
        self.refresh_button.grid(row=2, column=0,pady=2)

        self.connections_frame = tk.Frame(self)
        self.connect_button = tk.Button(self.connections_frame, command=self.connectToPort, text="Connect")
        self.connect_button.config(width=17)
        self.disconnect_button = tk.Button(self.connections_frame, command=self.disconnectPort, text="Disconnect")
        self.disconnect_button.config(width=17)
        self.disconnect_button.configure(state="disabled")
        self.connect_button.grid(row=0, column=0,pady=2)
        self.disconnect_button.grid(row=1, column=0,pady=2)

        self.console = serialConsole(self,font=("normal",8))
        self.console.configure(width=65,height=20)

        self.port_menu_frame.grid(row=0,column=0,padx=10,sticky="n")
        self.connections_frame.grid(row=1, column=0,padx=10,sticky="s")
        self.console.grid(row=0,column=1,rowspan=2)

    def refreshPorts(self) -> None:

        self.available_ports = getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_menu['menu'].delete(0, "end")
        for port in self.available_ports:
            self.port_menu['menu'].add_command(label=port, command=tk._setit(self.port_option_var, port))

    def connectToPort(self):

        if self.parent.parent.device is not None:
            self.parent.parent.device.close_serial()

        potential_port = self.port_option_var.get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.",headline="ERROR: ", msg_type="ERROR")
        else:
            if clin_comm.tryConnection(potential_port):
                self.parent.parent.device = clin_comm.Clinostat(potential_port)
                self.parent.parent.device.port_name = potential_port
                self.console.println("Succesfully connected to {}.".format(potential_port), headline="STATUS: ")
                self.disconnect_button.configure(state="normal")
                self.connect_button.configure(state="disabled")
                self.parent.enableStart()

            else:
                self.console.println("Connection failed.",headline="ERROR: ",msg_type="ERROR")

    def disconnectPort(self):

        self.parent.parent.device.close_serial()
        self.console.println("Succesfully disconnected from {}.".format(self.parent.parent.device.port_name),
                             headline="STATUS: ")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.parent.disableAllModes()


class ModeOptions(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # self.refresh_button = tk.Button(self.port_menu_frame, command=self.refreshPorts, text="Refresh")
        # self.refresh_button.config(width=17, height=1)

        self.button_frame = tk.Frame(self)
        self.abort_button = tk.Button(self.button_frame,command=self.handleAbort,text="Abort")
        self.abort_button.config(width=17,background="#bf4032",activebackground="#eb7063",
                                 foreground="white",disabledforeground="#d1d1d1")
        self.abort_button.config(state="disabled")

        self.run_button = tk.Button(self.button_frame,command=self.handleRun,text="Run")
        self.run_button.config(width=17)
        self.run_button.config(state="disabled")

        self.pause_button = tk.Button(self.button_frame,command=self.handlePause,text="Pause")
        self.pause_button.config(width=17)
        self.pause_button.config(state="disabled")

        self.resume_button = tk.Button(self.button_frame,command=self.handleResume,text="Resume")
        self.resume_button.config(width=17)
        self.resume_button.config(state="disabled")

        self.home_button = tk.Button(self.button_frame,command=self.handleHome,text="Home")
        self.home_button.config(width=17)
        self.home_button.config(state="disabled")


        self.abort_button.grid(row=0,column=0,pady=2)
        self.run_button.grid(row=1, column=0,pady=2)
        self.pause_button.grid(row=2, column=0,pady=2)
        self.resume_button.grid(row=3, column=0,pady=2)
        self.home_button.grid(row=4, column=0,pady=2)
        self.button_frame.grid(row=0,column=0,padx=10)

    def gatherRPM(self):
        pass

    def handleAbort(self):
        self.run_button.configure(state="normal")
        self.home_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.abort_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        # self.parent.parent.device.abort()
        pass

    def handleRun(self):
        self.abort_button.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.home_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        # self.parent.parent.device.run(self.gatherRPM)
        pass

    def handlePause(self):
        self.resume_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        # self.parent.parent.device.pause()
        pass

    def handleResume(self):
        self.resume_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        # self.parent.parent.device.resume()
        pass

    def handleHome(self):
        # self.parent.parent.device.home()
        pass

    def disableButtons(self):

        self.abort_button.config(state="disabled")
        self.run_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.home_button.config(state="disabled")

    def enable(self):
        self.run_button.config(state="normal")
        self.home_button.config(state="normal")


class DataEmbed(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)


class ClinostatControlSystem(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.serial_config = SerialConfig(self)
        self.mode_options = ModeOptions(self)
        self.data_embed = DataEmbed(self)

        self.serial_config.grid(row=0,column=0,padx=10,pady=10)
        self.mode_options.grid(row=1,column=0,padx=10,pady=10,sticky="w")
        self.data_embed.grid(row=0, column=1, padx=10, pady=10)

    def disableAllModes(self):
        self.mode_options.disableButtons()

    def enableStart(self):
        self.mode_options.enable()



class App(tk.Tk):
    def __init__(self):
        self.device = None
        tk.Tk.__init__(self)


if __name__ == "__main__":
    root = App()
    root.title("Clinostat control system")
    root.iconbitmap("icon/favicon.ico")
    ClinostatControlSystem(root).pack(side="top", fill="both", expand=True)
    root.mainloop()