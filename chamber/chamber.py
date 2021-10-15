from modules import sensors
import socket
import time
import yaml
import smbus

HEADER_SIZE = 10

with open("config/chamber_config.yaml", "r") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

main_i2c_bus = smbus.SMBus(1)

address = config["IP"]
port = config["PORT"]

running = True

grav_sensor = sensors.LIS3DHAccelerometer(config["GRAV"], main_i2c_bus)
grav_sensor.enable()
index = 0
means = [0,0,0]

while running:

    # Once per 20min take a picture of chamber inside with flash.
    # One per 10 min make a humidity measurement.
    # message scheme:
    # grav_x;grav_y;grav_z;temp1;temp2;temp3;light1;light2;humidity;time since last humidity test

    # formulate message, ';' delimiter
    accel_vals = grav_sensor.read()
    accel_vals = [val/(2**16/4) for val in accel_vals]
    temp = [means[ind] * index / (index + 1) + accel_vals[ind] / (index + 1) for ind in range(3)]
    index += 1
    means = temp
    grav_values = accel_vals + means
    msg = ";".join([str(val) for val in grav_values]) + "\n"
    msg = f'{len(msg):<{HEADER_SIZE}}' + msg
    print(msg)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sc:
        sc.settimeout(10)
        try:
            sc.connect((address, port))
        except socket.timeout:
            print("Connection timed out.")
            running = False
            break
        except ConnectionRefusedError:
            break
        sc.sendall(msg.encode())
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
    time.sleep(0.2)
