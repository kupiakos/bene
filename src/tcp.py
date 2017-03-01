from .buffer import SendBuffer, ReceiveBuffer
from .connection import Connection
from .sim import Sim
from .tcppacket import TCPPacket


class TCP(Connection):
    """ A TCP connection between two hosts."""

    def __init__(self, transport, source_address, source_port,
                 destination_address, destination_port, app=None, window=1000):
        Connection.__init__(self, transport, source_address, source_port,
                            destination_address, destination_port, app)

        # -- Sender functionality

        # send window; represents the total number of bytes that may
        # be outstanding at one time
        self.window = window
        # send buffer
        self.send_buffer = SendBuffer()
        # maximum segment size, in bytes
        self.mss = 1000
        # largest sequence number that has been ACKed so far; represents
        # the next sequence number the client expects to receive
        self.sequence = 0
        # retransmission timer
        self.timer = None
        # timeout duration in seconds
        self.timeout = 1

        # -- Receiver functionality

        # receive buffer
        self.receive_buffer = ReceiveBuffer()
        # ack number to send; represents the largest in-order sequence
        # number not yet received
        self.ack = 0

    def trace(self, message):
        """ Print debugging messages. """
        Sim.trace("TCP", message)

    def receive_packet(self, packet):
        """ Receive a packet from the network layer. """
        if packet.ack_number > 0:
            # handle ACK
            self.handle_ack(packet)
        if packet.length > 0:
            # handle data
            self.handle_data(packet)

    ''' Sender '''

    def send(self, data):
        """ Send data on the connection. Called by the application. This
            code currently sends all data immediately. """
        self.send_buffer.put(data)
        self.trace('Put %d bytes into buffer' % len(data))
        self.send_all_allowed()
        # Sim.scheduler.add(delay=0, event='transmit', handler=self.handle_send)

    def send_all_allowed(self):
        """Send all data that the current state (window) allows us to"""
        while True:
            data_len = min(self.send_buffer.available, self.window - self.send_buffer.outstanding, self.mss)
            if data_len <= 0:
                return
            data, seq = self.send_buffer.get(data_len)
            assert len(data) == data_len
            self.send_packet(data, seq)

    def send_packet(self, data, sequence):
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           body=data,
                           sequence=sequence, ack_number=self.ack)

        # send the packet
        self.trace("%s (%d) sending TCP segment %d-%d to %d" % (
            self.node.hostname, self.source_address,
            packet.sequence, sequence + len(data) - 1,
            self.destination_address))
        self.transport.send_packet(packet)
        if not self.timer:
            self.reset_timer()

    def handle_ack(self, packet):
        """ Handle an incoming ACK. """
        self.trace('%s (%d) received ACK from %d for %d' % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.ack_number
        ))
        self.send_buffer.slide(packet.ack_number)
        self.cancel_timer()
        if self.send_buffer.outstanding == 0:
            self.reset_timer()
        self.sequence = packet.ack_number
        self.send_all_allowed()


    def retransmit(self, event):
        """ Retransmit data. """
        self.trace("%s (%d) retransmission timer fired" % (self.node.hostname, self.source_address))

    def reset_timer(self):
        if self.timer:
            self.cancel_timer()
        self.timer = Sim.scheduler.add(delay=self.timeout, event='retransmit', handler=self.retransmit)

    def cancel_timer(self):
        """ Cancel the timer. """
        if not self.timer:
            return
        Sim.scheduler.cancel(self.timer)
        self.timer = None

    ''' Receiver '''

    def handle_data(self, packet):
        """ Handle incoming data. This code currently gives all data to
            the application, regardless of whether it is in order, and sends
            an ACK."""
        self.trace("%s (%d) received TCP segment %d-%d from %d" % (
            self.node.hostname, packet.destination_address,
            packet.sequence, packet.sequence + len(packet.body) - 1,
            packet.source_address))
        self.receive_buffer.put(packet.body, packet.sequence)
        data, seq = self.receive_buffer.get()
        if data:
            self.trace('%s buffer has %d-%d' % (self.node.hostname, seq, seq + len(data) - 1))
            self.ack = seq + len(data)
            self.app.receive_data(data)
        self.send_ack()

    def send_ack(self):
        """ Send an ack. """
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           sequence=self.sequence, ack_number=self.ack)
        # send the packet
        self.trace("%s (%d) sending TCP ACK to %d for %d" % (
            self.node.hostname, self.source_address, self.destination_address, packet.ack_number))
        self.transport.send_packet(packet)
