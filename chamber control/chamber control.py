import sensors
import socket
import time
import yaml
import smbus

HEADER_SIZE = 10

with open("chamber_config.yaml", "r") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

main_i2c_bus = smbus.SMBus(1)

address = config["IP"]
port = config["PORT"]

running = True

grav_sensor = sensors.LIS3DHAccelerometer(config["GRAV"],main_i2c_bus)
grav_sensor.enable()

while running:

    # Once per 20min take a picture of chamber inside with flash.
    # One per 10 min make a humidity measurement.

    # Read sensors

    # message scheme:
    # grav_x;grav_y;grav_z;temp1;temp2;temp3;light1;light2;humidity;time since last humidity test

    # formulate message, ';' delimiter
    vals = grav_sensor.readAllAxes()
    msg = ";".join([str(val) for val in vals]) + "\n"
    msg = f'{len(msg):<{HEADER_SIZE}}' + msg
    print(msg)

    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sc:
        sc.settimeout(10)
        try:
            sc.connect((address, port))
        except socket.timeout:
            print("Connection timed out.")
            running = False
        sc.sendall(msg.encode())
    time.sleep(0.1)
