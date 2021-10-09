import tkinter as tk
from modules import data_socket, properties
from modules.segments import SerialConfig, DataEmbed, PumpControl, ModeMenu, LightControl, ServerStarter
import yaml
import queue
import os
import tkinter.ttk as ttk
import time


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
                                            text="TCP client control")
        self.interface.update(self.server_starter.interface)

        self.serial_config.grid(row=0, column=0, padx=10, pady=10, sticky="nw", rowspan=2)
        self.mode_options.grid(row=2, column=0, padx=10, pady=10, sticky="sw")
        self.pump_control.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
        self.light_control.grid(row=1, column=1, padx=10, pady=10, sticky="ne")
        self.server_starter.grid(row=2, column=1, padx=10, pady=10, sticky="nw")

        self.data_embed = DataEmbed(master=self, supervisor=self.master, interface_manager=self)
        self.interface.update(self.data_embed.interface)

        self.outputs["serial"] = self.serial_config.console
        # self.outputs["server"] = self.data_embed.console
        self.master.params["server"].linkOutput(self.outputs["serial"].println)

        self.master.params["plotter"] = self.data_embed

        self.add(self.motors_tab, text="Clinostat control")
        self.add(self.data_embed, text="Chamber computer")

    def ui_modesSuspend(self):
        self.serial_sensitive_interface["connect"].configure(state="normal")
        self.serial_sensitive_interface["disconnect"].configure(state="disabled")
        self.ui_disableCommandButtons()
        self.ui_disableSpeedIndicators()
        self.mode_options.resetIndicators()
        self.ui_wateringReset()

    def ui_serialSuspend(self):
        self.serial_interface_buffer = {button: self.serial_sensitive_interface[button]["state"]
                                        for button in self.serial_sensitive_interface}
        for button in self.serial_sensitive_interface:
            self.serial_sensitive_interface[button].configure(state="disabled")

    def ui_serialBreakSuspend(self):
        if self.serial_interface_buffer:
            for button in self.serial_sensitive_interface:
                self.serial_sensitive_interface[button].configure(state=self.serial_interface_buffer[button])
            self.serial_interface_buffer = {}
        else:
            raise RuntimeError("Button states not saved.")

    def ui_disableSpeedIndicators(self):
        self.interface["speed_slider1"].configureState(state="disabled")
        self.interface["speed_slider2"].configureState(state="disabled")

    def ui_enableSpeedIndicators(self):
        self.interface["speed_slider1"].configureState(state="normal")
        self.interface["speed_slider2"].configureState(state="normal")

    def ui_deviceConnected(self):
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["connect"].configure(state="disabled")
        self.ui_enableRun()
        self.ui_wateringEnable()

    def ui_runHandler(self):
        self.ui_disableCommandButtons()
        self.ui_disableSpeedIndicators()
        self.ui_serialSuspend()

    def ui_abortHandler(self):
        self.ui_disableCommandButtons()

    def ui_pauseHandler(self):
        self.ui_disableCommandButtons()
        self.ui_serialSuspend()

    def ui_resumeHandler(self):
        self.serial_sensitive_interface["resume"].configure(state="disabled")
        self.serial_sensitive_interface["pause"].configure(state="normal")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_homeHandler(self):
        pass

    def ui_disableCommandButtons(self):
        self.serial_sensitive_interface["disconnect"].configure(state="disabled")
        self.serial_sensitive_interface["abort"].config(state="disabled")
        self.serial_sensitive_interface["run"].config(state="disabled")
        self.serial_sensitive_interface["pause"].config(state="disabled")
        self.serial_sensitive_interface["resume"].config(state="disabled")
        self.serial_sensitive_interface["echo"].config(state="disabled")
        self.serial_sensitive_interface["home"].config(state="disabled")

    def ui_enableStop(self):
        self.ui_serialBreakSuspend()
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["pause"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_enableRun(self):
        self.serial_sensitive_interface["run"].config(state="normal")
        self.serial_sensitive_interface["home"].config(state="normal")
        self.serial_sensitive_interface["echo"].config(state="normal")
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.ui_enableSpeedIndicators()

    def ui_enableResume(self):
        self.ui_serialBreakSuspend()
        self.serial_sensitive_interface["disconnect"].configure(state="normal")
        self.serial_sensitive_interface["resume"].configure(state="normal")
        self.serial_sensitive_interface["pause"].configure(state="disabled")
        self.serial_sensitive_interface["abort"].configure(state="normal")
        self.serial_sensitive_interface["echo"].configure(state="normal")

    def ui_disablePumpIndicators(self):
        self.interface["water_slider1"].configureState(state="disabled")
        self.interface["time_slider1"].configureState(state="disabled")

    def ui_enablePumpIndicators(self):
        self.interface["water_slider1"].configureState(state="normal")
        self.interface["time_slider1"].configureState(state="normal")

    def ui_wateringStarted(self):
        self.serial_sensitive_interface["force"].configure(state="normal")
        self.serial_sensitive_interface["stop"].configure(state="normal")
        self.serial_sensitive_interface["start"].configure(state="disabled")
        self.interface["time_slider1"].configureState(state="disabled")
        self.interface["water_slider1"].configureState(state="disabled")

    def ui_wateringStopped(self):
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="normal")
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.interface["time_slider1"].configureState(state="normal")
        self.interface["water_slider1"].configureState(state="normal")

    def ui_wateringReset(self):
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="disabled")
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.interface["water_slider1"].configureState(state="disabled")
        self.interface["time_slider1"].configureState(state="disabled")
        self.interface["time_slider1"].reset()
        self.interface["water_slider1"].reset()

    def ui_wateringButtonsDisable(self):
        self.serial_sensitive_interface["force"].configure(state="disabled")
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="disabled")

    def ui_wateringEnable(self):
        self.serial_sensitive_interface["stop"].configure(state="disabled")
        self.serial_sensitive_interface["start"].configure(state="active")
        self.interface["water_slider1"].configureState(state="normal")
        self.interface["time_slider1"].configureState(state="normal")

    def ui_serverEnable(self):
        self.interface["start_server"].configure(state="disabled")
        self.interface["close_server"].configure(state="normal")

    def ui_serverDisable(self):
        self.interface["start_server"].configure(state="normal")
        self.interface["close_server"].configure(state="disabled")

    def ui_lightingEnable(self):
        self.interface["light_slider1"].configureState(state="normal")

    def ui_lightingDisable(self):
        self.interface["light_slider1"].configureState(state="disabled")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.params = properties.AppProperties()
        self.variables = properties.AppVariables()
        self.trackers = properties.AppTrackers()
        self.flags = properties.AppFlags()
        self.data_buffers = properties.DataBuffers()

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
        self.params["server"].attachReceiveQueue(self.get_queue)
        self.params["server"].attachResponseQueue(self.put_queue)

        self.interface_manager = InterfaceManager(self)
        self.interface_manager.pack(expand=True)

    def destroy(self):

        if self.params["server"].running:
            self.params["server"].closeServer()

        if self.params["device"]:
            self.params["device"].close_serial()

        super().quit()

    def clearQueues(self):
        with self.get_queue.mutex:
            self.get_queue.queue.clear()

        with self.put_queue.mutex:
            self.put_queue.queue.clear()

    def resetDataBuffers(self):
        self.data_buffers = properties.DataBuffers()

    def programLoop(self):

        if self.flags["plotting"] and not self.get_queue.empty():
            self.params["plotter"].updateData()

        if self.params["device"] and self.flags["pumping"]:

            now_time = time.time()

            if self.flags["prev_pumping_flag_state"] != self.flags["pumping"]:
                self.trackers["seconds"] = now_time
                self.trackers["pump_time"] = now_time

            if now_time - self.trackers["seconds"] >= 1:
                time_left = self.variables["time1"].get()*60 - (now_time - self.trackers["pump_time"])
                mins = int(time_left//60)
                secs = int(time_left - mins*60)
                self.variables["time_left_str"].set(f"{mins:02d}:{secs:02d}")
                self.trackers["seconds"] = now_time

            if (now_time - self.trackers["pump_time"])/60 >= self.variables["time1"].get():
                self.interface_manager.pump_control.forceWateringCycle()
                self.trackers["pump_time"] = now_time

        self.flags["prev_pumping_flag_state"] = self.flags["pumping"]

        self.after(1, self.programLoop)


if __name__ == "__main__":
    root = App()
    root.resizable(False, False)
    #root.geometry("1100x800")
    root.title("Clinostat control system")
    # root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
