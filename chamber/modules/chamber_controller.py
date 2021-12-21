import queue
import sensors
import socket
import time
import yaml
import smbus
from threading import Thread
from typing import Optional
import gpiozero
import os
import datetime

#  todo: Add a graceful shutdown.


class ChamberController:

    __slots__ = {"_cameras",
                 "_sensors_short_read",
                 "_sensors_long_read",
                 "_i2c_bus",
                 "_sensors_driver_pin",
                 "_light_panel",
                 "_server_config",
                 "_flags",
                 "_data_queue",
                 "_trackers",
                 "_current_run_images_dir"}

    PACKET_HEADER_SIZE = 10
    DEFAULT_SERVER_RESPONSE = "default"
    MOISTURE_LEVEL_MEASUREMENT_INTERVAL_MINS = 3
    MOISTURE_LEVEL_MEASUREMENT_SAMPLES = 100
    DATA_EXCHANGE_FREQUENCY_HZ = 5

    def __init__(self):
        self._i2c_bus: smbus.SMBus = smbus.SMBus(1)
        self._cameras: dict = {}
        self._sensors_driver_pin: Optional[gpiozero.Pin] = None
        self._sensors_long_read: dict = {}
        self._sensors_short_read: dict = {}
        self._light_panel: Optional[sensors.LightPanel] = None
        self._server_config: dict = {}
        self._data_queue = queue.Queue()
        self._flags = {"moisture_measurement_scheduled": False, "running": True}
        self._trackers: dict = {"last_measurement_timestamp": time.time(), "current_timestamp": time.time()}
        self._current_run_images_dir: Optional[str] = None

    def attach_camera(self, camera: sensors.Camera):
        self._cameras[camera.name()] = camera

    def load_sensors(self):

        with open("../config/chamber_config.yaml", "r") as fl:
            temp_config = yaml.load(fl, Loader=yaml.FullLoader)

        self._sensors_short_read["GRAV"] = sensors.LIS3DHAccelerometer(temp_config["GRAV"], self._i2c_bus)
        self._sensors_long_read["ADC"] = sensors.ADS1115ADC(temp_config["ADC"], self._i2c_bus)
        self._sensors_short_read["TEMP1"] = sensors.MCP9808Thermometer(temp_config["TEMP1"], self._i2c_bus)
        self._sensors_short_read["TEMP2"] = sensors.MCP9808Thermometer(temp_config["TEMP2"], self._i2c_bus)
        self._sensors_short_read["TEMP3"] = sensors.MCP9808Thermometer(temp_config["TEMP3"], self._i2c_bus)

        for (key, sensor) in self._sensors_short_read:
            sensor.enable()

    def start(self):
        if self._server_config:
            if "images" not in os.listdir():
                os.mkdir("images")
            self._flags["running"] = True
            self._control_loop()
        else:
            raise RuntimeError("Add server connection using the add_server_connection method.")

    def _control_loop(self):

        measurement_index = 0
        gravity_avg = [0, 0, 0]

        while True:
            while True:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sc:

                    if measurement_index == 1:
                        date = str(datetime.datetime.now()).replace(" ", "-").replace(":", "-").replace(".", "-")
                        self._current_run_images_dir = "images/run_" + date
                        os.mkdir(self._current_run_images_dir)

                    sc.settimeout(5)
                    try:
                        print(f"Attempting connection to {self._server_config['IP']}")
                        sc.connect((self._server_config["IP"], self._server_config["PORT"]))
                    except socket.timeout:
                        print("Connection timed out.")
                        break
                    except ConnectionRefusedError:
                        measurement_index = 0
                        gravity_avg = [0, 0, 0]  # Resetting the gravity averages.
                        self._current_run_images_dir = None
                        self._flags["moisture_measurement_scheduled"] = False
                        print("Connection refused, reconnection attempt in 5s.")
                        time.sleep(5)
                        break  # Here interrupt the forever loop and continue to watch for the connection.

                    self._trackers["current_timestamp"] = time.time()
                    if self._trackers["current_timestamp"] - self._trackers["last_measurement_timestamp"] >= 0.5 * 60\
                            and self._sensors_driver_pin:
                        print("Scheduling saturation measurement.")
                        Thread(target=self._moisture_measurement, args=(self._data_queue,))
                        self._trackers["last_measurement_timestamp"] = self._trackers["current_timestamp"]

                    sensor_values = []
                    for (key, sensor) in self._sensors_short_read:
                        sensor_values += sensor.read()

                    if not self._data_queue.empty():
                        moisture_level = self._data_queue.get()
                        sensor_values += [moisture_level]
                        self._data_queue.task_done()
                    else:
                        sensor_values += [-100]

                    accel_values = sensor_values[0]
                    gravity_avg = [gravity_avg[ind] * measurement_index / (measurement_index + 1) + accel_values[ind] /
                                   (measurement_index + 1) for ind in range(3)]
                    measurement_index += 1

                    sensor_values.insert(1, gravity_avg)

                    msg = ";".join([str(val) for val in sensor_values]) + "\n"
                    msg = f'{len(msg):<{ChamberController.PACKET_HEADER_SIZE}}' + msg

                    fresh = True
                    try:
                        sc.sendall(msg.encode())
                    except BrokenPipeError:
                        measurement_index = 0
                        gravity_avg = [0, 0, 0]
                        self._current_run_images_dir = None
                        self._flags["moisture_measurement_scheduled"] = False
                        break

                    server_response = ""

                    while True:
                        raw_data_received = sc.recv(ChamberController.PACKET_HEADER_SIZE)
                        raw_data_received = raw_data_received.decode('utf-8')

                        if fresh:
                            packet_size = int(raw_data_received[:ChamberController.PACKET_HEADER_SIZE])
                            fresh = False
                            server_response += raw_data_received[ChamberController.PACKET_HEADER_SIZE:]
                        else:
                            server_response += raw_data_received

                        if len(server_response) == packet_size:
                            break
                    response_components = server_response.split(";")
                    if response_components[0] != ChamberController.DEFAULT_SERVER_RESPONSE and self._light_panel:
                        self._light_panel.set_intensity(response_components[0], response_components[1])
                        print("Adjusting lighting... ", int(response_components[0]), int(response_components[1]))

                    time.sleep(1./ChamberController.DATA_EXCHANGE_FREQUENCY_HZ)

    def add_light_control(self, pin_red: int, pin_blue: int) -> None:
        self._light_panel = sensors.LightPanel(pin_red, pin_blue)

    def add_server_connection(self, ip_address: Optional[str] = None, port: Optional[int] = None) -> None:
        if not ip_address or not port:
            with open("../config/chamber_config.yaml", "r") as fl:
                temp_config = yaml.load(fl, Loader=yaml.FullLoader)

            self._server_config["IP"] = temp_config["IP"]
            self._server_config["PORT"] = temp_config["PORT"]

        else:
            self._server_config["IP"] = ip_address
            self._server_config["PORT"] = port

    def add_worker_pin(self, pin: int) -> None:
        self._sensors_driver_pin = gpiozero.Pin(pin)
        self._sensors_driver_pin.off()

    def take_pictures(self) -> None:
        for (key, camera) in self._cameras:
            camera.capture_frame(self._current_run_images_dir)

    def _moisture_measurement(self, fake: bool = False) -> None:
        sum_ = 0
        self._sensors_driver_pin.on()
        for i in range(ChamberController.MOISTURE_LEVEL_MEASUREMENT_SAMPLES):
            if not fake:
                sum_ += self._sensors_long_read["ADC"].read(channel=0)
            else:
                sum_ += sensors.ADS1115ADC.fake_read()
            time.sleep(3. / ChamberController.MOISTURE_LEVEL_MEASUREMENT_SAMPLES)
        self._sensors_driver_pin.off()

        self._data_queue.put(sum_ / ChamberController.MOISTURE_LEVEL_MEASUREMENT_SAMPLES)
