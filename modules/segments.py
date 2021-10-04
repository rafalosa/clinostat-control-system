from multiprocessing import Pool
import matplotlib.pyplot as plt
import numpy as np
from modules import clinostat_com, custom_tk_widgets as cw
from datetime import datetime
from shutil import copyfile
from scipy import fft
from functools import partial
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
import tkinter as tk
import threading
import queue
import os


class SerialConfig(ttk.LabelFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_ports = clinostat_com.getPorts()

        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_option_var = tk.StringVar(self)
        self.port_option_var.set("Select serial port")

        self.port_description = tk.StringVar()
        self.port_description.set("Select serial port:")

        self.port_menu_frame = tk.Frame(self)
        self.port_label = tk.Label(self.port_menu_frame, textvariable=self.port_description)
        self.port_menu = ttk.Combobox(self.port_menu_frame, textvariable=self.port_option_var, state="readonly")
        self.port_menu["values"] = self.available_ports
        self.port_menu.bind("<<ComboboxSelected>>", lambda x: self.port_menu.selection_clear())
        self.refresh_button = tk.Button(self.port_menu_frame, command=self.refreshPorts, text="Refresh ports")
        self.refresh_button.config(width=17)
        self.port_menu.config(width=18)
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

        self.master.master.serial_buttons.append(self.connect_button)
        self.master.master.serial_buttons.append(self.disconnect_button)

    def refreshPorts(self) -> None:

        self.available_ports = clinostat_com.getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        # self.port_menu['menu'].delete(0, "end")
        # for port in self.available_ports:
        #     self.port_menu['menu'].add_command(label=port, command=tk._setit(self.port_option_var, port))
        self.port_menu["values"] = self.available_ports
        self.port_option_var.set("Select serial port")
        self.port_description.set("Select serial port:")
        self.console.println("Updated available serial ports.", headline="SERIAL: ", msg_type="MESSAGE")

    def connectToPort(self) -> None:

        self.connect_button.configure(state="disabled")
        if self.master.master.master.device is not None:
            self.master.master.master.device.close_serial()

        potential_port = self.port_option_var.get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.", headline="ERROR: ", msg_type="ERROR")
            self.connect_button.configure(state="normal")
        else:
            if clinostat_com.Clinostat.tryConnection(potential_port):
                self.master.master.master.device = clinostat_com.Clinostat(potential_port)
                self.master.master.master.device.port_name = potential_port
                self.console.println(f"Successfully connected to {potential_port}.", headline="STATUS: ")
                self.master.master.master.device.linkConsole(self.console)
                self.disconnect_button.configure(state="normal")
                self.connect_button.configure(state="disabled")
                self.master.master.enableStart()

            else:
                self.console.println("Connection to serial port failed.", headline="ERROR: ", msg_type="ERROR")
                self.connect_button.configure(state="normal")

    def disconnectPort(self) -> None:

        try:
            self.master.master.master.device.close_serial()
        except clinostat_com.ClinostatCommunicationError as ex:
            self.console.println(ex.message, headline="ERROR: ", msg_type="ERROR")
            return
        finally:
            port_name = self.master.master.master.device.port_name
            self.master.master.master.device = None
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")
            self.master.master.disableAllModes()
            self.master.master.pump_control.cycle_active = False

        self.console.println(f"Successfully disconnected from {port_name}.",
                             headline="STATUS: ")

class ModeMenu(ttk.LabelFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_frame = tk.Frame(self)

        self.indicators_frame = tk.Frame(self)
        self.RPMindicator1 = cw.SlidingIndicator(master=self.indicators_frame, label="1st DOF\nspeed")
        self.RPMindicator2 = cw.SlidingIndicator(master=self.indicators_frame, label="2nd DOF\nspeed")
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

        self.master.master.serial_buttons.append(self.abort_button)
        self.master.master.serial_buttons.append(self.run_button)
        self.master.master.serial_buttons.append(self.pause_button)
        self.master.master.serial_buttons.append(self.resume_button)
        self.master.master.serial_buttons.append(self.home_button)
        self.master.master.serial_buttons.append(self.echo_button)

    def readIndicatorValues(self):
        return (indicator.getValue() for indicator in self.indicators)

    def handleAbort(self):
        self.disableButtons()
        func = partial(self.master.master.master.device.abort, self.enableRun)
        threading.Thread(target=func).start()

    def handleRun(self):
        self.disableButtons()
        self.master.master.blockIndicators()
        self.master.master.suspendSerialUI()
        func = partial(self.master.master.master.device.run, self.readIndicatorValues(), self.enableStop)
        threading.Thread(target=func).start()

    def handleEcho(self):
        self.master.master.master.device.echo()

    def handlePause(self):
        self.disableButtons()
        self.master.master.suspendSerialUI()
        func = partial(self.master.master.master.device.pause, self.enableResume)
        threading.Thread(target=func).start()

    def handleResume(self):
        self.resume_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        self.echo_button.configure(state="normal")
        self.disableIndicators()
        self.master.master.master.device.resume()

    def handleHome(self):
        self.master.master.master.device.home()

    def disableButtons(self):
        self.master.master.serial_config.disconnect_button.configure(state="disabled")
        self.abort_button.config(state="disabled")
        self.run_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.echo_button.config(state="disabled")
        self.home_button.config(state="disabled")

    def enableStop(self):
        self.master.master.breakSuspendSerialUI()
        self.master.master.serial_config.disconnect_button.configure(state="normal")
        self.abort_button.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.echo_button.configure(state="normal")

    def enableRun(self):
        self.run_button.config(state="normal")
        self.home_button.config(state="normal")
        self.echo_button.config(state="normal")
        self.master.master.serial_config.disconnect_button.configure(state="normal")
        for indicator in self.indicators:
            indicator.configureState(state="normal")

    def enableResume(self):
        self.master.master.breakSuspendSerialUI()
        self.master.master.serial_config.disconnect_button.configure(state="normal")
        self.resume_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.abort_button.configure(state="normal")
        self.echo_button.configure(state="normal")

    def disableIndicators(self):
        for indicator in self.indicators:
            indicator.configureState(state="disabled")

    def resetIndicators(self):
        for indicator in self.indicators:
            indicator.reset()

class DataEmbed(tk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.data_records_amount = 300

        self.data_buffers = []
        self.plotting_flag = False
        self.new_data_available = False

        self.server_buttons_frame = ttk.LabelFrame(self, text="Data server connection")
        self.data_save_frame = ttk.LabelFrame(self, text="Save or discard data")

        self.start_server_button = tk.Button(self.server_buttons_frame,
                                             text="Start server", command=self.handleRunServer)
        self.start_server_button.grid(row=0, column=0, pady=2, padx=5)
        self.start_server_button.configure(width=20)

        self.close_server_button = tk.Button(self.server_buttons_frame,
                                             text="Close server", command=self.handleCloseServer)
        self.close_server_button.grid(row=0, column=1, pady=2, padx=5)
        self.close_server_button.configure(width=20, state="disabled")

        self.address_frame = tk.Frame(self.server_buttons_frame)

        self.address_label_var = tk.StringVar()
        self.address_label_var.set("Current server address:")
        self.address_var = tk.StringVar()
        self.entry = tk.Entry(self.address_frame, textvariable=self.address_var)
        self.entry.config(width=20, state="disabled")
        self.entry.configure(disabledbackground="white", disabledforeground="black")

        self.address_label = tk.Label(self.address_frame, textvariable=self.address_label_var)
        self.address_label.grid(row=1, column=0)
        self.entry.grid(row=1, column=1)
        self.address_frame.grid(row=1, column=0, columnspan=2)

        self.console = cw.Console(self, width=50, height=15, font=("normal", 8))

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

        for i in range(len(plot_descriptions)):
            plot = cw.EmbeddedFigure(master=self.gravity_plots, figsize=(5, 2.5), maxrecords=600)
            plot.addLinesObject()
            plot.addLinesObject()
            self.grav_axes.append(plot)
            self.gravity_plots.add(plot, text=plot_descriptions[i])
            for _ in range(3):
                self.data_buffers.append([])  # Data buffers for each lines object in EmbeddedFigure.

        for ax in self.grav_axes:
            ax.legend(["X", "Y", "Z"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
            ax.xlabel("Time elapsed (s)")
            ax.ylabel("Gravitational acceleration (G)")

        self.data_buttons_frame = tk.Frame(self)

        self.fourier_plot = cw.EmbeddedFigure(master=self.fourier, figsize=(5, 2.5), maxrecords=600)
        self.fourier_plot.addLinesObject()
        self.fourier_plot.addLinesObject()
        self.fourier_plot.xlabel("Frequency (Hz)")
        self.fourier_plot.ylabel("Intensity")
        self.fourier.add(self.fourier_plot, text="FFT of gravity vector")
        self.fourier_plot.legend(["FFT(X)", "FFT(Y)", "FFT(Z)"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)

        self.time_shift_plot = cw.EmbeddedFigure(master=self.time_shift, figsize=(5, 2.5), maxrecords=600)
        self.time_shift.add(self.time_shift_plot, text="Time shift map of gravity vector")

        self.data_save_frame.rowconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(1, weight=1)

        self.save_button = tk.Button(self.data_save_frame, text="Save to CSV", command=self.saveFile, width=17)
        self.clear_button = tk.Button(self.data_save_frame, text="Clear data", command=self.clearData, width=17)
        self.save_button.grid(row=0, column=0, padx=10)
        self.clear_button.grid(row=0, column=1, padx=10)

        self.server_buttons_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nswe")
        self.data_save_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nswe")
        self.console.grid(row=1, column=0, padx=10, pady=10, sticky="nswe")
        self.gravity_plots.grid(row=2, column=0, padx=10, pady=10, sticky="nswe")
        self.fourier.grid(row=1, column=1, padx=10, pady=10, sticky="nswe")
        self.time_shift.grid(row=2, column=1, padx=10, pady=10, sticky="nswe")
        self.data_buttons_frame.grid(row=3, column=0, pady=10, padx=10, sticky="nswe")

    def handleRunServer(self):
        server_object = self.master.master.server
        server_object.runServer()

    def enableInterface(self):  # Had to define different method for changing the button states. Since runServer()
        # is running on a different thread, a server.running flag cannot be checked, because it's state has not
        # been updated yet. Changing button states has to be done from within the runServer method.
        self.start_server_button.configure(state="disabled")
        self.close_server_button.configure(state="normal")
        server_object = self.master.master.server
        self.address_var.set(server_object.address + ":" + str(server_object.port))
        self.plotting_flag = True

    def handleCloseServer(self):
        self.plotting_flag = False
        server_object = self.master.master.server
        server_object.closeServer()
        self.start_server_button.configure(state="normal")
        self.close_server_button.configure(state="disabled")
        self.address_var.set("")
        self.master.master.server.console.println("Connection to server closed.", headline="TCP: ", msg_type="TCP")

    def resetDataBuffers(self):
        self.master.master.data_queue = queue.Queue()
        self.master.master.server.data_queue = self.master.master.data_queue
        size_ = len(self.data_buffers)
        self.data_buffers = []
        for i in range(size_):
            self.data_buffers.append([])

    def updateData(self):

        data_queue = self.master.master.data_queue

        if not data_queue.empty():
            message_string = data_queue.get()
            values = [float(val) for val in message_string.split(";")]

            for index, buffer in enumerate(self.data_buffers):

                if len(buffer) >= self.data_records_amount:
                    temp = list(np.roll(buffer, -1))
                    temp[-1] = values[index]
                    self.data_buffers[index] = temp

                else:
                    buffer.append(values[index])
            with open("temp/data.temp", "a") as file:
                file.write(message_string)
            data_queue.task_done()

        if all(self.data_buffers):  # If data buffers are not empty, plot.

            # Update plots only if data tab is active.
            if self.master.main_tabs.index(self.master.main_tabs.select()) == 1:
                for plot_ind, plot in enumerate(self.grav_axes):
                    for line, buffer in zip(plot.lines, self.data_buffers[3 * plot_ind:3 * plot_ind + 3]):
                        plot.plot(line, np.arange(0, len(buffer)), buffer)

                if len(self.data_buffers[0]) >= self.data_records_amount:
                    pool = Pool(processes=3)
                    result = pool.imap(fft.fft, self.data_buffers[:3])
                    pool.close()
                    pool.join()
                    calculated_ffts = [fft_ for fft_ in result]
                    for index, buffer in enumerate(calculated_ffts):
                        N = len(self.data_buffers[index])
                        frt = fft.fft(self.data_buffers[index])
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
            self.master.master.server.console.println("No data to save.", headline="ERROR: ", msg_type="ERROR")

class PumpControl(ttk.LabelFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cycle_active = False

        self.water_slider = cw.SlidingIndicator(master=self, label="Watering volume", unit="ml",
                                                orientation="horizontal", from_=0, to=250, res=10, length=300,
                                                width=30, entry_pos="right")

        self.time_slider = cw.SlidingIndicator(master=self, label="Watering time interval", unit="min",
                                               orientation="horizontal", from_=0, to=240, res=5, length=300,
                                               width=30, entry_pos="right")

        self.water_slider.configureState(state="disabled")
        self.time_slider.configureState(state="disabled")

        self.times_frame = tk.Frame(self)

        self.time_left_label_var = tk.StringVar()
        self.time_left_label_var.set("Time till next watering cycle:")
        self.time_left_label = tk.Label(self.times_frame, textvariable=self.time_left_label_var)
        self.time_left_var = tk.StringVar()
        self.time_left_var.set("00:00")
        self.time_left_entry = tk.Entry(self.times_frame, textvariable=self.time_left_var)
        self.time_left_entry.configure(width=9, state="disabled", disabledbackground="white",
                                       disabledforeground="black", justify="center")

        self.time_left_label.grid(row=0, column=0)
        self.time_left_entry.grid(row=0, column=1)

        self.buttons_frame = tk.Frame(self)
        self.start_button = tk.Button(self.buttons_frame, text="Start cycle", command=self.startWateringCycle)
        self.stop_button = tk.Button(self.buttons_frame, text="Stop cycle", command=self.stopWateringCycle)
        self.force_cycle_button = tk.Button(self.buttons_frame, text="Force watering", command=self.forceWateringCycle)
        self.start_button.configure(state="disabled", width=9)
        self.stop_button.configure(state="disabled", width=9)
        self.force_cycle_button.configure(state="disabled", width=9)
        self.start_button.grid(row=0, column=0, padx=10, pady=10)
        self.stop_button.grid(row=0, column=1, padx=10, pady=10)
        self.force_cycle_button.grid(row=0, column=2, padx=10, pady=10)

        self.water_slider.grid(row=0, column=0, padx=10, pady=10)
        self.time_slider.grid(row=1, column=0, padx=10, pady=10)
        self.times_frame.grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.buttons_frame.grid(row=3, column=0, padx=10, pady=10)

        self.master.master.serial_buttons.append(self.start_button)
        self.master.master.serial_buttons.append(self.stop_button)
        self.master.master.serial_buttons.append(self.force_cycle_button)

    def startWateringCycle(self):
        if self.water_slider.getValue() > 0 and self.time_slider.getValue() > 0:

            self.cycle_active = True
            self.force_cycle_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.start_button.configure(state="disabled")

        else:
            self.master.master.serial_config.console.println("Time and volume values have to be greater than 0.",
                                                      headline="CCS: ", msg_type="CCS")

    def stopWateringCycle(self):
        self.cycle_active = False
        self.time_left_var.set("00:00")
        self.force_cycle_button.configure(state="disabled")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def forceWateringCycle(self):
        self.master.master.suspendSerialUI()
        func = partial(self.master.master.master.device.dumpWater,
                       self.water_slider.getValue(), self.master.master.breakSuspendSerialUI)
        threading.Thread(target=func).start()

    def disableWateringUI(self):
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.water_slider.configureState(state="disabled")
        self.time_slider.configureState(state="disabled")
        self.time_slider.reset()
        self.water_slider.reset()
        self.force_cycle_button.configure(state="disabled")

    def disableButtons(self):
        self.force_cycle_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="disabled")

    def enableWateringUI(self):
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="active")
        self.water_slider.configureState(state="active")
        self.time_slider.configureState(state="active")