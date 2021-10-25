import time
from collections.abc import MutableMapping


class ProgramProperties(MutableMapping):

    def __setitem__(self, key, value):
        if key in self.__slots__:
            setattr(self, key, value)
        else:
            raise KeyError

    def __delitem__(self, key):
        pass

    def __getitem__(self, key):
        return getattr(self, key)

    def __len__(self):
        return len(self.__slots__)

    def __iter__(self):
        return iter(self.__slots__)


class AppProperties(ProgramProperties):

    __slots__ = (
        "device",
        "plotter",
        "server"
    )

    def __init__(self):
        for atr in self.__slots__:
            setattr(self, atr, None)


class AppVariables(ProgramProperties):

    __slots__ = (
        "time1",
        "time_left_str",
        "water1",
        "address",
        "speed1",
        "speed2"
    )

    def __init__(self):
        for atr in self.__slots__:
            setattr(self, atr, None)


class AppTrackers(ProgramProperties):

    __slots__ = (
        "seconds",
        "pump_time"
    )

    def __init__(self):
        for atr in self.__slots__:
            setattr(self, atr, time.time())


class AppFlags(ProgramProperties):

    __slots__ = (
        "pumping",
        "plotting",
        "prev_pumping_flag_state",
        "new_data_present"
    )

    def __init__(self):
        for atr in self.__slots__:
            setattr(self, atr, False)


class DataBuffers(ProgramProperties):

    __slots__ = (
        "grav_components",
        "grav_means",
        "temperatures",
        "humidity"
    )

    def __init__(self):

        self.MEASUREMENT_NUM_DEFAULT = 300
        self._default_primer = [0 for _ in range(self.MEASUREMENT_NUM_DEFAULT)]

        self.HUMID_MEASUREMENT_NUM = 10
        self._humid_primer = [0 for _ in range(self.HUMID_MEASUREMENT_NUM)]

        setattr(self, "grav_components", [self._default_primer, self._default_primer, self._default_primer])
        setattr(self, "grav_means", [self._default_primer, self._default_primer, self._default_primer])
        setattr(self, "temperatures", [self._default_primer, self._default_primer, self._default_primer])
        setattr(self, "humidity", [self._humid_primer])
        # setattr(self, "light", [[]])
        # setattr(self, "time_humidity", [[]])
