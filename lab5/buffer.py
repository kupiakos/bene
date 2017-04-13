from lab5.ranges import range_merge


class SendBuffer(object):
    """ Send buffer for transport protocols """

    def __init__(self):
        """ The buffer holds a series of characters to send. The base
            is the starting sequence number of the buffer. The next
            value is the sequence number for the next data that has
            not yet been sent. The last value is the sequence number
            for the last data in the buffer."""
        self.buffer = bytearray()
        self.base_seq = 0
        self.next_seq = 0
        self.last_seq = 0

    @property
    def available(self):
        """ Return number of bytes available to send. This is data that
            could be sent but hasn't."""
        assert self.last_seq >= self.next_seq
        return self.last_seq - self.next_seq

    @property
    def outstanding(self):
        """ Return number of outstanding bytes. This is data that has
            been sent but not yet acked."""
        assert self.next_seq >= self.base_seq
        return self.next_seq - self.base_seq

    def put(self, data):
        """ Put some data into the buffer """
        self.buffer += data
        self.last_seq += len(data)

    def get(self, size):
        """ Get the next data that has not been sent yet. Return the
            data and the starting sequence number of this data. The
            total amount of data returned is at most size bytes but may
            be less."""
        if self.next_seq + size > self.last_seq:
            size = self.last_seq - self.next_seq
        start = self.next_seq - self.base_seq
        data = self.buffer[start:start + size]
        sequence = self.next_seq
        self.next_seq = self.next_seq + size
        return bytes(data), sequence

    def skip(self, size):
        """Ensure that the next result from get will skip at least the
        first size bytes in the buffer."""
        if self.next_seq < self.base_seq + size:
            self.next_seq = self.base_seq + size

    def resend(self, size, reset=True):
        """ Get oldest data that is outstanding, so it can be
        resent. Return the data and the starting sequence number of
        this data. The total amount of data returned is at most size
        bytes but may be less. If reset is true, then all other data
        that was outstanding is now treated as if it was never sent. This
        is standard practice for TCP when retransmitting."""
        if self.base_seq + size > self.last_seq:
            size = self.last_seq - self.base_seq
        data = self.buffer[:size]
        sequence = self.base_seq
        if reset:
            self.next_seq = sequence + size
        return bytes(data), sequence

    def slide(self, sequence):
        """ Slide the receive window to the acked sequence
            number. This sequence number represents the lowest
            sequence number that is not yet acked. In other words, the
            ACK is for all data less than but not equal to this
            sequence number. Return the number of ACKed bytes."""
        acked = sequence - self.base_seq
        self.buffer = self.buffer[acked:]
        self.base_seq = sequence
        # adjust next in case we slide past it
        if self.next_seq < self.base_seq:
            self.next_seq = self.base_seq
        return acked


class Chunk(object):
    """ Chunk of data stored in receive buffer. """

    def __init__(self, data, sequence):
        self.data = data
        self.length = len(data)
        self.sequence = sequence

    @property
    def range(self):
        return range(self.sequence, self.sequence + self.length)

    def trim(self, sequence, length):
        """ Check for overlap with a previous chunk and trim this chunk
            if needed."""
        # check for overlap
        if self.sequence < sequence + length:
            self.data = self.data[sequence + length:]
            self.length = len(self.data)
            self.sequence = sequence + length


class ReceiveBuffer(object):
    """ Receive buffer for transport protocols """

    def __init__(self):
        """ The buffer holds all the data that has been received,
            indexed by starting sequence number. Data may come in out
            of order, so this buffer will order them. Data may also be
            duplicated, so this buffer will remove any duplicate
            bytes."""
        self.buffer = {}
        # starting sequence number
        self.base_seq = 0

    def put(self, data, sequence):
        """ Add data to the receive buffer. Put it in order of
        sequence number and remove any duplicate data."""
        # ignore old chunk
        if sequence < self.base_seq:
            return
        # ignore duplicate chunk
        if sequence in self.buffer:
            if self.buffer[sequence].length >= len(data):
                return
        self.buffer[sequence] = Chunk(data, sequence)
        # remove overlapping data
        next_data = -1
        length = 0

        for sequence in sorted(self.buffer.keys()):
            chunk = self.buffer[sequence]
            # trim chunk if there is duplicate data from the previous chunk
            chunk.trim(next_data, length)
            if chunk.length == 0:
                # remove chunk
                del self.buffer[sequence]
            next_data = chunk.sequence
            length = len(chunk.data)

    def get(self):
        """ Get and remove all data that is in order. Return the data
            and its starting sequence number. """
        data = bytearray()
        start = self.base_seq
        for sequence in sorted(self.buffer.keys()):
            chunk = self.buffer[sequence]
            if chunk.sequence == self.base_seq:
                # append the data, adjust the base, delete the chunk
                data += chunk.data
                self.base_seq += chunk.length
                del self.buffer[chunk.sequence]
        return bytes(data), start

    def get_ranges(self):
        return range_merge(chunk.range for chunk in self.buffer.values())
