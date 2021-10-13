import threading
from typing import Union, Optional, Callable


class SuccessThread(threading.Thread):
    def __init__(self, at_success: Optional[Callable] = None, at_fail: Optional[Callable] = None,
                 exception_: Optional[Exception] = None, **kwargs):
        super().__init__(**kwargs)
        self._at_success = at_success
        self._at_fail = at_fail
        self._exception = exception_
        if not exception_:
            raise AttributeError

    def run(self):
        failed = False
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)

        except self._exception:
            failed = True
            if self._at_fail:
                self._at_fail()

        finally:
            if not failed and self._at_success:
                self._at_success()
            del self._target, self._args, self._kwargs