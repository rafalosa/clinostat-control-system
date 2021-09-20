import tkinter as tk
from tkinter import filedialog, messagebox, Grid
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
import custom_tk_widgets as cw
import tkinter.ttk as ttk
from scipy import fft
from functools import partial


# todo: Maybe add terminal emulator to the data tab for easy access for the ssh to chamber computer.
# todo: Add time shift maps to data tab.
# todo: Rewrite most of the program to avoid re verse calls like self.parent.master.parent.device.pause.
# todo: Add chamber environment control and monitoring (scheduling water pumps, lighting settings, temperature monitor)
# The above is due to the change in the program architecture which wasn't planned in this form in the beginning.

class SerialConfig(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
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
        self.refresh_button = tk.Button(self.port_menu_frame, command=self.refreshPorts, text="Refresh ports")
        self.refresh_button.config(width=17)
        self.port_menu.config(width=15)
        self.port_label.grid(row=0, column=0)
        self.port_menu.grid(row=1, column=0, pady=2)
        self.refresh_button.grid(row=2, column=0, pady=2)

        self.connections_frame = tk.Frame(self)
        self.connect_button = tk.Button(self.connections_frame, command=lambda: threading.Thread(
            target=self.connectToPort).start(), text="Connect")
        self.connect_button.config(width=17)
        self.disconnect_button = tk.Button(self.connections_frame, command=self.disconnectPort, text="Disconnect")
        self.disconnect_button.config(width=17)
        self.disconnect_button.configure(state="disabled")
        self.connect_button.grid(row=0, column=0, pady=2)
        self.disconnect_button.grid(row=1, column=0, pady=2)

        self.console = cw.Console(self, font=("normal", 8))
        self.console.configure(width=65, height=30)

        self.port_menu_frame.grid(row=0, column=0, padx=10, sticky="n")
        self.connections_frame.grid(row=1, column=0, padx=10, sticky="s")
        self.console.grid(row=0, column=1, rowspan=2)

    def refreshPorts(self) -> None:

        self.available_ports = clinostat_com.getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_menu['menu'].delete(0, "end")
        for port in self.available_ports:
            self.port_menu['menu'].add_command(label=port, command=tk._setit(self.port_option_var, port))
        self.console.println("Updated available serial ports.",headline="SERIAL: ",msg_type="MESSAGE")

    def connectToPort(self) -> None:

        self.connect_button.configure(state="disabled")
        if self.parent.master.parent.device is not None:
            self.parent.master.parent.device.close_serial()

        potential_port = self.port_option_var.get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.", headline="ERROR: ", msg_type="ERROR")
            self.connect_button.configure(state="normal")
        else:
            if clinostat_com.tryConnection(potential_port):
                self.parent.master.parent.device = clinostat_com.Clinostat(potential_port)
                self.parent.master.parent.device.port_name = potential_port
                self.console.println("Succesfully connected to {}.".format(potential_port), headline="STATUS: ")
                self.parent.master.parent.device.linkConsole(self.console)
                self.disconnect_button.configure(state="normal")
                self.connect_button.configure(state="disabled")
                self.parent.master.enableStart()

            else:
                self.console.println("Connection to serial port failed.", headline="ERROR: ", msg_type="ERROR")
                self.connect_button.configure(state="normal")

    def disconnectPort(self) -> None:

        self.parent.master.parent.device.close_serial()
        self.console.println("Succesfully disconnected from {}.".format(self.parent.master.parent.device.port_name),
                             headline="STATUS: ")
        self.parent.master.parent.device = None
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.parent.master.disableAllModes()


class ModeMenu(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.button_frame = tk.Frame(self)

        self.indicators_frame = tk.Frame(self)
        self.RPMindicator1 = cw.SlidingIndicator(self.indicators_frame, label="1st DOF\nspeed")
        self.RPMindicator2 = cw.SlidingIndicator(self.indicators_frame, label="2nd DOF\nspeed")
        # self.ACCELindicator1 = cw.SlidingIndicator(self.indicators_frame, label="1st DOF\nacceleration", unit="RPM/s")
        # self.ACCELindicator2 = cw.SlidingIndicator(self.indicators_frame, label="2nd DOF\nacceleration", unit="RPM/s")
        self.RPMindicator1.grid(row=0, column=0, padx=30)
        self.RPMindicator2.grid(row=0, column=1, padx=30)
        # self.ACCELindicator1.grid(row=0, column=2, padx=15)
        # self.ACCELindicator2.grid(row=0, column=3, padx=15)
        self.indicators = [self.RPMindicator1, self.RPMindicator2]  # ,self.ACCELindicator1,self.ACCELindicator2]

        self.abort_button = tk.Button(self.button_frame, command=self.handleAbort, text="Abort")
        self.abort_button.config(width=17, background="#bf4032", activebackground="#eb7063",
                                 foreground="white", disabledforeground="#d1d1d1")
        self.abort_button.config(state="disabled")

        self.run_button = tk.Button(self.button_frame, command=self.handleRun, text="Run")
        self.run_button.config(width=17)
        self.run_button.config(state="disabled")

        self.pause_button = tk.Button(self.button_frame, command=self.handlePause, text="Pause")
        self.pause_button.config(width=17)
        self.pause_button.config(state="disabled")

        self.resume_button = tk.Button(self.button_frame, command=self.handleResume, text="Resume")
        self.resume_button.config(width=17)
        self.resume_button.config(state="disabled")

        self.home_button = tk.Button(self.button_frame, command=self.handleHome, text="Home")
        self.home_button.config(width=17)
        self.home_button.config(state="disabled")

        self.echo_button = tk.Button(self.button_frame, command=self.handleEcho, text="Echo")
        self.echo_button.config(width=17)
        self.echo_button.config(state="disabled")

        self.abort_button.grid(row=0, column=0, pady=6)
        self.run_button.grid(row=1, column=0, pady=6)
        self.pause_button.grid(row=2, column=0, pady=6)
        self.resume_button.grid(row=3, column=0, pady=6)
        self.home_button.grid(row=4, column=0, pady=6)
        self.echo_button.grid(row=5, column=0, pady=6)
        self.button_frame.grid(row=0, column=0, padx=10)
        self.indicators_frame.grid(row=0, column=1, padx=30, rowspan=5, sticky="NE")

        for indicator in self.indicators:
            indicator.configureState(state="disabled")

    def readIndicatorValues(self):
        return (indicator.getValue() for indicator in self.indicators)

    def handleAbort(self):
        self.disableButtons()
        func = partial(self.parent.master.parent.device.abort, self.enableRun)
        threading.Thread(target=func).start()

    def handleRun(self):
        self.disableButtons()
        self.parent.master.blockIndicators()
        func = partial(self.parent.master.parent.device.run, self.readIndicatorValues(), self.enableStop)
        threading.Thread(target=func).start()

    def handleEcho(self):
        self.parent.master.parent.device.echo()

    def handlePause(self):
        self.disableButtons()
        func = partial(self.parent.master.parent.device.pause, self.enableResume)
        threading.Thread(target=func).start()

    def handleResume(self):
        self.resume_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        self.echo_button.configure(state="normal")
        self.disableIndicators()
        self.parent.master.parent.device.resume()

    def handleHome(self):
        self.parent.master.parent.device.home()

    def disableButtons(self):
        self.parent.master.serial_config.disconnect_button.configure(state="disabled")
        self.abort_button.config(state="disabled")
        self.run_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.echo_button.config(state="disabled")
        self.home_button.config(state="disabled")

    def enableStop(self):
        self.parent.master.serial_config.disconnect_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.echo_button.configure(state="normal")

    def enableRun(self):
        self.run_button.config(state="normal")
        self.home_button.config(state="normal")
        self.echo_button.config(state="normal")
        self.parent.master.serial_config.disconnect_button.configure(state="normal")
        for indicator in self.indicators:
            indicator.configureState(state="normal")

    def enableResume(self):
        self.parent.master.serial_config.disconnect_button.configure(state="normal")
        self.resume_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.abort_button.configure(state="normal")
        self.echo_button.configure(state="normal")

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
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.data_buffers = []
        self.plotting_flag = False
        self.new_data_available = False

        self.server_buttons_frame = tk.Frame(self)

        self.desc_var = tk.StringVar()
        self.desc_var.set("TCP data server:")
        self.server_label = tk.Label(self.server_buttons_frame, textvariable=self.desc_var)
        self.server_label.grid(row=0, column=0, columnspan=2)

        self.start_server_button = tk.Button(self.server_buttons_frame,
                                             text="Start server", command=self.handleRunServer)
        self.start_server_button.grid(row=1, column=0, pady=2, padx=5)
        self.start_server_button.configure(width=17)

        self.close_server_button = tk.Button(self.server_buttons_frame,
                                             text="Close server", command=self.handleCloseServer)
        self.close_server_button.grid(row=1, column=1, pady=2, padx=5)
        self.close_server_button.configure(width=17)
        self.close_server_button.configure(state="disabled")

        self.address_var = tk.StringVar()
        self.entry = tk.Entry(self.server_buttons_frame, textvariable=self.address_var)
        self.entry.config(width=20, state="disabled")
        self.entry.configure(disabledbackground="white", disabledforeground="black")

        self.address_label_var = tk.StringVar()
        self.address_label_var.set("Current server address:")

        self.address_label = tk.Label(self.server_buttons_frame, textvariable=self.address_label_var)
        self.address_label.grid(row=2, column=0)
        self.entry.grid(row=2, column=1)

        self.console = cw.Console(self,width=50,height=15,font=("normal", 8))

        plt.rcParams['figure.facecolor'] = "#f0f0f0"
        plt.rcParams['font.size'] = 7
        plt.rcParams["lines.linewidth"] = 0.5
        plt.rcParams["figure.subplot.top"] = 0.85
        plt.rcParams["figure.subplot.bottom"] = 0.15
        plt.rcParams["figure.subplot.left"] = 0.17

        self.gravity_plots = ttk.Notebook(self)
        self.fourier = ttk.Notebook(self)
        self.time_shift = ttk.Notebook(self)
        #self.gravity_vector = ttk.Notebook(self)

        self.grav_axes = []
        plot_descriptions = ["Gravity vector", "Mean gravity"]

        for i in range(len(plot_descriptions)):
            plot = cw.EmbeddedFigure(self.gravity_plots, figsize=(3.5, 2.5), maxrecords=600)
            plot.addLinesObject()
            plot.addLinesObject()
            self.grav_axes.append(plot)
            self.gravity_plots.add(plot, text=plot_descriptions[i])
            for _ in range(3):
                self.data_buffers.append([])  # Data buffers for each lines object in EmbeddedFigure.

        for ax in self.grav_axes:
            ax.legend(["X","Y","Z"],bbox_to_anchor=(0,1.02,1,.102),loc=3,ncol=3)
            ax.xlabel("Time elapsed (s)")
            ax.ylabel("Gravitational acceleration (G)")

        # self.gravity_vector_plot = cw.EmbeddedFigure(self.gravity_plots, figsize=(3, 3), maxrecords=600, spatial=True)
        # self.gravity_plots.add(self.gravity_vector_plot,text="Gravity vector orientation")

        self.data_buttons_frame = tk.Frame(self)

        self.fourier_plot = cw.EmbeddedFigure(self.fourier, figsize=(3.5, 2.5), maxrecords=600)
        self.fourier_plot.addLinesObject()
        self.fourier_plot.addLinesObject()
        self.fourier_plot.xlabel("Frequency (Hz)")
        self.fourier_plot.ylabel("Intensity")
        self.fourier.add(self.fourier_plot, text="FFT of gravity vector")
        self.fourier_plot.legend(["FFT(X)", "FFT(Y)", "FFT(Z)"],bbox_to_anchor=(0,1.02,1,.102),loc=3,ncol=3)

        self.time_shift_plot = cw.EmbeddedFigure(self.time_shift,figsize=(3.5, 2.5), maxrecords=600)
        self.time_shift.add(self.time_shift_plot,text="Time shift map of gravity vector")

        # self.gravity_vector.add(self.gravity_vector_plot,text="Gravity vector orientation")

        self.save_button = tk.Button(self.server_buttons_frame, text="Save to CSV", command=self.saveFile, width=17)
        self.clear_button = tk.Button(self.server_buttons_frame, text="Clear data", command=self.clearData, width=17)
        self.save_button.grid(row=1, column=2, padx=10)
        self.clear_button.grid(row=1, column=3, padx=10)

        self.server_buttons_frame.grid(row=0, column=0, padx=10,pady=10,columnspan = 2)
        self.console.grid(row=1, column=0, padx=10,pady=10)
        self.gravity_plots.grid(row=2, column=0, padx=10, pady=10)
        self.fourier.grid(row=1, column=1, padx=10, pady=10)
        self.time_shift.grid(row=2, column=1, padx=10, pady=10)
        #self.gravity_vector.grid(row=3, column=1, padx=10, pady=10)
        self.data_buttons_frame.grid(row=3, column=0, pady=10, padx=10)

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
        server_object = self.parent.parent.server
        server_object.closeServer()
        self.start_server_button.configure(state="normal")
        self.close_server_button.configure(state="disabled")
        self.address_var.set("")
        self.parent.parent.server.console.println("Connection to server closed.", headline="TCP: ", msg_type="TCP")

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
            print(message_string)
            #self.gravity_vector_plot.plot()

            for index, buffer in enumerate(self.data_buffers):

                if len(buffer) >= 600:
                    temp = list(np.roll(buffer, -1))
                    temp[-1] = values[index]
                    self.data_buffers[index] = temp
                    if index <= 2:
                        N = len(self.data_buffers[index])
                        frt = fft.fft(self.data_buffers[index])
                        fr_domain = fft.fftfreq(N, 10)[:N // 2]
                        self.fourier_plot.plot(self.fourier_plot.lines[index], fr_domain,
                                               np.abs(frt[:N // 2]), tracking=False)
                        # todo: Crop fourier domain to the maximum detected frequency, ex. half of the sampling freq.
                else:
                    buffer.append(values[index])
            with open("temp/data.temp", "a") as file:
                file.write(message_string)
            data_queue.task_done()

        if all(self.data_buffers):  # If data buffers are not empty, plot.

            for plot_ind, plot in enumerate(self.grav_axes):
                for line, buffer in zip(plot.lines, self.data_buffers[3 * plot_ind:3 * plot_ind + 3]):
                    plot.plot(line, np.arange(0, len(buffer)), buffer)

        else:
            self.fourier_plot.resetPlot()
            for plot in self.grav_axes:
                plot.resetPlot()

    def clearData(self):
        if messagebox.askyesno(title="Clinostat control system", message="Are you sure you want to clear all data?"):
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("temp/data.temp", "a"):
                    pass
            self.resetDataBuffers()
            self.updateData()
        else:
            pass

    def saveFile(self):
        if all(self.data_buffers):
            date = datetime.now()
            date = str(date).replace(".", "-").replace(" ", "-").replace(":", "-")
            filename = filedialog.asksaveasfilename(initialdir="/", title="Save file", defaultextension='.csv',
                                                    initialfile=f"{date}",
                                                    filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
            try:
                copyfile("temp/data.temp", filename)
            except FileNotFoundError:
                pass
        else:
            self.parent.parent.server.console.println("No data to save.", headline="ERROR: ", msg_type="ERROR")


class ClinostatControlSystem(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.main_tabs = ttk.Notebook(self)

        self.motors_tab = tk.Frame(self)
        self.serial_config = SerialConfig(self.motors_tab)
        self.mode_options = ModeMenu(self.motors_tab)

        self.serial_config.grid(row=0, column=0, sticky="nswe",padx=10,pady=20)
        self.mode_options.grid(row=1, column=0, sticky="nswe",padx=10,pady=20)

        self.data_embed = DataEmbed(self)

        self.main_tabs.add(self.motors_tab, text="Clinostat control")
        self.main_tabs.add(self.data_embed, text="Chamber computer")

        Grid.rowconfigure(self, 0, weight=1)
        Grid.columnconfigure(self, 0, weight=1)

        self.main_tabs.grid(row=0,column=0,sticky="nswe")

    def disableAllModes(self):
        self.mode_options.disableButtons()
        self.mode_options.resetIndicators()
        self.mode_options.disableIndicators()

    def blockIndicators(self):
        self.mode_options.disableIndicators()

    def enableStart(self):
        self.mode_options.enableRun()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.device = None

        if "saved data" not in os.listdir("."):
            os.mkdir("saved data")

        if "temp" not in os.listdir("."):
            os.mkdir("temp")
        else:
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("temp/data.temp", "a"):
                    pass

        with open("config.yaml", "r") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

        self.lock = threading.Lock()
        self.data_queue = queue.Queue()
        self.kill_server = threading.Event()
        self.server = data_socket.DataServer(parent=self, queue_=self.data_queue,
                                             address=config["IP"], port=config["PORT"],
                                             thread_lock=self.lock)
        
        self.control_system = ClinostatControlSystem(self)
        Grid.rowconfigure(self, 0, weight=1)
        Grid.columnconfigure(self, 0, weight=1)
        self.control_system.grid(row=0,column=0,sticky="nswe")

        self.server.linkConsole(self.control_system.data_embed.console)

    def destroy(self):
        if self.server.running:
            self.server.closeServer()

        if self.device:
            self.device.close_serial()

        tk.Tk.destroy(self)

    def programLoop(self):

        if self.control_system.data_embed.plotting_flag and not self.data_queue.empty():
            self.control_system.data_embed.updateData()

        self.after(1, self.programLoop)


if __name__ == "__main__":
    root = App()
    root.title("Clinostat control system")
    # root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
