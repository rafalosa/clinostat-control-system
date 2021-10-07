from multiprocessing import Pool
import matplotlib.pyplot as plt
import numpy as np
from modules import clinostat_com, custom_tk_widgets as cw
from datetime import datetime
from shutil import copyfile
from scipy import fft
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
import tkinter as tk
import threading
import queue
import os
from modules.data_socket import ServerStartupError
from modules.custom_thread import SuccessThread


class SerialConfig(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}  # todo: Maybe add a differentiation of passive and active interface.
        self.interface_manager = interface_manager
        self.serial_sensitive_interface = {}
        self.variables = {}

        self.available_ports = clinostat_com.getPorts()

        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.variables["ports"] = tk.StringVar(self)
        self.variables["ports"].set("Select serial port")

        self.port_menu_frame = tk.Frame(self)

        self.port_label = tk.Label(self.port_menu_frame, text="Serial port:")

        self.port_menu = ttk.Combobox(self.port_menu_frame, textvariable=self.variables["ports"],
                                      state="readonly", width=18)
        self.port_menu["values"] = self.available_ports
        self.port_menu.bind("<<ComboboxSelected>>", lambda _: self.port_menu.selection_clear())

        self.interface["refresh"] = tk.Button(self.port_menu_frame, command=self.refreshPorts, text="Refresh ports")

        self.interface["refresh"].config(width=17)

        self.port_label.grid(row=0, column=0)
        self.port_menu.grid(row=1, column=0, pady=2)
        self.interface["refresh"].grid(row=2, column=0, pady=2)

        self.connections_frame = tk.Frame(self)

        self.serial_sensitive_interface["connect"] = self.interface["connect"] = \
            tk.Button(self.connections_frame, command=lambda: threading.Thread(
                target=self.connectToPort).start(), text="Connect", width=17)

        self.serial_sensitive_interface["disconnect"] = self.interface["disconnect"] = \
            tk.Button(self.connections_frame, command=self.disconnectPort,
                      text="Disconnect", width=17, state="disabled")

        self.interface["connect"].grid(row=0, column=0, pady=2)
        self.interface["disconnect"].grid(row=1, column=0, pady=2)

        self.console = self.supervisor.params["serial_console"] = cw.Console(self, font=("normal", 8))
        self.console.configure(width=65, height=30)

        self.port_menu_frame.grid(row=0, column=0, padx=10, sticky="n")
        self.connections_frame.grid(row=1, column=0, padx=10, pady=10, sticky="s")
        self.console.grid(row=0, column=1, rowspan=2, pady=10, padx=10)

    def refreshPorts(self) -> None:

        self.available_ports = clinostat_com.getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_menu["values"] = self.available_ports
        self.variables["ports"].set("Select serial port")
        self.console.println("Updated available serial ports.", headline="SERIAL: ", msg_type="MESSAGE")

    def connectToPort(self) -> None:

        self.interface["connect"].configure(state="disabled")
        if self.supervisor.params["device"] is not None:
            self.supervisor.params["device"].close_serial()  # Not necessary.

        potential_port = self.variables["ports"].get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.", headline="ERROR: ", msg_type="ERROR")
            self.interface["connect"].configure(state="normal")
        else:
            if clinostat_com.Clinostat.tryConnection(potential_port):
                self.supervisor.params["device"] = clinostat_com.Clinostat(potential_port)
                self.supervisor.params["device"].port_name = potential_port
                self.console.println(f"Successfully connected to {potential_port}.", headline="STATUS: ")
                self.supervisor.params["device"].linkConsole(self.console)
                self.interface["disconnect"].configure(state="normal")
                self.interface["connect"].configure(state="disabled")
                self.interface_manager.ui_deviceConnected()

            else:
                self.console.println("Connection to serial port failed.", headline="ERROR: ", msg_type="ERROR")
                self.interface["connect"].configure(state="normal")

    def disconnectPort(self) -> None:

        try:
            self.supervisor.params["device"].close_serial()
        except clinostat_com.ClinostatCommunicationError as ex:
            self.console.println(ex.message, headline="ERROR: ", msg_type="ERROR")
            return
        finally:
            port_name = self.supervisor.params["device"].port_name
            self.supervisor.params["device"] = None
            self.interface["connect"].configure(state="normal")
            self.interface["disconnect"].configure(state="disabled")
            self.interface_manager.ui_modesSuspend()
            self.supervisor.variables["pumping"] = False

        self.console.println(f"Successfully disconnected from {port_name}.", headline="STATUS: ")


