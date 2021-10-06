import threading

# todo: Add another function to call at exception.


class SuccessThread(threading.Thread):
    def __init__(self, at_success=None, exception_=None,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._at_success = at_success
        self._exception = exception_
        self._failed = False
        if not exception_:
            raise AttributeError

    def run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)

        except self._exception:
            self._failed = True

        finally:
            if not self._failed and self._at_success:
                self._at_success()
            del self._target, self._args, self._kwargs