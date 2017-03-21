import sys
from abc import ABCMeta, abstractmethod, abstractproperty

from src.sim import Sim


class CongestionControl(metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def trace(message):
        Sim.trace('Congestion', message=message)

    @abstractmethod
    def bytes_successful(self, num_bytes: int):
        pass

    @abstractmethod
    def bytes_failed(self, num_bytes: int, fast=False):
        pass

    @abstractproperty
    def max_outstanding(self) -> int:
        pass


class NoCongestionControl(CongestionControl):
    @property
    def max_outstanding(self) -> int:
        return sys.maxsize

    def bytes_successful(self, num_bytes: int):
        pass

    def bytes_failed(self, num_bytes: int, fast=False):
        pass


class TCPTahoe(CongestionControl):
    def __init__(self, mss: int, threshold: int = 100000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mss = mss
        self.cwnd = mss
        self.threshold = threshold

    def bytes_successful(self, num_bytes: int):
        if self.cwnd < self.threshold:
            self.slow_start(num_bytes)
        else:
            self.additive_increase(num_bytes)

    def bytes_failed(self, num_bytes: int, fast=False):
        self.threshold = max(
            self.mss,
            (self.max_outstanding // 2 // self.mss) * self.mss
        )
        self.trace('Loss, threshold = %d / 2 = %d, cwnd = %d' % (
            self.max_outstanding, self.threshold, self.mss))
        self.cwnd = self.mss

    @property
    def max_outstanding(self) -> int:
        return self.mss * (self.cwnd // self.mss)

    def slow_start(self, num_bytes: int):
        increase = min(num_bytes, self.mss)
        self.cwnd += increase
        self.trace('Slow start increase by %d to %d' % (increase, self.cwnd))
        if self.cwnd >= self.threshold:
            self.trace('Slow start hit threshold of %d' % self.threshold)
            self.cwnd = self.threshold

    def additive_increase(self, num_bytes: int):
        increase = num_bytes * self.mss // self.cwnd
        self.cwnd += increase
        self.trace('Additive increase by %d to %d' % (increase, self.cwnd))
