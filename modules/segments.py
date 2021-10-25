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
import os
from modules.data_socket import ServerStartupError
from modules.custom_thread import ClinostatSerialThread
from typing import List


class SerialConfig(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.interface_manager = interface_manager
        self.serial_sensitive_interface = {}
        self.variables = {}

        self.available_ports = clinostat_com.get_ports()

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

        self.interface["refresh"] = tk.Button(self.port_menu_frame, command=self.refresh_ports, text="Refresh ports")

        self.interface["refresh"].config(width=17)

        self.port_label.grid(row=0, column=0)
        self.port_menu.grid(row=1, column=0, pady=2)
        self.interface["refresh"].grid(row=2, column=0, pady=2)

        self.connections_frame = tk.Frame(self)

        self.serial_sensitive_interface["connect"] = self.interface["connect"] = \
            tk.Button(self.connections_frame, command=lambda: threading.Thread(
                target=self.connect_to_port).start(), text="Connect", width=17)

        self.serial_sensitive_interface["disconnect"] = self.interface["disconnect"] = \
            tk.Button(self.connections_frame, command=self.disconnect_port,
                      text="Disconnect", width=17, state="disabled")

        self.interface["connect"].grid(row=0, column=0, pady=2)
        self.interface["disconnect"].grid(row=1, column=0, pady=2)

        self.console = cw.Console(self, font=("normal", 10))
        self.console.configure(width=65, height=54)

        self.interface["clear_console"] = tk.Button(self, command=self.console.clear,
                                                    text="Clear logs", width=17)

        self.port_menu_frame.grid(row=1, column=0, padx=10, sticky="n")
        self.connections_frame.grid(row=2, column=0, padx=10, pady=10, sticky="s")
        self.console.grid(row=1, column=1, rowspan=2, pady=10, padx=10, columnspan=3)
        self.interface["clear_console"].grid(row=0, column=3, pady=10, padx=10,sticky="e")

    def refresh_ports(self) -> None:

        self.available_ports = clinostat_com.get_ports()
        if not self.available_ports:
            self.available_ports = ["Empty"]

        self.port_menu["values"] = self.available_ports
        self.variables["ports"].set("Select serial port")
        self.console.println("Updated available serial ports.", headline="SERIAL: ", msg_type="MESSAGE")

    def connect_to_port(self) -> None:

        self.interface["connect"].configure(state="disabled")
        if self.supervisor.params["device"] is not None:
            self.supervisor.params["device"].close_serial()  # Not necessary.

        potential_port = self.variables["ports"].get()

        if potential_port == "Select serial port" or potential_port == "Empty":
            self.console.println("No ports to connect to.", headline="ERROR: ", msg_type="ERROR")
            self.interface["connect"].configure(state="normal")
        else:
            if clinostat_com.Clinostat.try_connection(potential_port):
                self.supervisor.params["device"] = clinostat_com.Clinostat(potential_port)
                self.supervisor.params["device"].port_name = potential_port
                self.console.println(f"Successfully connected to {potential_port}.", headline="STATUS: ")
                self.supervisor.params["device"].link_console(self.console)
                self.interface_manager.ui_device_connected()

            else:
                self.console.println("Connection to serial port failed.", headline="ERROR: ", msg_type="ERROR")
                self.interface["connect"].configure(state="normal")

    def disconnect_port(self) -> None:

        try:
            self.supervisor.params["device"].close_serial()
        except clinostat_com.ClinostatCommunicationError as ex:
            self.console.println(ex.message, headline="ERROR: ", msg_type="ERROR")
            return
        finally:
            port_name = self.supervisor.params["device"].port_name
            self.supervisor.params["device"] = None
            self.interface_manager.ui_modes_reset()
            self.supervisor.flags["pumping"] = False

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
        self.interface["speed_slider1"].grid(row=0, column=0, padx=15)
        self.interface["speed_slider2"].grid(row=0, column=1, padx=15)

        self.supervisor.variables["speed1"] = self.interface["speed_slider1"].var
        self.supervisor.variables["speed2"] = self.interface["speed_slider2"].var

        self.linear_indicators = [self.interface["speed_slider1"], self.interface["speed_slider2"]]  # Easier access.

        self.interface["abort"] = tk.Button(self.button_frame, command=self.handle_abort, text="Abort")
        self.interface["abort"].configure(width=ModeMenu.button_w, background="#bf4032", activebackground="#eb7063",
                                          foreground="white", disabledforeground="#d1d1d1", state="disabled")

        self.interface["run"] = tk.Button(self.button_frame, command=self.handle_run, text="Run")
        self.interface["run"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["pause"] = tk.Button(self.button_frame, command=self.handle_pause, text="Pause")
        self.interface["pause"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["resume"] = tk.Button(self.button_frame, command=self.handle_resume, text="Resume")
        self.interface["resume"].configure(width=ModeMenu.button_w, state="disabled")

        # self.interface["home"] = tk.Button(self.button_frame, command=self.handle_home, text="Home")
        # self.interface["home"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["echo"] = tk.Button(self.button_frame, command=self.handle_echo, text="Echo")
        self.interface["echo"].configure(width=ModeMenu.button_w, state="disabled")

        self.interface["abort"].grid(row=0, column=0, pady=ModeMenu.button_pady)
        self.interface["run"].grid(row=1, column=0, pady=ModeMenu.button_pady)
        self.interface["pause"].grid(row=2, column=0, pady=ModeMenu.button_pady)
        self.interface["resume"].grid(row=3, column=0, pady=ModeMenu.button_pady)
        # self.interface["home"].grid(row=4, column=0, pady=ModeMenu.button_pady)
        self.interface["echo"].grid(row=4, column=0, pady=ModeMenu.button_pady)

        self.button_frame.grid(row=1, column=0, padx=10)
        self.indicators_frame.grid(row=0, column=1, padx=30, rowspan=3, sticky="NE")

        for indicator in self.linear_indicators:
            indicator.configure_state(state="disabled")

        for widget in self.interface:
            if self.interface[widget] not in self.linear_indicators:
                self.serial_sensitive_interface[widget] = self.interface[widget]

    def read_indicator_values(self) -> List[float]:
        return [indicator.get_value() for indicator in self.linear_indicators]

    def handle_abort(self) -> None:
        self.interface_manager.ui_abort_handler()
        ClinostatSerialThread(target=self.supervisor.params["device"].abort,
                              at_success=self.interface_manager.ui_enable_run,
                              at_fail=self.supervisor.device_likely_unplugged).start()

    def handle_run(self) -> None:
        self.interface_manager.ui_run_handler()
        speed = self.read_indicator_values()
        ClinostatSerialThread(target=self.supervisor.params["device"].run, args=(speed,),
                              at_success=self.interface_manager.ui_enable_stop,
                              at_fail=self.supervisor.device_likely_unplugged).start()

    def handle_echo(self) -> None:
        self.interface_manager.ui_serial_suspend()
        ClinostatSerialThread(target=self.supervisor.params["device"].echo,
                              at_success=self.interface_manager.ui_serial_break_suspend,
                              at_fail=self.supervisor.device_likely_unplugged).start()

    def handle_pause(self) -> None:
        self.interface_manager.ui_pause_handler()
        ClinostatSerialThread(target=self.supervisor.params["device"].pause,
                              at_success=self.interface_manager.ui_enable_resume,
                              at_fail=self.supervisor.device_likely_unplugged).start()

    def handle_resume(self) -> None:
        self.interface_manager.ui_resume_handler()
        self.interface_manager.ui_disable_speed_Indicators()
        self.supervisor.params["device"].resume()

    def handle_home(self) -> None:
        self.supervisor.params["device"].home()

    def reset_indicators(self) -> None:
        for indicator in self.linear_indicators:
            indicator.reset()


class DataEmbed(tk.Frame):

    figsize_ = (5.7, 3.4)

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.variables = {}
        self.plots = {}
        self.interface_manager = interface_manager
        self.data_records_amount_default = 300

        self.data_save_frame = ttk.LabelFrame(self, text="Save or discard data")

        plt.rcParams['figure.facecolor'] = "#f0f0f0"
        plt.rcParams['font.size'] = 7
        plt.rcParams["lines.linewidth"] = 0.5
        plt.rcParams["figure.subplot.top"] = 0.85
        plt.rcParams["figure.subplot.bottom"] = 0.15
        plt.rcParams["figure.subplot.left"] = 0.17

        self.gravity_plots = ttk.Notebook(self)
        self.fourier = ttk.Notebook(self)
        self.temperatures = ttk.Notebook(self)
        self.humidity = ttk.Notebook(self)

        self.grav_axes = []
        plot_descriptions = ["Gravity vector", "Mean gravity"]
        plot_keys = ["grav_components", "grav_means"]

        for i in range(len(plot_descriptions)):
            self.plots[plot_keys[i]] = cw.EmbeddedFigure(master=self.gravity_plots,
                                                         figsize=DataEmbed.figsize_,
                                                         tracking=True)
            self.plots[plot_keys[i]].add_lines_object()
            self.plots[plot_keys[i]].add_lines_object()
            self.grav_axes.append(self.plots[plot_keys[i]])
            self.gravity_plots.add(self.plots[plot_keys[i]], text=plot_descriptions[i])

        for ax in self.grav_axes:
            ax.legend(["X", "Y", "Z"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
            ax.xlabel("Time elapsed (s)")
            ax.ylabel("Gravitational acceleration (G)")

        self.plots["fourier"] = cw.EmbeddedFigure(master=self.fourier, figsize=DataEmbed.figsize_)
        for i in range(2):
            self.plots["fourier"].add_lines_object()
        self.plots["fourier"].xlabel("Frequency (Hz)")
        self.plots["fourier"].ylabel("Intensity")
        self.fourier.add(self.plots["fourier"], text="FFT of gravity vector")
        self.plots["fourier"].legend(["FFT(X)", "FFT(Y)", "FFT(Z)"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)

        self.plots["temperatures"] = cw.EmbeddedFigure(master=self.temperatures,
                                                       figsize=DataEmbed.figsize_,
                                                       tracking=True)
        for i in range(2):
            self.plots["temperatures"].add_lines_object()

        self.plots["temperatures"].xlabel("Elapsed time (s)")
        self.plots["temperatures"].ylabel("Temperature °C")
        self.plots["temperatures"].legend(["Temp1", "Temp2", "Temp3"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
        self.temperatures.add(self.plots["temperatures"], text="Temperatures")

        self.plots["humidity"] = cw.EmbeddedFigure(master=self.humidity,
                                                   figsize=DataEmbed.figsize_,
                                                   tracking=True,
                                                   style=".",
                                                   maxrecords=10)
        self.plots["humidity"].xlabel("Elapsed time (min)")
        self.plots["humidity"].ylabel("Humidity %")
        self.plots["humidity"].set_hard_y_limits([0, 100])
        self.plots["humidity"].legend(["Sensor1"], bbox_to_anchor=(0, 1.02, 1, .102), loc=3, ncol=3)
        self.humidity.add(self.plots["humidity"], text="Humidity")

        self.data_save_frame.rowconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(0, weight=1)
        self.data_save_frame.columnconfigure(1, weight=1)

        self.interface["save"] = tk.Button(self.data_save_frame, text="Save to CSV", command=self.save_file, width=17)
        self.interface["clear"] = tk.Button(self.data_save_frame, text="Clear data", command=self.clear_data, width=17)
        self.interface["save"].grid(row=0, column=0, padx=10, pady=10)
        self.interface["clear"].grid(row=0, column=1, padx=10, pady=10)

        self.data_save_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nwse", columnspan=2)
        self.gravity_plots.grid(row=0, column=0, padx=10, pady=10, sticky="sw", columnspan=2)
        self.fourier.grid(row=0, column=2, padx=10, pady=10, sticky="ne", columnspan=2)
        self.temperatures.grid(row=1, column=2, padx=10, pady=10, sticky="se", columnspan=2)
        self.humidity.grid(row=1, column=0, padx=10, pady=10, sticky="sw", columnspan=2)

    def reset_data_buffers(self) -> None:
        self.supervisor.clear_queues()
        self.supervisor.reset_data_buffers()

    def update_data(self) -> None:

        data_queue = self.supervisor.get_queue

        if not data_queue.empty():
            self.supervisor.flags["new_data_present"] = True
            message_string = data_queue.get()
            values = [float(val) for val in message_string.split(";")]
            index = 0
            for key in self.supervisor.data_buffers:

                for i, buffer in enumerate(self.supervisor.data_buffers[key]):

                    if key == "humidity" and values[index] == -100:
                        pass

                    else:
                        temp = list(np.roll(buffer, -1))
                        temp[-1] = values[index]
                        self.supervisor.data_buffers[key][i] = temp

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

                for line, buffer in zip(self.plots["temperatures"].lines, self.supervisor.data_buffers["temperatures"]):
                    self.plots["temperatures"].plot(line, np.arange(0, len(buffer)), buffer)

                obj = self.plots["humidity"]
                buffer = self.supervisor.data_buffers["humidity"][0]
                obj.plot(obj.lines[0], np.arange(0, len(buffer)), buffer)

                if len(self.supervisor.data_buffers["grav_components"][0]) >= self.data_records_amount_default:
                    pool = Pool(processes=3)
                    result = pool.imap(fft.fft, self.supervisor.data_buffers["grav_components"])
                    pool.close()
                    pool.join()
                    calculated_ffts = [fft_ for fft_ in result]
                    for index, buffer in enumerate(calculated_ffts):
                        N = len(self.supervisor.data_buffers["grav_components"][index])
                        frt = fft.fft(self.supervisor.data_buffers["grav_components"][index])
                        fr_domain = fft.fftfreq(N, 10)[:N // 2]
                        self.plots["fourier"].plot(self.plots["fourier"].lines[index], fr_domain,
                                                   np.abs(frt[:N // 2]))

        else:
            for plot in self.plots:
                self.plots[plot].reset_plot()

    def clear_data(self) -> None:
        if messagebox.askyesno(title="Clinostat control system", message="Are you sure you want to clear all data?"):
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("temp/data.temp", "a"):
                    pass
            self.reset_data_buffers()
            self.update_data()

    def save_file(self) -> None:
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
            messagebox.showinfo(title="Save or discard data", message="No data to save.")


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

        self.interface["water_slider1"].configure_state(state="disabled")
        self.interface["time_slider1"].configure_state(state="disabled")

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
            tk.Button(self.buttons_frame, text="Start cycle", command=self.start_watering_cycle)
        self.interface["start"].configure(state="disabled", width=8)

        self.interface["stop"] = self.serial_sensitive_interface["stop"] =  \
            tk.Button(self.buttons_frame, text="Stop cycle", command=self.stop_watering_cycle)
        self.interface["stop"].configure(state="disabled", width=8)

        self.interface["force"] = self.serial_sensitive_interface["force"] = \
            tk.Button(self.buttons_frame, text="Force cycle", command=self.force_watering_cycle)
        self.interface["force"].configure(state="disabled", width=8)

        self.interface["start"].grid(row=0, column=0, padx=10, pady=10)
        self.interface["stop"].grid(row=0, column=1, padx=10, pady=10)
        self.interface["force"].grid(row=0, column=2, padx=10, pady=10)

        self.interface["water_slider1"].grid(row=0, column=0, padx=10, pady=10)
        self.interface["time_slider1"].grid(row=1, column=0, padx=10, pady=10)

        self.times_frame.grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.buttons_frame.grid(row=3, column=0, padx=10, pady=10)

    def start_watering_cycle(self) -> None:
        if self.interface["water_slider1"].get_value() > 0 and self.interface["time_slider1"].get_value() > 0:
            self.supervisor.flags["pumping"] = True
            self.interface_manager.ui_watering_started()

        else:
            self.interface_manager.outputs["primary"].println("Time and water volume values"
                                                              " have to be greater than 0.",
                                                              headline="ERROR: ", msg_type="ERROR")

    def stop_watering_cycle(self) -> None:
        self.supervisor.flags["pumping"] = False
        self.variables["time_left"].set("00:00")
        self.interface_manager.ui_watering_stopped()

    def force_watering_cycle(self) -> None:
        self.interface_manager.ui_serial_suspend()

        ClinostatSerialThread(target=self.supervisor.params["device"].dump_water,
                              at_success=self.interface_manager.ui_serial_break_suspend,
                              at_fail=self.supervisor.device_likely_unplugged,
                              args=(self.interface["water_slider1"].get_value(),)).start()


class LightControl(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.interface = {}
        self.interface_manager = interface_manager

        self.intensity_slider_red = cw.SlidingIndicator(master=self, label="Red light intensity",
                                                        unit="%  ",
                                                        orientation="horizontal",
                                                        from_=0, to=100, res=1,
                                                        length=300, width=30,
                                                        entry_pos="right",
                                                        opt=self.update_value_container)

        self.intensity_slider_blue = cw.SlidingIndicator(master=self,
                                                         label="Blue light intensity",
                                                         unit="%  ",
                                                         orientation="horizontal",
                                                         from_=0, to=100, res=1,
                                                         length=300, width=30,
                                                         entry_pos="right",
                                                         opt=self.update_value_container)

        self.intensity_slider_red.grid(row=0, column=0, sticky="ne", padx=10, pady=10)
        self.intensity_slider_blue.grid(row=1, column=0, sticky="ne", padx=10, pady=10)
        self.intensity_slider_red.configure_state(state="disabled")
        self.intensity_slider_blue.configure_state(state="disabled")
        self.interface["light_slider1"] = self.intensity_slider_red
        self.interface["light_slider2"] = self.intensity_slider_blue

        self.intensity_queue = self.supervisor.put_queue

    def update_value_container(self, *args) -> None:
        msg = f'{self.intensity_slider_red.get_value()};{self.intensity_slider_blue.get_value()}'
        self.intensity_queue.put(msg)


class ServerStarter(ttk.LabelFrame):

    def __init__(self, supervisor, interface_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervisor = supervisor
        self.variables = {}
        self.interface = {}
        self.interface_manager = interface_manager

        self.interface["start_server"] = tk.Button(self,
                                                   text="Run server",
                                                   command=self.handle_run_server)

        self.interface["start_server"].configure(width=20)
        self.interface["start_server"].grid(row=0, column=0, pady=2, padx=30, sticky="w")

        self.interface["close_server"] = tk.Button(self,
                                                   text="Close server", command=self.handle_close_server)
        self.interface["close_server"].configure(width=20, state="disabled")
        self.interface["close_server"].grid(row=0, column=1, pady=2, padx=30, sticky="e")

        self.variables["address"] = self.supervisor.variables["address"] = tk.StringVar()
        self.interface["address_entry"] = tk.Entry(self,
                                                   textvariable=self.supervisor.variables["address"],
                                                   justify="center")

        self.interface["address_entry"].config(width=20, state="disabled")
        self.interface["address_entry"].configure(disabledbackground="white", disabledforeground="black")

        self.address_label = tk.Label(self, text="Current server address:")

        self.interface["start_server"].grid(row=0, column=0)
        self.interface["close_server"].grid(row=1, column=0)
        self.address_label.grid(row=2, column=0, pady=5)
        self.interface["address_entry"].grid(row=3, column=0, pady=10)

    def handle_run_server(self) -> None:
        server = self.supervisor.params["server"]
        try:
            server.run_server()
        except ServerStartupError:
            return

        self.interface_manager.ui_server_enable()
        self.supervisor.variables["address"].set(server.address + ":" + str(server.port))
        self.supervisor.flags["plotting"] = True
        self.interface_manager.ui_lighting_enable()

    def handle_close_server(self) -> None:
        self.interface_manager.ui_lighting_disable()
        self.interface_manager.ui_server_disable()
        self.supervisor.flags["plotting"] = False
        self.supervisor.params["server"].close_server()
        self.supervisor.variables["address"].set("")


if __name__ == "__main__":
    app = tk.Tk()
    app.title("widget test")
    app.mainloop()
