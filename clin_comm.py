import serial
import time
import serial.serialutil


def tryConnection(port):
    try:
        test_serial = serial.Serial(port,baudrate=115200,timeout=2)
    except serial.serialutil.SerialException:
        return False
    test_serial.write(b'\x08')
    time.sleep(0.001)
    received = test_serial.read(1)
    test_serial.close()
    if received == b'\x01':
        return True
    else:
        return False


class Clinostat:

    def __init__(self,port_name):

        self._baud = 115200
        self._port = serial.Serial(port_name,self._baud,timeout=2)
        self.port_name = port_name
        self._RUN = b'\x01'
        self._HOME = b'\x02'
        self._ABORT = b'\x03'
        self._PAUSE = b'\x04'
        self._RESUME = b'\x05'
        self._ECHO = b'\x09'

    def echo(self) -> None:  # Mode byte: b'\x09'.
        # Check if device is responding. Maybe return current mode.
        pass

    def run(self,RPMs:tuple) -> bool:  # time:float): # Mode byte: b'\x01'.
        # Send mode + RPM1 + RPM2, maybe run for some amount of time?
        # listen for response, return true if controller responded correctly
        pass

    def home(self) -> bytes:  # Mode byte: b'\x02'.
        # Home clinostat, and set new 0 if necessary.
        # listen for response, return true if controller responded correctly
        pass

    def abort(self) -> bytes:  # Mode byte: b'\x03'.
        # self._port.write(b'\x03')
        # listen for response, return true if controller responded correctly
        pass

    def pause(self) -> bytes:  # Mode byte: b'\x04'.
        # Send mode and stop steppers, check for flags if the clinostat is homed or aborted.
        # listen for response, return true if controller responded correctly
        pass

    def resume(self) -> bytes:  # Mode byte: b'\x05'.
        # resume run with previously set speeds, check for flag if paused first.
        # listen for response, return true if controller responded correctly
        pass

    def close_serial(self) -> None:
        self._port.close()
