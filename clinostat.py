import serial


class Clinostat:

    def __init__(self,port_name,baud_rate):

        self.__baud = baud_rate
        self.__port = serial.Serial(port_name,self.__baud,timeout=2)
        self.__RUN = b'\x01'
        self.__HOME = b'\x02'
        self.__ABORT = b'\x03'
        self.__PAUSE = b'\x04'
        self.__RESUME = b'\x05'
        self.__ECHO = b'\x09'

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
