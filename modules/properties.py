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
        self.__setitem__("pumping", False)


class AppTrackers(dict):
    def __init__(self):
        super().__init__()
        self.__setitem__("seconds", time.time())
        self.__setitem__("pump_time", time.time())
        self.__setitem__("prev_pumping_flag_state", False)

