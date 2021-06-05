import sensors
import socket
import time
import yaml
import smbus

HEADER_SIZE = 10

with open("host_config.yaml", "r") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

main_i2c_bus = smbus.SMBus(1)

address = config["IP"]
port = config["PORT"]

running = True

grav_sensor = sensors.LIS3DHAccelerometer(0x18,main_i2c_bus)
grav_sensor.enable()

while running:

    # Read sensors

    # formulate message, ';' delimiter
    vals = grav_sensor.readAllAxes()
    msg = ";".join([str(val) for val in vals]) + "\n"
    msg = f'{len(msg):<{HEADER_SIZE}}' + msg
    print(msg)

    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sc:
        sc.connect((address, port))
        sc.sendall(msg.encode())
    time.sleep(0.1)


