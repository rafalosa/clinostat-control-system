import tkinter as tk
import tkinter.scrolledtext
import serial.tools
from serial.tools import list_ports
import clin_comm
from datetime import datetime
import threading
import chamber_data_socket
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import yaml


class EmbeddedFigure(tk.Frame):

    def __init__(self,parent, figsize=(1,1), maxrecords=100,*args,**kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.fig = plt.figure(figsize=figsize)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.ax = self.fig.add_subplot()
        self.ax.set_xlim([0, maxrecords])
        self.ax.grid("minor")
        self.lines = [self.ax.plot([], [])[0]]
        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.canvas.draw()
        self.y_max = 1
        self.y_min = -1
        self.ax.set_ylim([self.y_min, self.y_max])

    def draw(self):
        self.canvas.draw()

    def plot(self,lines, x_data, y_data):

        if self.y_max < max(y_data):
            self.y_max = max(y_data)

        if self.y_min > min(y_data):
            self.y_min = min(y_data)

        lines.set_xdata(x_data)
        lines.set_ydata(y_data)
        self.ax.set_ylim([self.y_min, self.y_max])
        self.canvas.draw()

    def resetPlot(self):
        self.y_max = 1
        self.y_min = -1
        self.ax.set_ylim([self.y_min, self.y_max])
        for line in self.lines:
            line.set_xdata([])
            line.set_ydata([])
        self.canvas.draw()

    def addLinesObject(self):
        self.lines.append(self.ax.plot([], [])[0])


class SpeedIndicator(tk.Frame):

    def __init__(self,parent, label="Speed",unit="RPM", *args,**kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.var = tk.StringVar()
        self.var.set(label)
        self.label = tk.Label(self,textvariable=self.var)
        self.slider = tk.Scale(self,from_=5,to=0,orient="vertical",
                               resolution=0.1,length=100,command=self.updateEntry,showvalue=0,width=30)
        self.slider.configure(cursor="dot",troughcolor="green")

        self.entry_frame = tk.Frame(self)
        self.var = tk.DoubleVar()
        self.entry = tk.Entry(self.entry_frame,textvariable=self.var)
        self.entry.config(width=3,state="disabled")
        self.entry.configure(disabledbackground="white",disabledforeground="black")
        self.unit_var = tk.StringVar()
        self.unit_var.set(unit)
        self.entry_label = tk.Label(self.entry_frame,textvariable=self.unit_var)
        self.entry.grid(row=0,column=0)
        self.entry_label.grid(row=0, column=1)

        self.label.grid(row=0,column=0)
        self.slider.grid(row=1,column=0)
        self.entry_frame.grid(row=2, column=0)

    def updateEntry(self,*args):
        self.var.set(args[0])

    def getSpeed(self):
        return self.var.get()

    def configureState(self,state):
        if state == "disabled":
            self.slider.configure(troughcolor="#f3f3f3")
        else:
            self.slider.configure(troughcolor="#c2ebc0")
        self.slider.configure(state=state)

    def reset(self):
        self.slider.set(0)
        self.var.set(0.0)


class Console(tk.scrolledtext.ScrolledText):

    def __init__(self,parent,**kwargs):
        tk.scrolledtext.ScrolledText.__init__(self,parent,**kwargs)
        self.tag_config("MESSAGE",foreground="green")
        self.tag_config("ERROR",foreground="red")
        self.tag_config("CCS", foreground="red")
        self.tag_config("DIRECTION", foreground="red")
        self.tag_config("CONTROLLER", foreground="red")
        self.tag_config("TCP",foreground="magenta")
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
        # todo: Add logging to textfile


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
        self.connect_button = tk.Button(self.connections_frame, command=lambda: threading.Thread(
            target=self.connectToPort).start(), text="Connect")
        self.connect_button.config(width=17)
        self.disconnect_button = tk.Button(self.connections_frame, command=self.disconnectPort, text="Disconnect")
        self.disconnect_button.config(width=17)
        self.disconnect_button.configure(state="disabled")
        self.connect_button.grid(row=0, column=0,pady=2)
        self.disconnect_button.grid(row=1, column=0,pady=2)

        self.console = Console(self, font=("normal", 8))
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

    def connectToPort(self) -> None:

        self.connect_button.configure(state="disabled")
        if self.parent.parent.device is not None:
            self.parent.parent.device.close_serial()

        potential_port = self.port_option_var.get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.",headline="ERROR: ", msg_type="ERROR")
            self.connect_button.configure(state="normal")
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
                self.connect_button.configure(state="normal")

    def disconnectPort(self) -> None:

        self.parent.parent.device.close_serial()
        self.console.println("Succesfully disconnected from {}.".format(self.parent.parent.device.port_name),
                             headline="STATUS: ")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.parent.disableAllModes()


class ModeMenu(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.button_frame = tk.Frame(self)

        self.indicators_frame = tk.Frame(self)
        self.RPMindicator1 = SpeedIndicator(self.indicators_frame,label="1DOF\nspeed")
        self.RPMindicator2 = SpeedIndicator(self.indicators_frame,label="2DOF\nspeed")
        self.RPMindicator1.grid(row=0,column=0,padx=10)
        self.RPMindicator2.grid(row=0, column=1, padx=10)

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
        self.indicators_frame.grid(row=0,column=1,padx=10,rowspan=5)

        self.RPMindicator1.configureState(state="disabled")
        self.RPMindicator2.configureState(state="disabled")

    def gatherSpeed(self):
        return self.RPMindicator1.getSpeed(),self.RPMindicator2.getSpeed()

    def handleAbort(self):
        self.pause_button.configure(state="disabled")
        self.abort_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.enable()
        self.parent.parent.device.abort()
        pass

    def handleRun(self):
        self.abort_button.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.home_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        self.parent.parent.device.run(self.gatherSpeed)
        self.parent.blockIndicators()
        pass

    def handlePause(self):
        self.resume_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.parent.parent.device.pause()
        pass

    def handleResume(self):
        self.resume_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        self.disableIndicators()
        self.parent.parent.device.resume()
        pass

    def handleHome(self):
        self.parent.parent.device.home()
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
        self.RPMindicator1.configureState(state="normal")
        self.RPMindicator2.configureState(state="normal")

    def disableIndicators(self):
        self.RPMindicator1.configureState(state="disabled")
        self.RPMindicator2.configureState(state="disabled")

    def resetIndicators(self):
        self.RPMindicator1.configureState(state="normal")
        self.RPMindicator2.configureState(state="normal")
        self.RPMindicator1.reset()
        self.RPMindicator2.reset()
        self.RPMindicator1.configureState(state="disabled")
        self.RPMindicator2.configureState(state="disabled")


class DataEmbed(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.data_buffers = []
        self.plotting_flag = False
        self.new_data_available = False

        self.server_buttons_frame = tk.Frame(self)

        self.desc_var = tk.StringVar()
        self.desc_var.set("TCP data server:")
        self.server_label = tk.Label(self.server_buttons_frame,textvariable=self.desc_var)
        self.server_label.grid(row=0,column=0,columnspan=2)

        self.start_server_button = tk.Button(self.server_buttons_frame,
                                             text="Start server", command=self.handleRunServer)
        self.start_server_button.grid(row=1,column=0,pady=2,padx=5)
        self.start_server_button.configure(width=17)

        self.close_server_button = tk.Button(self.server_buttons_frame,
                                             text="Close server", command=self.handleCloseServer)
        self.close_server_button.grid(row=1, column=1, pady=2,padx=5)
        self.close_server_button.configure(width=17)
        self.close_server_button.configure(state="disabled")

        self.address_var = tk.StringVar()
        self.entry = tk.Entry(self.server_buttons_frame, textvariable=self.address_var)
        self.entry.config(width=20, state="disabled")
        self.entry.configure(disabledbackground="white", disabledforeground="black")

        self.address_label_var = tk.StringVar()
        self.address_label_var.set("Current server address:")

        self.address_label = tk.Label(self.server_buttons_frame,textvariable=self.address_label_var)
        self.address_label.grid(row=2,column=0)
        self.entry.grid(row=2,column=1)

        plt.rcParams['figure.facecolor'] = "#f0f0f0"
        plt.rcParams['font.size'] = 7

        self.grav_plot = EmbeddedFigure(self,figsize=(3,2),maxrecords=100)
        self.grav_plot.addLinesObject()
        self.grav_plot.addLinesObject()

        self.data_buffers.append([])
        self.data_buffers.append([])  # Data buffers for each lines object in EmbeddedFigure.
        self.data_buffers.append([])

        self.grav_plot.grid(row=1,column=0,padx=10)

        self.server_buttons_frame.grid(row=0, column=0, padx=10)

    def handleRunServer(self):
        server_object = self.parent.parent.server
        server_object.runServer()

    def enableInterface(self):  # Had to define different method for changing the button states. Since runServer()
        # is running on a different thread, a server.running flag cannot be checked, because it's state has not
        # been updated yet. Changing button states has to be done from within the runServer method.
        self.start_server_button.configure(state="disabled")
        self.close_server_button.configure(state="normal")
        server_object = self.parent.parent.server
        self.address_var.set(server_object.address + ":" + str(server_object.port))
        self.plotting_flag = True

    def handleCloseServer(self):
        self.plotting_flag = False
        self.resetDataBuffers()
        self.updateData()
        server_object = self.parent.parent.server
        server_object.close()
        self.start_server_button.configure(state="normal")
        self.close_server_button.configure(state="disabled")
        self.address_var.set("")

    def resetDataBuffers(self):
        size_ = len(self.data_buffers)
        self.data_buffers = []
        for i in range(size_):
            self.data_buffers.append([])

    def updateData(self):

        if all([bool(buffer) for buffer in self.data_buffers]):
            self.parent.parent.lock.acquire()
            for line,buffer in zip(self.grav_plot.lines,self.data_buffers):
                self.grav_plot.plot(line,np.arange(0,len(buffer)),buffer)

            self.new_data_available = False
            self.parent.parent.lock.release()

        else:
            self.grav_plot.resetPlot()


class ClinostatControlSystem(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.serial_config = SerialConfig(self)
        self.mode_options = ModeMenu(self)
        self.data_embed = DataEmbed(self)

        self.serial_config.grid(row=0,column=0,padx=10,pady=10,sticky="n")
        self.mode_options.grid(row=1,column=0,padx=10,pady=10,sticky="w")
        self.data_embed.grid(row=0, column=1, padx=10, pady=10,rowspan=2,sticky="n")

    def disableAllModes(self):
        self.mode_options.disableButtons()
        self.mode_options.resetIndicators()
        self.mode_options.disableIndicators()

    def blockIndicators(self):
        self.mode_options.disableIndicators()

    def enableStart(self):
        self.mode_options.enable()


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.device = None
        with open("config.yaml","r") as file:
            config = yaml.load(file,Loader=yaml.FullLoader)
        self.lock = threading.Lock()
        self.server = chamber_data_socket.DataServer(parent=self,
                                                     address=config["IP"],port=config["PORT"],thread_lock=self.lock)
        self.control_system = ClinostatControlSystem(self)
        self.control_system.pack(side="top", fill="both", expand=True)
        self.server.linkConsole(self.control_system.serial_config.console)

    def destroy(self):
        if self.server.running:
            self.server.close()
        # todo: Close any other running threads
        # todo: Close communication with serial port if it exists.
        tk.Tk.destroy(self)

    def programLoop(self):

        if self.control_system.data_embed.plotting_flag and self.control_system.data_embed.new_data_available:
            self.control_system.data_embed.updateData()

        # for thread in threading.enumerate():
        #     print(thread.name)

        self.after(1,self.programLoop)


def getPorts() -> list:

    return [str(port).split(" ")[0] for port in serial.tools.list_ports.comports()]


if __name__ == "__main__":
    root = App()
    root.title("Clinostat control system")
    root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
