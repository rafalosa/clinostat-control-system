import tkinter as tk
from tkinter import Grid
from modules import data_socket
from modules.segments import SerialConfig, DataEmbed, PumpControl, ModeMenu
import threading
import yaml
import queue
import os
import tkinter.ttk as ttk
import time
import math


# todo: Rewrite most of the program to avoid re verse calls like self.master.master.master.device.pause.
# The above is due to the change in the program architecture which wasn't planned in this form in the beginning.

# todo: Add chamber environment control and monitoring (scheduling water pumps, lighting settings, temperature monitor)


class ClinostatControlSystem(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.serial_buttons = []
        self.saved_button_states = []

        self.main_tabs = ttk.Notebook(self)

        self.motors_tab = tk.Frame(self)

        self.serial_config = SerialConfig(self.motors_tab, text="Controller connection")
        self.mode_options = ModeMenu(self.motors_tab, text="Motors control")
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
        self.pump_control.disableWateringUI()

    def suspendSerialUI(self):
        self.saved_button_states = [button["state"] for button in self.serial_buttons]
        for button in self.serial_buttons:
            button.configure(state="disabled")

    def breakSuspendSerialUI(self):
        for button,state_ in zip(self.serial_buttons,self.saved_button_states):
            button.configure(state=state_)

    def blockIndicators(self):
        self.mode_options.disableIndicators()

    def enableStart(self):
        self.mode_options.enableRun()
        self.pump_control.enableWateringUI()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.device = None
        self.running = True
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

        with open("config/config.yaml", "r") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

        self.lock = threading.Lock()
        self.data_queue = queue.Queue()
        self.kill_server = threading.Event()
        self.server = data_socket.DataServer(parent=self, queue_=self.data_queue,
                                             address=config["IP"], port=config["PORT"],
                                             thread_lock=self.lock)
        
        self.control_system = ClinostatControlSystem(self)
        self.control_system.pack()

        self.server.linkConsole(self.control_system.data_embed.console)

    def destroy(self):

        if self.server.running:
            self.server.closeServer()

        if self.device:
            self.device.close_serial()

        self.running = False

        super().quit()

    def programLoop(self):

        if self.control_system.data_embed.plotting_flag and not self.data_queue.empty():
            self.control_system.data_embed.updateData()

        if self.device and self.control_system.pump_control.cycle_active:

            now_time = time.time()

            if self.pump_flag_previous_state != self.control_system.pump_control.cycle_active:
                self.seconds_tracker = now_time
                self.pumps_tracker = now_time

            if now_time - self.seconds_tracker >= 1:
                time_left = self.control_system.pump_control.time_slider.getValue()*60 - (now_time - self.pumps_tracker)
                mins = math.floor(time_left/60)
                secs = math.floor(time_left - mins*60)
                self.control_system.pump_control.time_left_var.set(f"{mins:02d}:{secs:02d}")
                print(time_left)
                self.seconds_tracker = now_time

            if (now_time - self.pumps_tracker)/60 >= self.control_system.pump_control.time_slider.getValue():
                self.control_system.pump_control.forceWateringCycle()
                self.pumps_tracker = now_time

        self.pump_flag_previous_state = self.control_system.pump_control.cycle_active
        if self.running:
            self.after(100, self.programLoop)


if __name__ == "__main__":
    root = App()
    root.resizable(False, False)
    root.title("Clinostat control system")
    #root.iconbitmap("icon/favicon.ico")
    root.after(1, root.programLoop)
    root.mainloop()
