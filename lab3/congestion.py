from abc import ABCMeta, abstractmethod, abstractproperty


class CongestionControl(metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def bytes_received(self, num_bytes: int):
        pass

    @abstractmethod
    def bytes_dropped(self, num_bytes: int, fast: bool = False):
        pass

    @abstractproperty
    def max_outstanding(self) -> int:
        pass


class TCPTahoe(CongestionControl):
    def __init__(self, mss=None, threshold=10000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mss = mss
        self.cwnd = mss
        self.threshold = threshold

    def bytes_received(self, num_bytes: int):
        if self.cwnd < self.threshold:
            self.slow_start(num_bytes)
        else:
            self.additive_increase(num_bytes)

    def bytes_dropped(self, num_bytes: int, fast: bool = False):
        self.threshold = max(self.max_outstanding // 2, self.mss)
        self.cwnd = self.mss

    @property
    def max_outstanding(self) -> int:
        return self.mss * (self.cwnd // self.mss)

    def slow_start(self, num_bytes: int):
        self.cwnd += min(num_bytes, self.mss)

    def additive_increase(self, num_bytes: int):
        self.cwnd += num_bytes * (self.mss // self.cwnd)

