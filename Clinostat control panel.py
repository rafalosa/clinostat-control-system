import tkinter as tk
from tkinter import filedialog,messagebox
import clinostat_com
from datetime import datetime
import threading
import data_socket
import matplotlib.pyplot as plt
import numpy as np
import yaml
import queue
import os
from shutil import copyfile
from ttkthemes import themed_tk
import custom_tk_widgets as cw


class SerialConfig(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.available_ports = clinostat_com.getPorts()

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

        self.console = cw.Console(self, font=("normal", 8))
        self.console.configure(width=65,height=20)

        self.port_menu_frame.grid(row=0,column=0,padx=10,sticky="n")
        self.connections_frame.grid(row=1, column=0,padx=10,sticky="s")
        self.console.grid(row=0,column=1,rowspan=2)

    def refreshPorts(self) -> None:

        self.available_ports = clinostat_com.getPorts()
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
            if clinostat_com.tryConnection(potential_port):
                self.parent.parent.device = clinostat_com.Clinostat(potential_port)
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
        self.parent.parent.device = None
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.parent.disableAllModes()


class ModeMenu(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.button_frame = tk.Frame(self)

        self.indicators_frame = tk.Frame(self)
        self.RPMindicator1 = cw.SlidingIndicator(self.indicators_frame, label="1st DOF\nspeed")
        self.RPMindicator2 = cw.SlidingIndicator(self.indicators_frame, label="2nd DOF\nspeed")
        self.ACCELindicator1 = cw.SlidingIndicator(self.indicators_frame, label="1st DOF\nacceleration", unit="RPM/s")
        self.ACCELindicator2 = cw.SlidingIndicator(self.indicators_frame, label="2nd DOF\nacceleration", unit="RPM/s")
        self.RPMindicator1.grid(row=0,column=0,padx=15)
        self.RPMindicator2.grid(row=0, column=1, padx=15)
        self.ACCELindicator1.grid(row=0, column=2, padx=15)
        self.ACCELindicator2.grid(row=0, column=3, padx=15)
        self.indicators = [self.RPMindicator1,self.RPMindicator2,self.ACCELindicator1,self.ACCELindicator2]

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
        self.indicators_frame.grid(row=0,column=1,padx=10,rowspan=5,sticky="N")

        for indicator in self.indicators:
            indicator.configureState(state="disabled")

    def gatherIndicatorValues(self):
        return (indicator.getValue() for indicator in self.indicators)

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
        self.parent.parent.device.run(self.gatherIndicatorValues)
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
        for indicator in self.indicators:
            indicator.configureState(state="normal")

    def disableIndicators(self):
        for indicator in self.indicators:
            indicator.configureState(state="disabled")

    def resetIndicators(self):
        for indicator in self.indicators:
            indicator.configureState(state="normal")
            indicator.reset()
            indicator.configureState(state="disabled")


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

        self.grav_plot = cw.EmbeddedFigure(self,figsize=(3,2),maxrecords=100)
        self.grav_plot.addLinesObject()
        self.grav_plot.addLinesObject()

        self.text_area = tk.Text(self,height=8,width=34)

        self.data_buttons_frame = tk.Frame(self)

        self.save_button = tk.Button(self.data_buttons_frame,text="Save to file",command=self.saveFile)
        self.clear_button = tk.Button(self.data_buttons_frame, text="Clear data",command=self.clearData)
        self.save_button.grid(row=0, column=0, padx=10)
        self.clear_button.grid(row=0, column=1, padx=10)

        for i in range(3):
            self.data_buffers.append([])  # Data buffers for each lines object in EmbeddedFigure.

        self.grav_plot.grid(row=1,column=0,padx=10,pady=10)
        self.server_buttons_frame.grid(row=0, column=0, padx=10)
        self.text_area.grid(row=2,column=0,pady=10,padx=10,sticky="W")
        self.data_buttons_frame.grid(row=3,column=0,pady=10,padx=10)

    def handleRunServer(self):
        server_object = self.parent.parent.server
        server_object.runServer()
        self.parent.serial_config.console.println(f"Successfully connected to: {server_object.address}",
                                                  headline="TCP: ", msg_type="TCP")

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
        server_object = self.parent.parent.server
        server_object.closeServer()
        # server_object.server_thread.join()
        self.start_server_button.configure(state="normal")
        self.close_server_button.configure(state="disabled")
        self.address_var.set("")
        self.parent.serial_config.console.println("Connection to server closed.",headline="TCP: ",msg_type="TCP")

    def resetDataBuffers(self):
        self.parent.parent.data_queue = queue.Queue()
        self.parent.parent.server.data_queue = self.parent.parent.data_queue
        size_ = len(self.data_buffers)
        self.data_buffers = []
        for i in range(size_):
            self.data_buffers.append([])

    def updateData(self):

        data_queue = self.parent.parent.data_queue

        if not data_queue.empty():
            message_string = data_queue.get()
            values = [float(val) for val in message_string.split(";")]

            for index, buffer in enumerate(self.data_buffers):

                if len(buffer) >= 100:
                    temp = list(np.roll(buffer,-1))
                    temp[-1] = values[index]
                    self.data_buffers[index] = temp
                else:
                    buffer.append(values[index])
            with open("temp/data.temp","a") as file:
                file.write(message_string)
            data_queue.task_done()

        if all(self.data_buffers):  # If data buffers are not empty, plot.

            for line,buffer in zip(self.grav_plot.lines,self.data_buffers):
                self.grav_plot.plot(line,np.arange(0,len(buffer)),buffer)

        else:
            self.grav_plot.resetPlot()

    def clearData(self):
        if messagebox.askyesno(title="Clinostat control system",message="Are you sure you want to clear all data?"):
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("temp/data.temp","a"):
                    pass
            self.resetDataBuffers()
            self.updateData()
        else:
            pass

    def saveFile(self):
        if all(self.data_buffers):
            date = datetime.now()
            date = str(date).replace(".","-").replace(" ","-").replace(":","-")
            filename = filedialog.asksaveasfilename(initialdir="/", title="Save file",defaultextension='.csv',
                                                    initialfile=f"{date}",
                                                    filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
            try:
                copyfile("temp/data.temp",filename)
            except FileNotFoundError:
                pass
        else:
            self.parent.serial_config.console.println("No data to save.",headline="ERROR: ",msg_type="ERROR")


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


class App(themed_tk.ThemedTk):
    def __init__(self):
        themed_tk.ThemedTk.__init__(self)
        self.device = None

        if "saved data" not in os.listdir("."):
            os.mkdir("saved data")

        if "temp" not in os.listdir("."):
            os.mkdir("temp")
        else:
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("data.temp","a"):
                    pass

        with open("config.yaml","r") as file:
            config = yaml.load(file,Loader=yaml.FullLoader)

        self.lock = threading.Lock()
        self.data_queue = queue.Queue()
        self.kill_server = threading.Event()
        self.server = data_socket.DataServer(parent=self, queue_=self.data_queue,
                                             address=config["IP"], port=config["PORT"],
                                             thread_lock=self.lock)
        self.control_system = ClinostatControlSystem(self)
        self.control_system.pack(side="top", fill="both", expand=True)
        self.server.linkConsole(self.control_system.serial_config.console)

    def destroy(self):
        if self.server.running:
            self.server.closeServer()

        if self.device:
            self.device.close_serial()

        tk.Tk.destroy(self)

    def programLoop(self):

        if self.control_system.data_embed.plotting_flag and not self.data_queue.empty():
            self.control_system.data_embed.updateData()

        self.after(100,self.programLoop)


if __name__ == "__main__":
    root = App()
    root.title("Clinostat control system")
    root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
