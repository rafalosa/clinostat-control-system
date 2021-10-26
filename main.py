from modules import data_socket, properties
from modules.segments import *
import yaml
import queue
import os
import tkinter.ttk as ttk
import time
import ttkbootstrap
from tkinter import PhotoImage

# todo: There is a possibility that a watering command is executed during a rampdown of the motors which would cause a
#  ClinostatCommunicationError exception to occur. Do something to prevent that. <- use a thread lock for each serial
#  operation.


class InterfaceManager(ttk.Notebook):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.serial_sensitive_interface = {}
        self.serial_interface_buffer = {}
        self.serial_access_modules = {}
        self.interface = {}
        self.outputs = {}

        self.motors_tab = tk.Frame(self)

        self.serial_config = self.serial_access_modules["connection"] =\
            SerialConfig(master=self.motors_tab,
                         supervisor=self.master,
                         interface_manager=self,
                         text="Controller connection")
        self.serial_sensitive_interface.update(self.serial_config.serial_sensitive_interface)
        self.interface.update(self.serial_config.interface)

        self.mode_options = self.serial_access_modules["modes"] =\
            ModeMenu(master=self.motors_tab,
                     supervisor=self.master,
                     interface_manager=self,
                     text="Motors control")
        self.serial_sensitive_interface.update(self.mode_options.serial_sensitive_interface)
        self.interface.update(self.mode_options.interface)

        self.pump_control = self.serial_access_modules["pump_control"] =\
            PumpControl(master=self.motors_tab,
                        supervisor=self.master,
                        interface_manager=self,
                        text="Pump control")
        self.serial_sensitive_interface.update(self.pump_control.serial_sensitive_interface)
        self.interface.update(self.pump_control.interface)

        self.light_control = LightControl(master=self.motors_tab, supervisor=self.master, interface_manager=self,
                                          text="Lighting control")
        self.interface.update(self.light_control.interface)

        self.server_starter = ServerStarter(master=self.motors_tab, supervisor=self.master, interface_manager=self,
                                            text="TCP server control")
        self.interface.update(self.server_starter.interface)

        self.serial_config.grid(row=0, column=0, padx=10, pady=10, sticky="nw", rowspan=4)
        self.mode_options.grid(row=0, column=1, padx=10, pady=10, sticky="nw")
        self.pump_control.grid(row=1, column=1, padx=10, pady=10, sticky="nw")
        self.light_control.grid(row=2, column=1, padx=10, pady=10, sticky="nw")
        self.server_starter.grid(row=3, column=1, padx=10, pady=10, sticky="sw")

        self.data_embed = DataEmbed(master=self, supervisor=self.master, interface_manager=self)
        self.interface.update(self.data_embed.interface)

        self.outputs["primary"] = self.serial_config.console
        self.master.params["server"].link_output(self.outputs["primary"].println)

        self.master.params["plotter"] = self.data_embed

        self.add(self.motors_tab, text="Clinostat control")
        self.add(self.data_embed, text="Diagnostics")

    def ui_modes_reset(self) -> None:
        self.serial_sensitive_interface["connect"].configure(state="normal")
        self.serial_sensitive_interface["disconnect"].configure(state="disabled")
        self.ui_disable_command_buttons()
        self.ui_disable_speed_Indicators()
        self.mode_options.reset_indicators()
        self.ui_watering_reset()

    def ui_serial_suspend(self) -> None:
        self.serial_interface_buffer = {button: self.serial_sensitive_interface[button]["state"]
                                        for button in self.serial_sensitive_interface}
        for button in self.serial_sensitive_interface:
            self.serial_sensitive_interface[button].configure(state="disabled")

    def ui_serial_break_suspend(self) -> None:
        if self.serial_interface_buffer:
            for button in self.serial_sensitive_interface:
                self.serial_sensitive_interface[button].configure(state=self.serial_interface_buffer[button])
            self.serial_interface_buffer = {}
        else:
            raise RuntimeError("Button states not saved.")

    def ui_disable_speed_Indicators(self) -> None:
        self.interface["speed_slider1"].configure_state(state="disabled")
        self.interface["speed_slider2"].configure_state(state="disabled")

    def ui_enable_speed_indicators(self) -> None:
        self.interface["speed_slider1"].configure_state(state="normal")
        self.interface["speed_slider2"].configure_state(state="normal")

    def ui_device_connected(self) -> None:
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["connect"].configure(state="disabled")
        self.ui_enable_run()
        self.ui_watering_enable()

    def ui_run_handler(self) -> None:
        self.ui_disable_command_buttons()
        self.ui_disable_speed_Indicators()
        self.ui_serial_suspend()

    def ui_abort_handler(self) -> None:
        self.ui_disable_command_buttons()

    def ui_pause_handler(self) -> None:
        self.ui_disable_command_buttons()
        self.ui_serial_suspend()

    def ui_resume_handler(self) -> None:
        self.serial_sensitive_interface["resume"].configure(state="disabled")
        self.serial_sensitive_interface["pause"].configure(state="normal")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_home_handler(self) -> None:
        pass

    def ui_disable_command_buttons(self) -> None:
        self.serial_sensitive_interface["disconnect"].configure(state="disabled")
        self.serial_sensitive_interface["abort"].config(state="disabled")
        self.serial_sensitive_interface["run"].config(state="disabled")
        self.serial_sensitive_interface["pause"].config(state="disabled")
        self.serial_sensitive_interface["resume"].config(state="disabled")
        self.serial_sensitive_interface["echo"].config(state="disabled")
        # self.serial_sensitive_interface["home"].config(state="disabled")

    def ui_enable_stop(self) -> None:
        self.ui_serial_break_suspend()
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["pause"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_enable_run(self) -> None:
        self.serial_sensitive_interface["run"].config(state="normal")
        # self.serial_sensitive_interface["home"].config(state="normal")
        self.serial_sensitive_interface["echo"].config(state="normal")
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.ui_enable_speed_indicators()

    def ui_enable_resume(self) -> None:
        self.ui_serial_break_suspend()
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["resume"].configure(state="normal")
        self.serial_sensitive_interface["pause"].configure(state="disabled")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_disable_pump_indicators(self) -> None:
        self.interface["water_slider1"].configure_state(state="disabled")
        self.interface["time_slider1"].configure_state(state="disabled")

    def ui_enable_pump_indicators(self) -> None:
        self.interface["water_slider1"].configure_state(state="normal")
        self.interface["time_slider1"].configure_state(state="normal")

    def ui_watering_started(self) -> None:
        self.serial_sensitive_interface["force"].configure(state="normal")
        self.serial_sensitive_interface["stop"].configure(state="normal")
        self.serial_sensitive_interface["start"].configure(state="disabled")
        self.interface["time_slider1"].configure_state(state="disabled")
        self.interface["water_slider1"].configure_state(state="disabled")

    def ui_watering_stopped(self) -> None:
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="normal")
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.interface["time_slider1"].configure_state(state="normal")
        self.interface["water_slider1"].configure_state(state="normal")

    def ui_watering_reset(self) -> None:
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="disabled")
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.interface["water_slider1"].configure_state(state="disabled")
        self.interface["time_slider1"].configure_state(state="disabled")
        self.interface["time_slider1"].reset()
        self.interface["water_slider1"].reset()

    def ui_watering_buttons_disable(self) -> None:
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="disabled")

    def ui_watering_enable(self) -> None:
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="active")
        self.interface["water_slider1"].configure_state(state="normal")
        self.interface["time_slider1"].configure_state(state="normal")

    def ui_server_enable(self) -> None:
        self.interface["start_server"].configure(state="disabled")
        self.interface["close_server"].configure(state="normal")

    def ui_server_disable(self) -> None:
        self.interface["start_server"].configure(state="normal")
        self.interface["close_server"].configure(state="disabled")

    def ui_lighting_enable(self) -> None:
        self.interface["light_slider1"].configure_state(state="normal")
        self.interface["light_slider2"].configure_state(state="normal")

    def ui_lighting_disable(self) -> None:
        self.interface["light_slider1"].reset()
        self.interface["light_slider2"].reset()
        self.interface["light_slider1"].configure_state(state="disabled")
        self.interface["light_slider2"].configure_state(state="disabled")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.params = properties.AppProperties()
        self.variables = properties.AppVariables()
        self.trackers = properties.AppTrackers()
        self.flags = properties.AppFlags()
        self.data_buffers = properties.DataBuffers()
        self.serial_lock = threading.Lock()
        ttkbootstrap.Style(theme="cosmo")

        if "saved data" not in os.listdir("."):
            os.mkdir("saved data")

        if "temp" not in os.listdir("."):
            os.mkdir("temp")
        else:
            if "data.temp" in os.listdir("temp"):
                os.remove("temp/data.temp")
                with open("temp/data.temp", "a"):
                    pass

        with open("config/config.yaml", "r") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

        self.get_queue = queue.Queue()
        self.put_queue = queue.Queue()
        self.params["server"] = data_socket.DataServer(address=config["IP"], port=config["PORT"])
        self.params["server"].attach_receive_queue(self.get_queue)
        self.params["server"].attach_response_queue(self.put_queue)

        self.interface_manager = InterfaceManager(self)
        self.interface_manager.pack(expand=True)

    def destroy(self) -> None:

        if self.params["server"].running:
            self.params["server"].close_server()

        if self.params["device"]:
            self.params["device"].close_serial()

        super().quit()

    def clear_queues(self) -> None:
        with self.get_queue.mutex:
            self.get_queue.queue.clear()

        with self.put_queue.mutex:
            self.put_queue.queue.clear()

    def reset_data_buffers(self) -> None:
        self.data_buffers = properties.DataBuffers()

    def device_likely_unplugged(self) -> None:

        try:
            self.params["device"].close_serial()
        except clinostat_com.ClinostatCommunicationError:
            pass
        self.params["device"] = None
        # try:
        #     self.serial_lock.release()
        # except RuntimeError:
        #     pass
        self.interface_manager.ui_modes_reset()
        self.flags["pumping"] = False
        self.trackers = properties.AppTrackers()

    def reset_timers(self):
        pass

    def program_loop(self) -> None:

        if self.flags["plotting"] and not self.get_queue.empty():
            self.params["plotter"].update_data()

        if self.params["device"] and self.flags["pumping"]:

            now_time = time.time()

            if self.flags["prev_pumping_flag_state"] != self.flags["pumping"]:
                self.trackers["seconds"] = now_time
                self.trackers["pump_time"] = now_time

            if now_time - self.trackers["seconds"] >= 1:
                time_left = self.variables["time1"].get()*60 - (now_time - self.trackers["pump_time"])
                minutes = int(time_left/60)
                seconds = int(time_left - minutes*60)
                self.variables["time_left_str"].set(f"{minutes:02d}:{seconds:02d}")
                self.trackers["seconds"] = now_time

            if (now_time - self.trackers["pump_time"])/60 >= self.variables["time1"].get():
                self.interface_manager.pump_control.force_watering_cycle()
                self.trackers["pump_time"] = now_time

        self.flags["prev_pumping_flag_state"] = self.flags["pumping"]

        self.after(1, self.program_loop)


if __name__ == "__main__":
    root = App()
    root.resizable(False, False)
    root.title("Clinostat control system")
    root.iconphoto(True, PhotoImage(file="icon/favicon.gif"))
    root.after(1, root.program_loop)
    root.mainloop()
