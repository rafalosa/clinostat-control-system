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
        "grav_means"
    )

    def __init__(self):
        setattr(self, "grav_components", [[], [], []])
        setattr(self, "grav_means", [[], [], []])
        # setattr(self, "temps", [[], [], []])
        # setattr(self, "humidity", [[]])
        # setattr(self, "light", [[]])
        # setattr(self, "time_humidity", [[]])
