import time


class AppProperties(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("device", None)
        self.__setitem__("plotter", None)
        self.__setitem__("server", None)


class AppVariables(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("time1", None)
        self.__setitem__("time_left_str", None)
        self.__setitem__("water1", None)
        self.__setitem__("address", None)


class AppTrackers(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("seconds", time.time())
        self.__setitem__("pump_time", time.time())


class AppFlags(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("pumping", False)
        self.__setitem__("plotting", False)
        self.__setitem__("prev_pumping_flag_state", False)
        self.__setitem__("new_data_present", False)


class DataBuffers(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("grav_components", [[], [], []])
        self.__setitem__("grav_means", [[], [], []])
        # self.__setitem__("temps", [[], [], []])
        # self.__setitem__("humidity", [[]])
        # self.__setitem__("light", [[]])
        # self.__setitem__("time_humidity", [[]])
