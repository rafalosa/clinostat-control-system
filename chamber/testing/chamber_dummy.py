import socket
import yaml
import time
from queue import Queue
from chamber.modules import sensors
from threading import Thread

# todo: Wrap this whole program into a class to avoid global variables.


def measurement_dummy(q):
    num = 30
    sum_ = 0

    for i in range(num):
        sum_ += sensors.ADS1115ADC.fake_read()
        time.sleep(0.05)

    q.put(sum_ / num)


HEADER_SIZE = 10

with open("../config/chamber_config.yaml", "r") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

address = config["IP"]
port = config["PORT"]

index = 0
means = [0, 0, 0]
saturation_measurement_scheduled = False
last_measurement_timestamp = time.time()
current_timestamp = time.time()
saturation_queue = Queue()

while True:

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sc:

            sc.settimeout(10)
            try:
                sc.connect((address, port))
            except socket.timeout:
                print("Connection timed out.")
                break
            except ConnectionRefusedError:

                print("Connection refused, reconnection attempt in 5s.")
                index = 0
                means = [0, 0, 0]
                saturation_measurement_scheduled = False
                time.sleep(5)
                break
            except OSError:
                print("Network unreachable, reconnecting in 5s.")
                index = 0
                means = [0, 0, 0]
                saturation_measurement_scheduled = False
                time.sleep(5)
                break

            current_timestamp = time.time()

            if current_timestamp - last_measurement_timestamp >= 0.01*60:

                Thread(target=measurement_dummy, args=(saturation_queue,)).start()
                last_measurement_timestamp = current_timestamp

            accel_values = sensors.LIS3DHAccelerometer.fake_read()
            temp = [means[ind] * index / (index + 1) + accel_values[ind] / (index + 1) for ind in range(3)]
            index += 1
            means = temp
            sensor_values = accel_values + means
            temperatures = [sensors.MCP9808Thermometer.fake_read() for _ in range(3)]
            sensor_values += temperatures

            if not saturation_queue.empty():
                val = saturation_queue.get()
                sensor_values += [val]
                saturation_queue.task_done()

            else:
                sensor_values += [-100]

            msg = ";".join([str(val) for val in sensor_values]) + "\n"
            msg = f'{len(msg):<{HEADER_SIZE}}' + msg

            fresh = True
            try:
                sc.sendall(msg.encode())
            except BrokenPipeError:
                index = 0
                means = [0, 0, 0]
                saturation_measurement_scheduled = False
                break

            response = ""

            while True:
                data = sc.recv(HEADER_SIZE)
                data = data.decode('utf-8')

                if fresh:
                    size = int(data[:HEADER_SIZE])
                    fresh = False
                    response += data[HEADER_SIZE:]
                else:
                    response += data

                if len(response) == size:
                    break
            response_components = response.split(";")
            if response_components[0] != "default":
                # Adjust lighting
                # print("adjusting lighting", int(response_components[0]), int(response_components[1]))
                pass

            time.sleep(0.2)