class ModeMenu(ttk.LabelFrame):
    button_w = 17
    button_h = 5
    button_pady = 7
    button_padx = 3

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.interface_manager = interface_manager
        self.serial_sensitive_interface = {}
        self.button_frame = tk.Frame(self)

        self.indicators_frame = tk.Frame(self)

        self.interface["speed_slider1"] = cw.SlidingIndicator(master=self.indicators_frame, label="1st DOF\nspeed")
        self.interface["speed_slider2"] = cw.SlidingIndicator(master=self.indicators_frame, label="2nd DOF\nspeed")
        self.interface["speed_slider1"].grid(row=0, column=0, padx=30)
        self.interface["speed_slider2"].grid(row=0, column=1, padx=30)

        self.supervisor.variables["speed1"] = self.interface["speed_slider1"].var
        self.supervisor.variables["speed2"] = self.interface["speed_slider2"].var

        self.linear_indicators = [self.interface["speed_slider1"], self.interface["speed_slider2"]]  # Easier access.

        self.interface["abort"] = tk.Button(self.button_frame, command=self.handleAbort, text="Abort")
        self.interface["abort"].configure(width=ModeMenu.button_w, background="#bf4032", activebackground="#eb7063",
                                          foreground="white", disabledforeground="#d1d1d1", state="disabled")

        self.interface["run"] = tk.Button(self.button_frame, command=self.handleRun, text="Run")
        self.interface["run"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["pause"] = tk.Button(self.button_frame, command=self.handlePause, text="Pause")
        self.interface["pause"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["resume"] = tk.Button(self.button_frame, command=self.handleResume, text="Resume")
        self.interface["resume"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["home"] = tk.Button(self.button_frame, command=self.handleHome, text="Home")
        self.interface["home"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["echo"] = tk.Button(self.button_frame, command=self.handleEcho, text="Echo")
        self.interface["echo"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["abort"].grid(row=0, column=0, pady=ModeMenu.button_pady)
        self.interface["run"].grid(row=1, column=0, pady=ModeMenu.button_pady)
        self.interface["pause"].grid(row=2, column=0, pady=ModeMenu.button_pady)
        self.interface["resume"].grid(row=3, column=0, pady=ModeMenu.button_pady)
        self.interface["home"].grid(row=4, column=0, pady=ModeMenu.button_pady)
        self.interface["echo"].grid(row=5, column=0, pady=ModeMenu.button_pady)

        self.button_frame.grid(row=0, column=0, padx=10)
        self.indicators_frame.grid(row=0, column=1, padx=30, rowspan=5, sticky="NE")

        for indicator in self.linear_indicators:
            indicator.configureState(state="disabled")

        for widget in self.interface:
            if self.interface[widget] not in self.linear_indicators:
                self.serial_sensitive_interface[widget] = self.interface[widget]

    def readIndicatorValues(self):
        return (indicator.getValue() for indicator in self.linear_indicators)

    def handleAbort(self):
        self.interface_manager.ui_abortHandler()
        SuccessThread(target=self.supervisor.params["device"].abort,
                      at_success=self.interface_manager.ui_enableRun,
                      exception_=clinostat_com.ClinostatCommunicationError).start()

    def handleRun(self):
        self.interface_manager.ui_runHandler()
        SuccessThread(target=self.supervisor.params["device"].run, args=(tuple(self.readIndicatorValues()),),
                      at_success=self.interface_manager.ui_enableStop,
                      exception_=clinostat_com.ClinostatCommunicationError).start()

    def handleEcho(self):
        self.supervisor.params["device"].echo()

    def handlePause(self):
        self.interface_manager.ui_pauseHandler()
        SuccessThread(target=self.supervisor.params["device"].pause,
                      at_success=self.interface_manager.ui_enableResume,
                      exception_=clinostat_com.ClinostatCommunicationError).start()

    def handleResume(self):
        self.interface_manager.ui_resumeHandler()
        self.interface_manager.ui_disableSpeedIndicators()
        self.supervisor.params["device"].resume()

    def handleHome(self):
        self.supervisor.params["device"].home()

    def resetIndicators(self):
        for indicator in self.linear_indicators:
            indicator.reset()


class DataEmbed(tk.Frame):

    figsize_ = (5,2.75)

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.variables = {}
        self.plots = {}
        self.interface_manager = interface_manager
        self.data_records_amount = 300

        self.data_buffers = []

        self.server_buttons_frame = ttk.LabelFrame(self, text="Data server connection")
        self.data_save_frame = ttk.LabelFrame(self, text="Save or discard data")

        self.interface["start_server"] = tk.Button(self.server_buttons_frame,
                                                   text="Start server", command=self.handleRunServer)
        self.interface["start_server"].configure(width=20)
        self.interface["start_server"].grid(row=0, column=0, pady=2, padx=30, sticky="w")

        self.interface["close_server"] = tk.Button(self.server_buttons_frame,
                                                   text="Close server", command=self.handleCloseServer)
        self.interface["close_server"].configure(width=20, state="disabled")
        self.interface["close_server"].grid(row=0, column=1, pady=2, padx=30, sticky="e")

        self.address_frame = tk.Frame(self.server_buttons_frame)

        self.variables["address"] = self.supervisor.variables["address"] = tk.StringVar()
        self.interface["address_entry"] = tk.Entry(self.address_frame,
                                                   textvariable=self.supervisor.variables["address"])
        self.server_buttons_frame.rowconfigure(0, weight=1)
        self.server_buttons_frame.columnconfigure(1, weight=1)
        self.server_buttons_frame.columnconfigure(0, weight=1)
        self.interface["address_entry"].config(width=20, state="disabled")
        self.interface["address_entry"].configure(disabledbackground="white", disabledforeground="black")

        self.address_label = tk.Label(self.address_frame, text="Current server address:")
        self.address_label.grid(row=0, column=0)
        self.interface["address_entry"].grid(row=0, column=1)
        self.address_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.console = self.interface_manager.outputs["server"] = cw.Console(self,
                                                                             width=50, height=15, font=("normal", 8))

        plt.rcParams['figure.facecolor'] = "#f0f0f0"
        plt.rcParams['font.size'] = 7
        plt.rcParams["lines.linewidth"] = 0.5
        plt.rcParams["figure.subplot.top"] = 0.85
        plt.rcParams["figure.subplot.bottom"] = 0.15
        plt.rcParams["figure.subplot.left"] = 0.17

        self.gravity_plots = ttk.Notebook(self)
        self.fourier = ttk.Notebook(self)
        self.time_shift = ttk.Notebook(self)

        self.grav_axes = []
        plot_descriptions = ["Gravity vector", "Mean gravity"]
        plot_keys = ["grav_components", "grav_means"]

        for i in range(len(plot_descriptions)):
            self.plots[plot_keys[i]] = cw.EmbeddedFigure(master=self.gravity_plots,
                                                         figsize=DataEmbed.figsize_, maxrecords=300)
            self.plots[plot_keys[i]].addLinesObject()
            self.plots[plot_keys[i]].addLinesObject()
            self.grav_axes.append(self.plots[plot_keys[i]])
            self.gravity_plots.add(self.plots[plot_keys[i]], text=plot_descriptions[i])

        for ax in self.grav_axes:
            ax.legend(["X", "Y", "Z"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
            ax.xlabel("Time elapsed (s)")
            ax.ylabel("Gravitational acceleration (G)")

        self.fourier_plot = cw.EmbeddedFigure(master=self.fourier, figsize=DataEmbed.figsize_, maxrecords=300)
        self.fourier_plot.addLinesObject()
        self.fourier_plot.addLinesObject()
        self.fourier_plot.xlabel("Frequency (Hz)")
        self.fourier_plot.ylabel("Intensity")
        self.fourier.add(self.fourier_plot, text="FFT of gravity vector")
        self.fourier_plot.legend(["FFT(X)", "FFT(Y)", "FFT(Z)"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)

        self.time_shift_plot = cw.EmbeddedFigure(master=self.time_shift, figsize=DataEmbed.figsize_, maxrecords=600)
        self.time_shift.add(self.time_shift_plot, text="Time shift map of gravity vector")

        self.data_save_frame.rowconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(1, weight=1)

        self.interface["save"] = tk.Button(self.data_save_frame, text="Save to CSV", command=self.saveFile, width=17)
        self.interface["clear"] = tk.Button(self.data_save_frame, text="Clear data", command=self.clearData, width=17)
        self.interface["save"].grid(row=0, column=0, padx=10)
        self.interface["clear"].grid(row=0, column=1, padx=10)

        # todo: Setup temperature and humidity plots.

        self.server_buttons_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nwe")
        self.data_save_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nwse")
        self.console.grid(row=1, column=0, padx=10, pady=10, sticky="nswe")
        self.gravity_plots.grid(row=2, column=0, padx=10, pady=10, sticky="sw")
        self.fourier.grid(row=1, column=1, padx=10, pady=10, sticky="ne")
        self.time_shift.grid(row=2, column=1, padx=10, pady=10, sticky="se")

    def handleRunServer(self):
        server = self.supervisor.params["server"]
        try:
            server.runServer()
        except ServerStartupError:
            return

        self.console.println(f"Successfully connected to: {server.address}", headline="TCP: ", msg_type="TCP")
        self.interface_manager.ui_serverEnable()
        self.supervisor.variables["address"].set(server.address + ":" + str(server.port))
        self.supervisor.flags["plotting"] = True

    def handleCloseServer(self):
        self.interface_manager.ui_serverDisable()
        self.supervisor.flags["plotting"] = False
        self.supervisor.params["server"].closeServer()
        self.supervisor.variables["address"].set("")

    def resetDataBuffers(self):
        self.supervisor.clearQueues()
        self.supervisor.resetDataBuffers()

    def updateData(self):

        data_queue = self.supervisor.get_queue

        if not data_queue.empty():
            self.supervisor.flags["new_data_present"] = True
            message_string = data_queue.get()
            values = [float(val) for val in message_string.split(";")]
            index = 0
            for key in self.supervisor.data_buffers:

                for i, buffer in enumerate(self.supervisor.data_buffers[key]):

                    if len(buffer) >= self.data_records_amount:
                        temp = list(np.roll(buffer, -1))
                        temp[-1] = values[index]
                        self.supervisor.data_buffers[key][i] = temp

                    else:
                        buffer.append(values[index])
                    index += 1

            with open("temp/data.temp", "a") as file:
                file.write(message_string)
            data_queue.task_done()
        else:
            self.supervisor.flags["new_data_present"] = False

        if self.supervisor.flags["new_data_present"]:  # If data buffers are not empty, plot.

            # Update plots only if data tab is active.
            if self.interface_manager.index(self.interface_manager.select()) == 1:
                keys = ["grav_components", "grav_means"]
                for plot_ind, plot in enumerate(self.grav_axes):
                    for line, buffer in zip(plot.lines, self.supervisor.data_buffers[keys[plot_ind]]):
                        plot.plot(line, np.arange(0, len(buffer)), buffer)

                if len(self.supervisor.data_buffers["grav_components"][0]) >= self.data_records_amount:
                    pool = Pool(processes=3)
                    result = pool.imap(fft.fft, self.supervisor.data_buffers["grav_components"])
                    pool.close()
                    pool.join()
                    calculated_ffts = [fft_ for fft_ in result]
                    for index, buffer in enumerate(calculated_ffts):
                        N = len(self.supervisor.data_buffers["grav_components"][index])
                        frt = fft.fft(self.supervisor.data_buffers["grav_components"][index])
                        fr_domain = fft.fftfreq(N, 10)[:N // 2]
                        self.fourier_plot.plot(self.fourier_plot.lines[index], fr_domain,
                                               np.abs(frt[:N // 2]), tracking=False)

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
        if self.supervisor.data_buffers["grav_components"][0]:
            date = datetime.now()
            date = str(date).replace(".", "-").replace(" ", "-").replace(":", "-")
            try:
                filename = filedialog.asksaveasfilename(initialdir="/", title="Save file", defaultextension='.csv',
                                                        initialfile=f"{date}",
                                                        filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
            except TypeError:
                return
            try:
                copyfile("temp/data.temp", filename)
            except FileNotFoundError:
                pass
        else:
            self.console.println("No data to save.", headline="ERROR: ", msg_type="ERROR")


class PumpControl(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.interface_manager = interface_manager
        self.serial_sensitive_interface = {}
        self.variables = {}
        self.device = supervisor.params["device"]

        self.interface["water_slider1"] = cw.SlidingIndicator(master=self, label="Watering volume", unit="ml",
                                                              orientation="horizontal", from_=0, to=250, res=10,
                                                              length=300, width=30, entry_pos="right")

        self.interface["time_slider1"] = cw.SlidingIndicator(master=self, label="Watering time interval", unit="min",
                                                             orientation="horizontal", from_=0, to=240, res=5,
                                                             length=300, width=30, entry_pos="right")

        self.supervisor.variables["water1"] = self.interface["water_slider1"].var
        self.supervisor.variables["time1"] = self.interface["time_slider1"].var

        self.interface["water_slider1"].configureState(state="disabled")
        self.interface["time_slider1"].configureState(state="disabled")

        self.times_frame = tk.Frame(self)

        self.interface["time_label"] = tk.Label(self.times_frame, text="Time till next watering cycle:")

        self.variables["time_left"] = self.supervisor.variables["time_left_str"] = tk.StringVar()
        self.variables["time_left"].set("00:00")
        self.interface["time_entry1"] = tk.Entry(self.times_frame, textvariable=self.variables["time_left"])
        self.interface["time_entry1"].configure(width=9, state="disabled", disabledbackground="white",
                                                disabledforeground="black", justify="center")

        self.interface["time_label"].grid(row=0, column=0)
        self.interface["time_entry1"].grid(row=0, column=1)

        self.buttons_frame = tk.Frame(self)

        self.interface["start"] = self.serial_sensitive_interface["start"] = \
            tk.Button(self.buttons_frame, text="Start cycle", command=self.startWateringCycle)
        self.interface["start"].configure(state="disabled", width=8)

        self.interface["stop"] = self.serial_sensitive_interface["stop"] =  \
            tk.Button(self.buttons_frame, text="Stop cycle", command=self.stopWateringCycle)
        self.interface["stop"].configure(state="disabled", width=8)

        self.interface["force"] = self.serial_sensitive_interface["force"] = \
            tk.Button(self.buttons_frame, text="Force cycle", command=self.forceWateringCycle)
        self.interface["force"].configure(state="disabled", width=8)

        self.interface["start"].grid(row=0, column=0, padx=10, pady=10)
        self.interface["stop"].grid(row=0, column=1, padx=10, pady=10)
        self.interface["force"].grid(row=0, column=2, padx=10, pady=10)

        self.interface["water_slider1"].grid(row=0, column=0, padx=10, pady=10)
        self.interface["time_slider1"].grid(row=1, column=0, padx=10, pady=10)

        self.times_frame.grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.buttons_frame.grid(row=3, column=0, padx=10, pady=10)

    def startWateringCycle(self):
        if self.interface["water_slider1"].getValue() > 0 and self.interface["time_slider1"].getValue() > 0:
            self.supervisor.flags["pumping"] = True
            self.interface_manager.ui_wateringStarted()

        else:
            self.interface_manager.outputs["serial"].println("Time and water volume values"
                                                             " have to be greater than 0.",
                                                             headline="ERROR: ", msg_type="ERROR")

    def stopWateringCycle(self):
        self.supervisor.flags["pumping"] = False
        self.variables["time_left"].set("00:00")
        self.interface_manager.ui_wateringStopped()

    def forceWateringCycle(self):
        self.interface_manager.ui_serialSuspend()

        SuccessThread(target=self.supervisor.params["device"].dumpWater,
                      at_success=self.interface_manager.ui_serialBreakSuspend,
                      exception_=clinostat_com.ClinostatCommunicationError,
                      args=(self.interface["water_slider1"].getValue(),)).start()


class LightControl(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.interface_manager = interface_manager

        self.intensity_slider = cw.SlidingIndicator(master=self, label="Intensity", unit="%  ",
                                                    orientation="horizontal",
                                                    from_=0, to=100, res=1, length=300, width=30, entry_pos="right",
                                                    opt=self.updateValueContainer)
        self.intensity_slider.grid(row=0, column=0, sticky="ne", padx=10, pady=10)
        self.intensity_slider.configureState(state="disabled")

        self.intensity_queue = self.supervisor.put_queue
        self.intensity_queue.put(50)

    def updateValueContainer(self):
        self.intensity_queue.put(self.intensity_slider.getValue())


if __name__ == "__main__":
    app = tk.Tk()
    app.title("widget test")
    app.mainloop()
