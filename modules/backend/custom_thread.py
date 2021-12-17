import threading
from typing import Optional, Callable
from modules.backend.clinostat_com import ClinostatCommunicationError


class ClinostatSerialThread(threading.Thread):
    def __init__(self, serial_lock: threading.Lock,
                 at_start: Optional[Callable] = None,
                 at_success: Optional[Callable] = None,
                 at_fail: Optional[Callable] = None,
                 **kwargs):

        super().__init__(**kwargs)
        self._at_success = at_success
        self._at_fail = at_fail
        self._at_start = at_start
        self.lock = serial_lock

    def run(self):

        self.lock.acquire()
        failed = False
        if self._at_start:
            self._at_start()

        try:
            if self._target:
                self._target(*self._args, **self._kwargs)

        except ClinostatCommunicationError:
            failed = True
            if self._at_fail:
                self._at_fail()

        finally:
            if not failed and self._at_success:
                self._at_success()
            self.lock.release()
            del self._target, self._args, self._kwargs