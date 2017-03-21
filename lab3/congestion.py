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
    def send_successful(self, num_bytes: int):
        pass

    @abstractmethod
    def send_failed(self, num_bytes: int, dup_acks=0):
        pass

    @abstractproperty
    def max_outstanding(self) -> int:
        pass

    @abstractproperty
    def skip_sending(self) -> int:
        pass


class NoCongestionControl(CongestionControl):
    @property
    def skip_sending(self) -> int:
        return 0

    @property
    def max_outstanding(self) -> int:
        return sys.maxsize

    def send_successful(self, num_bytes: int):
        pass

    def send_failed(self, num_bytes: int, dup_acks=0):
        pass


class TCPTahoe(CongestionControl):
    def __init__(self, mss: int, threshold: int = 100000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mss = mss
        self.cwnd = mss
        self.threshold = threshold
        self.failed = False

    def send_successful(self, num_bytes: int):
        if self.cwnd < self.threshold:
            self.slow_start(num_bytes)
        else:
            self.additive_increase(num_bytes)

    def send_failed(self, num_bytes: int, dup_acks=0):
        if self.failed:
            self.trace('Still recovering')
        else:
            self.threshold = self.loss_threshold()
            self.trace('Loss, threshold = %d / 2 = %d, cwnd = %d' % (
                self.max_outstanding, self.threshold, self.mss))
            self.cwnd = self.mss
        self.failed = True

    def loss_threshold(self) -> int:
        return max(
            self.mss,
            self.align_mss(self.max_outstanding // 2),
        )

    def align_mss(self, num_bytes: int):
        return self.mss * (num_bytes // self.mss)

    @property
    def max_outstanding(self) -> int:
        return self.align_mss(self.cwnd)

    @property
    def skip_sending(self) -> int:
        return 0

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


class TCPReno(TCPTahoe):
    dup_acks = 0
    _skip = 0

    @property
    def max_outstanding(self) -> int:
        parent_val = super().max_outstanding
        if self.fast_recovery:
            val = parent_val + self.dup_acks * self.mss
            self.trace('In fast recovery, dup ACKs = %d, max outstanding = %d' % (self.dup_acks, val))
            return val
        return parent_val

    @property
    def skip_sending(self) -> int:
        if self._skip > 0:
            self.trace('Continue to skip %d outstanding bytes' % self._skip)
        return self._skip

    @property
    def fast_recovery(self) -> bool:
        return self.dup_acks > 0

    def send_successful(self, num_bytes: int):
        if num_bytes > 0 and self.fast_recovery:
            self.trace('Leaving fast recovery with %d bytes ACKed' % num_bytes)
            self.dup_acks = 0
        else:
            super().send_successful(max(0, num_bytes - (self._skip - self.mss)))
        self._skip = max(0, self._skip - num_bytes)
        if self._skip > 0:
            self.trace('Received %d bytes, new skip %d' % (num_bytes, self._skip))

    def send_failed(self, num_bytes: int, dup_acks=0):
        if dup_acks:
            if self.fast_recovery:
                self.trace('Already in fast recovery, dup ACKs = %d' % dup_acks)
            else:
                self.trace('Loss with duplicate ACKs, entering fast recovery')
                self._skip = num_bytes
                max_outstanding = self.max_outstanding
                self.threshold = self.cwnd = self.loss_threshold()
                self.trace('Fast recovery, cwnd = threshold = %d / 2 = %d, %d skipped' % (
                    max_outstanding, self.threshold, self._skip))

            self.dup_acks = dup_acks
        else:
            self.dup_acks = 0
            super().send_failed(num_bytes=num_bytes, dup_acks=0)
