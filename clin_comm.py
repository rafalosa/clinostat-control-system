import serial
import time


def tryConnection(port):

    test_serial = serial.Serial(port,baudrate=115200,timeout=2)
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
        self._port_name = port_name
        self._RUN = b'\x01'
        self._HOME = b'\x02'
        self._ABORT = b'\x03'
        self._PAUSE = b'\x04'
        self._RESUME = b'\x05'
        self._ECHO = b'\x09'

    def echo(self) -> None:  # Mode byte: b'\x09'.
        # Check if device is responding. Maybe return current mode.
        pass

    def run(self,RPM1:float,RPM2:float) -> None:  # time:float): # Mode byte: b'\x01'.
        # Send mode + RPM1 + RPM2, maybe run for some amount of time?
        pass

    def home(self) -> None:  # Mode byte: b'\x02'.
        # Home clinostat, and set new 0 if necessary.
        pass

    def abort(self) -> None:  # Mode byte: b'\x03'.
        # Stop clinostat.
        pass

    def pause(self) -> None:  # Mode byte: b'\x04'.
        # Send mode and stop steppers, check for flags if the clinostat is homed or aborted.
        pass

    def resume(self) -> None:  # Mode byte: b'\x05'.
        # resume run with previously set speeds, check for flag if paused first.
        pass

    def setHome(self):
        # Maybe allow user to set a new home position (?)
        pass

    def close_serial(self):
        self._port.close()
