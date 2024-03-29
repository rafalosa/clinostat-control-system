import serial
import time
import serial.serialutil
from serial.tools import list_ports
import struct
from time import sleep
from typing import Tuple


class Clinostat:

    # Commands that can be sent to device.

    _RUN = b'\x01'
    _HOME = b'\x02'
    _ABORT = b'\x03'
    _PAUSE = b'\x04'
    _RESUME = b'\x05'
    _ECHO = b'\x06'
    _CONNECT = b'\x07'
    _DISCONNECT = b'\x08'
    _WATERING = b'\x09'

    # Commands received from device.

    _CONNECTED = b'\x01'
    _TOP_SPEED = b'\x02'
    _STARTING = b'\x03'
    _STOPPING = b'\x04'
    _STOPPED = b'\x05'
    _RUNNING_STATE = b'\x06'
    _STOPPING_STATE = b'\x07'
    _IDLE_STATE = b'\x08'
    _PUMPING_STARTED = b'\x09'
    _STILL_PUMPING = b'\x0a'

    def __init__(self, port_name):

        self._baud = 57600
        self._port = serial.Serial(port_name, self._baud, timeout=2)
        self.port_name = port_name
        self.console = None
        self.res = False

    def echo(self) -> None:
        try:
            self._port.write(Clinostat._ECHO)
        except serial.SerialException as err:
            self.console.println("Device cannot be reached. Check USB cable and update serial ports.",
                                 headline="SERIAL ERROR: ", msg_type="ERROR")
            raise ClinostatCommunicationError("Device disconnected.")
        sleep(0.1)

        try:
            response = self._port.read(1)

        except serial.SerialTimeoutException:
            self.console.println("Device did not respond.", headline="SERIAL ERROR: ", msg_type="ERROR")
            raise ClinostatCommunicationError("Device didn't respond.")
        except serial.SerialException:
            self.console.println("Device cannot be reached. Check USB cable and update serial ports.",
                                 headline="SERIAL ERROR: ", msg_type="ERROR")
            raise ClinostatCommunicationError("Device has been disconnected.")

        message = "Device is currently "

        if response == Clinostat._RUNNING_STATE:
            message += "running."
        elif response == Clinostat._IDLE_STATE:
            message += "idle."
        elif response == Clinostat._STOPPING_STATE:
            message += "stopping"

        self.console.println(message, headline="CONTROLLER: ", msg_type="CONTROLLER")

    def run(self, rpm: Tuple[float, ...]):
        # Sends mode ID and 8 more bytes containing 2 floats for the speed.
        # listen for response, return true if controller responded correctly
        self.res = False
        values = [r for r in rpm]
        message = Clinostat._RUN
        for speed in values[:2]:
            message += bytes(bytearray(struct.pack("f", speed)))

        # message = message[0:1] + message[:0:-1]

        for byte in message:
            try:
                self._port.write(byte.to_bytes(1, 'little'))
            except serial.SerialException:
                self.console.println("Device cannot be reached. Check USB cable and update serial ports.",
                                     headline="SERIAL ERROR: ", msg_type="ERROR")
                raise ClinostatCommunicationError("Serial exception error.")
            sleep(0.1)
        try:
            response = self._port.read(1)
        except serial.SerialTimeoutException:
            raise ClinostatCommunicationError("Device didn't respond.")
        except serial.SerialException:
            raise ClinostatCommunicationError("Device has been disconnected.")
        if response == Clinostat._STARTING:
            self.console.println("Starting motors.", headline="CONTROLLER: ", msg_type="CONTROLLER")

        else:
            self.console.println("Received incorrect response, aborting.",
                                 headline="CONTROLLER ERROR: ", msg_type="CONTROLLER")
            raise ClinostatCommunicationError("Incorrect response.")

    def home(self):  # Mode byte: b'\x02'.
        # Home clinostat, and set new 0 if necessary.
        # listen for response, return true if controller responded correctly
        pass

    def abort(self):  # Mode byte: b'\x03'.

        self.handle_command(Clinostat._ABORT, response=False)
        if not self.res:
            rcv = b''
            while rcv != Clinostat._STOPPED:
                rcv = self._port.read(1)
            self.console.println("Motors have stopped.", headline="CONTROLLER: ", msg_type="CONTROLLER")
            self.res = False

    def pause(self):  # Mode byte: b'\x04'.

        self.handle_command(Clinostat._PAUSE, response=False)
        rcv = b''
        while rcv != Clinostat._STOPPED:
            try:
                rcv = self._port.read(1)
            except serial.SerialException:
                self.console.println("Device cannot be reached. Check USB cable and update serial ports.",
                                     headline="CONTROLLER: ", msg_type="ERROR")
                raise ClinostatCommunicationError("Device disconnected.")

        self.console.println("Motors have stopped.", headline="CONTROLLER: ", msg_type="CONTROLLER")
        self.res = True

    def resume(self):  # Mode byte: b'\x05'.
        # resume run with previously set speeds, check for flag if paused first.
        # listen for response, return true if controller responded correctly
        self.handle_command(Clinostat._RESUME)
        self.res = False

    def disconnect(self):

        self._port.write(Clinostat._DISCONNECT)

    def close_serial(self):
        try:
            self.disconnect()
        except serial.serialutil.SerialException:
            raise ClinostatCommunicationError("Device cannot be reached. Check USB cable and update serial ports.")
        finally:
            try:
                self._port.close()
            except serial.SerialException:
                pass

    def link_console(self, console) -> None:
        self.console = console

    def handle_command(self, command, response=True):

        try:
            self._port.write(command)
        except serial.SerialException as err:
            self.console.println("Device cannot be reached. Check USB cable and update serial ports.",
                                 headline="SERIAL ERROR: ", msg_type="ERROR")
            raise ClinostatCommunicationError("Device out of reach.")
        sleep(0.1)
        if response:
            try:
                response = self._port.read(1)
                print(response)
            except serial.SerialTimeoutException:
                raise ClinostatCommunicationError("Device didn't respond.")
            msg = self._generate_message(response)
            self.console.println(msg, headline="CONTROLLER: ", msg_type="CONTROLLER")

    def dump_water(self, amount):

        message = Clinostat._WATERING
        message += bytes(bytearray(struct.pack("f", amount)))

        for byte in message:
            try:
                self._port.write(byte.to_bytes(1, 'little'))
            except serial.serialutil.PortNotOpenError:
                raise ClinostatCommunicationError("")
            except serial.SerialException as err:
                self.console.println(err.args[0], headline="SERIAL ERROR: ", msg_type="ERROR")
                raise ClinostatCommunicationError
            sleep(0.1)
        try:
            response = self._port.read(1)
            print(response)
        except serial.SerialTimeoutException:
            raise ClinostatCommunicationError("Device didn't respond.")
        if response == Clinostat._PUMPING_STARTED:
            self.console.println("Watering starting.", headline="CONTROLLER: ", msg_type="CONTROLLER")
        elif response == Clinostat._STILL_PUMPING:
            self.console.println("Previous watering process still running.",
                                 headline="CONTROLLER: ", msg_type="CONTROLLER")
        else:
            self.console.println("Received incorrect response, aborting.",
                                 headline="CONTROLLER ERROR: ", msg_type="ERROR")
            raise ClinostatCommunicationError("Incorrect response.")
            # todo: Actually add handling the mentioned abort.

    @staticmethod
    def _generate_message(response):

        if response == Clinostat._STOPPING:
            message = "Stopping motors."
        elif response == Clinostat._STARTING:
            message = "Starting motors."
        elif response == Clinostat._STOPPED:
            message = "Motors stopped."
        elif response == Clinostat._TOP_SPEED:
            message = "Motors have reached full speed."
        elif response == Clinostat._PUMPING_STARTED:
            message = "Watering started."
        elif response == Clinostat._STILL_PUMPING:
            message = "Previous watering cycle hasn't finished yet."
        else:
            message = "Unknown response."

        return message

    @staticmethod
    def try_connection(port):
        try:
            test_serial = serial.Serial(port, baudrate=57600, timeout=2)
        except serial.serialutil.SerialException:
            return False
        test_serial.write(Clinostat._CONNECT)
        time.sleep(0.001)
        received = test_serial.read(1)
        test_serial.close()
        if received == Clinostat._CONNECTED:
            return True
        else:
            return False


def get_ports() -> list:

    return [str(port).split(" ")[0] for port in serial.tools.list_ports.comports()]


class ClinostatCommunicationError(Exception):
    def __init__(self, message="Clinostat backend error."):
        self.message = message
        super().__init__()
