import tkinter as tk
from tkinter import filedialog, messagebox, Grid
import clinostat_com
from datetime import datetime
import threading
import multiprocessing as mp
from multiprocessing import Pool
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
import time
import math

# todo: Add time shift maps to data tab.
# todo: Rewrite most of the program to avoid re verse calls like self.master.master.master.device.pause.
# The above is due to the change in the program architecture which wasn't planned in this form in the beginning.

# todo: Add chamber environment control and monitoring (scheduling water pumps, lighting settings, temperature monitor)


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

    def refreshPorts(self) -> None:

        self.available_ports = clinostat_com.getPorts()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        # self.port_menu['menu'].delete(0, "end")
        # for port in self.available_ports:
        #     self.port_menu['menu'].add_command(label=port, command=tk._setit(self.port_option_var, port))
        self.port_menu["values"] = self.available_ports
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
            if clinostat_com.tryConnection(potential_port):
                self.master.master.master.device = clinostat_com.Clinostat(potential_port)
                self.master.master.master.device.port_name = potential_port
                self.console.println("Succesfully connected to {}.".format(potential_port), headline="STATUS: ")
                self.master.master.master.device.linkConsole(self.console)
                self.disconnect_button.configure(state="normal")
                self.connect_button.configure(state="disabled")
                self.master.master.enableStart()

            else:
                self.console.println("Connection to serial port failed.", headline="ERROR: ", msg_type="ERROR")
                self.connect_button.configure(state="normal")

    def disconnectPort(self) -> None:

        self.master.master.master.device.close_serial()
        self.console.println("Succesfully disconnected from {}.".format(self.master.master.master.device.port_name),
                             headline="STATUS: ")
        self.master.master.master.device = None
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.master.master.disableAllModes()
        self.master.master.control_system.pump_control.cycle_active = False


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

    def readIndicatorValues(self):
        return (indicator.getValue() for indicator in self.indicators)

    def handleAbort(self):
        self.disableButtons()
        func = partial(self.master.master.master.device.abort, self.enableRun)
        threading.Thread(target=func).start()

    def handleRun(self):
        self.disableButtons()
        self.master.master.blockIndicators()
        func = partial(self.master.master.master.device.run, self.readIndicatorValues(), self.enableStop)
        threading.Thread(target=func).start()

    def handleEcho(self):
        self.master.master.master.device.echo()

    def handlePause(self):
        self.disableButtons()
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
            indicator.configureState(state="normal")
            indicator.reset()
            indicator.configureState(state="disabled")


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
            ax.legend(["X", "Y", "Z"],bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
            ax.xlabel("Time elapsed (s)")
            ax.ylabel("Gravitational acceleration (G)")

        self.data_buttons_frame = tk.Frame(self)

        self.fourier_plot = cw.EmbeddedFigure(master=self.fourier, figsize=(5, 2.5), maxrecords=600)
        self.fourier_plot.addLinesObject()
        self.fourier_plot.addLinesObject()
        self.fourier_plot.xlabel("Frequency (Hz)")
        self.fourier_plot.ylabel("Intensity")
        self.fourier.add(self.fourier_plot, text="FFT of gravity vector")
        self.fourier_plot.legend(["FFT(X)", "FFT(Y)", "FFT(Z)"],bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)

        self.time_shift_plot = cw.EmbeddedFigure(master=self.time_shift,figsize=(5, 2.5), maxrecords=600)
        self.time_shift.add(self.time_shift_plot,text="Time shift map of gravity vector")

        self.data_save_frame.rowconfigure(0,weight=1)
        self.data_save_frame.columnconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(1, weight=1)

        self.save_button = tk.Button(self.data_save_frame, text="Save to CSV", command=self.saveFile, width=17)
        self.clear_button = tk.Button(self.data_save_frame, text="Clear data", command=self.clearData, width=17)
        self.save_button.grid(row=0, column=0, padx=10)
        self.clear_button.grid(row=0, column=1, padx=10)

        self.server_buttons_frame.grid(row=0, column=0, padx=10,pady=10, sticky="nswe")
        self.data_save_frame.grid(row=0, column=1, padx=10,pady=10, sticky="nswe")
        self.console.grid(row=1, column=0, padx=10,pady=10, sticky="nswe")
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

            if self.master.main_tabs.index(self.master.main_tabs.select()) == 1: # Update plots only if data tab is active.
                for plot_ind, plot in enumerate(self.grav_axes):
                    for line, buffer in zip(plot.lines, self.data_buffers[3 * plot_ind:3 * plot_ind + 3]):
                        plot.plot(line, np.arange(0, len(buffer)), buffer)

                if len(self.data_buffers[0]) >= self.data_records_amount:
                    pool = Pool(processes=3)
                    result = pool.imap(fft.fft,self.data_buffers[:3])
                    pool.close()
                    pool.join()
                    a = [vec for vec in result]
                    for index, buffer in enumerate(a):
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
        # volume of water to pump
        # time interval of the watering
        # update parameters button
        # time remaining to next pumping cycle

        # water_title = tk.StringVar()
        # water_title.set("Watering volume:")
        # self.water_label = tk.Label(self,textvariable=water_title)
        # self.water_var = tk.DoubleVar()
        # self.water_var.set(0)
        # self.water_slider = tk.Scale(self,from_=0, to=200,orient="horizontal",resolution=10,length=300,
        #                              command = self.updateWaterSlider,showvalue=0,width=30)
        # water_unit_var = tk.StringVar()
        # water_unit_var.set("ml")
        # self.water_unit_label = tk.Label(self,textvariable=water_unit_var)

        self.water_slider = cw.SlidingIndicator(master=self, label="Watering volume",unit="ml",
                                                orientation="horizontal", from_=0,to=250,res=10,length=300,
                                                width=30,entry_pos="right")

        self.time_slider = cw.SlidingIndicator(master=self, label="Watering time interval",unit="min",
                                                orientation="horizontal", from_=0,to=240,res=5,length=300,
                                                width=30,entry_pos="right")

        self.water_slider.configureState(state="disabled")
        self.time_slider.configureState(state="disabled")

        self.times_frame = tk.Frame(self)

        self.time_passed_label_var = tk.StringVar()
        self.time_passed_label_var.set("Time from last watering cycle:")
        self.time_passed_label = tk.Label(self.times_frame,textvariable=self.time_passed_label_var)
        self.time_passed_var = tk.StringVar()
        self.time_passed_var.set(0)
        self.time_passed_entry = tk.Entry(self.times_frame, textvariable=self.time_passed_var)
        self.time_passed_entry.configure(width=9, state="disabled", disabledbackground="white",
                                         disabledforeground="black", justify="center")

        self.time_left_label_var = tk.StringVar()
        self.time_left_label_var.set("Time till next watering cycle:")
        self.time_left_label = tk.Label(self.times_frame, textvariable=self.time_left_label_var)
        self.time_left_var = tk.StringVar()
        self.time_left_var.set(0)
        self.time_left_entry = tk.Entry(self.times_frame, textvariable=self.time_left_var)
        self.time_left_entry.configure(width=9, state="disabled", disabledbackground="white",
                                         disabledforeground="black", justify="center")

        self.time_passed_label.grid(row=0,column=0)
        self.time_passed_entry.grid(row=0,column=1)
        self.time_left_label.grid(row=1, column=0)
        self.time_left_entry.grid(row=1, column=1)

        self.buttons_frame = tk.Frame(self)
        self.start_button = tk.Button(self.buttons_frame, text="Start cycle", command=self.startWateringCycle)
        self.stop_button = tk.Button(self.buttons_frame, text="Stop cycle", command=self.stopWateringCycle)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.start_button.grid(row=0,column=0,padx=10,pady=10)
        self.stop_button.grid(row=0, column=1, padx=10, pady=10)

        self.water_slider.grid(row=0,column=0,padx=10,pady=10)
        self.time_slider.grid(row=1,column=0,padx=10,pady=10)
        self.times_frame.grid(row=2,column=0,padx=10,pady=10,sticky="W")
        self.buttons_frame.grid(row=3,column=0,padx=10,pady=10)
        # self.water_label.grid(row=1,column=0,padx=10,pady=5,sticky="W")
        # self.water_slider.grid(row=2,column=0,padx=10,pady=10)
        # self.water_unit_label.grid(row=2,column=1,sticky="W")

    def startWateringCycle(self):
        self.cycle_active = True

    def stopWateringCycle(self):
        self.cycle_active = False

    def disableUI(self):
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.water_slider.configureState(state="disabled")
        self.time_slider.configureState(state="disabled")

    def enableUI(self):
        self.stop_button.configure(state="active")
        self.start_button.configure(state="active")
        self.water_slider.configureState(state="active")
        self.time_slider.configureState(state="active")


class ClinostatControlSystem(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_tabs = ttk.Notebook(self)

        self.motors_tab = tk.Frame(self)

        self.serial_config = SerialConfig(self.motors_tab,text="Controller connection")
        self.mode_options = ModeMenu(self.motors_tab,text="Motors control")
        self.pump_control = PumpControl(self.motors_tab, text="Pump control")

        self.serial_config.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
        self.mode_options.grid(row=1, column=0, sticky="nswe", padx=10, pady=10)
        self.pump_control.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

        self.data_embed = DataEmbed(self)

        self.main_tabs.add(self.motors_tab, text="Clinostat control")
        self.main_tabs.add(self.data_embed, text="Chamber computer")

        Grid.rowconfigure(self, 0, weight=1)
        Grid.columnconfigure(self, 0, weight=1)

        self.main_tabs.grid(row=0, column=0, sticky="nswe")

    def disableAllModes(self):
        self.mode_options.disableButtons()
        self.mode_options.resetIndicators()
        self.mode_options.disableIndicators()
        self.pump_control.disableUI()

    def blockIndicators(self):
        self.mode_options.disableIndicators()

    def enableStart(self):
        self.mode_options.enableRun()
        self.pump_control.enableUI()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.device = None
        self.seconds_tracker = time.time()
        self.pumps_tracker = time.time()
        self.pump_flag_previous_state = False

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

        if self.device and self.control_system.pump_control.cycle_active:

            now_time = time.time()

            if self.pump_flag_previous_state != self.control_system.pump_control.cycle_active:
                self.seconds_tracker = now_time
                self.pumps_tracker = now_time

            if now_time - self.seconds_tracker >= 1:
                # update entries
                time_left = self.control_system.pump_control.time_slider.getValue()*60 - (now_time - self.pumps_tracker)
                mins = math.floor(time_left/60)
                secs = math.floor(time_left - mins*60)
                self.control_system.pump_control.time_passed_var.set(0)
                self.control_system.pump_control.time_left_var.set(f"{mins:02d}:{secs:02d}")
                print(time_left)
                self.seconds_tracker = now_time

            if (now_time - self.pumps_tracker)/60 >= self.control_system.pump_control.time_slider.getValue():
                # send command to controller to execute watering routine
                # send console notification
                self.pumps_tracker = now_time

        self.pump_flag_previous_state = self.control_system.pump_control.cycle_active
        self.after(1, self.programLoop)


if __name__ == "__main__":
    root = App()
    root.resizable(False, False)
    root.title("Clinostat control system")
    # root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
