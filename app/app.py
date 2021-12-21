from modules.properties import properties
from modules.backend import data_socket
from modules.gui.segments import *
import yaml
import queue
import os
import time
import ttkbootstrap


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
