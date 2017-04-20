import itertools
import sched


class _KillScheduler(Exception):
    pass


class Scheduler(object):
    def __init__(self):
        self.current = 0
        self.count = itertools.count()
        self.scheduler = sched.scheduler(self.current_time, self.advance_time)

    def __enter__(self):
        self.reset()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.run()
        self.reset()

    def reset(self):
        self.current = 0

    def current_time(self):
        return self.current

    def advance_time(self, units):
        self.current += units

    def add(self, delay, event, handler):
        return self.scheduler.enter(delay, next(self.count), handler, [event])

    def cancel(self, event):
        self.scheduler.cancel(event)

    def run(self):
        self.scheduler.run()

    def run_until(self, delay):
        self.scheduler.enter(delay, next(self.count), self._kill)
        try:
            self.run()
        except _KillScheduler:
            self.reset()

    @staticmethod
    def _kill():
        raise _KillScheduler()
