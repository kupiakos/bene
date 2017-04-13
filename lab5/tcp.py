from lab5 import congestion
from lab5.buffer import SendBuffer, ReceiveBuffer
from lab5.nethelper import NetHelper
from lab5.ranges import range_format, range_subtract
from lab5.transport import Transport
from src.connection import Connection
from src.node import Node
from src.sim import Sim
from src.tcppacket import TCPPacket


class TCP(Connection):
    """ A TCP connection between two hosts."""

    def __init__(self, transport, source_address, source_port,
                 destination_address, destination_port, app=None, window=1000000, mss=1000,
                 fast_retransmit=3, congestion_control=None):
        Connection.__init__(self, transport, source_address, source_port,
                            destination_address, destination_port, app)

        # -- Sender functionality

        # send window; represents the total number of bytes that may
        # be outstanding at one time
        self.window = window
        # send buffer
        self.send_buffer = SendBuffer()
        # maximum segment size, in bytes
        self.mss = mss
        # largest sequence number that has been ACKed so far; represents
        # the next sequence number the client expects to receive
        self.sequence = 0
        # retransmission timer
        self.timer = None
        # timeout duration in seconds
        self.timeout = 2

        # The number of duplicate ACKs to receive before we perform a fast retransmit (0 for no fast retransmit)
        self.fast_retransmit = fast_retransmit
        # The number of duplicate ACKs we have received in a row
        self.duplicate_acks = 0

        # -- Receiver functionality

        # receive buffer
        self.receive_buffer = ReceiveBuffer()
        # ack number to send; represents the largest in-order sequence
        # number not yet received
        self.ack = 0

        if congestion_control is None:
            congestion_control = congestion.NoCongestionControl
        self.congestion = congestion_control(mss=self.mss)

    @classmethod
    def connect(cls, net: NetHelper, n1: Node, n2: Node, *args, **kwargs):
        # setup transport
        t1 = Transport(n1)
        t2 = Transport(n2)

        # setup connection
        n1_n2 = net.resolve_dest_address(n1, n2)
        n2_n1 = net.resolve_dest_address(n2, n1)

        c1 = cls(t1, n2_n1, 1, n1_n2, 1, *args, **kwargs)
        c2 = cls(t2, n1_n2, 1, n2_n1, 1, *args, **kwargs)
        return c1, c2

    @staticmethod
    def trace(message):
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
        self.send_all_allowed()
        self.trace('%s send buffer sent %d-%d, have through %d' % (
            self.node.hostname, self.send_buffer.base_seq, self.send_buffer.next_seq, self.send_buffer.last_seq
        ))

    def send_one_segment(self, resend=False):
        self.send_buffer.skip(0 if resend else self.congestion.skip_sending)
        data_len = min(self.send_buffer.available,
                       self.congestion.max_outstanding - self.send_buffer.outstanding,
                       self.window - self.send_buffer.outstanding, self.mss)
        if data_len <= 0:
            self.trace('%s cannot send more data' % self.node.hostname)
            return
        data, seq = self.send_buffer.get(data_len)
        assert len(data) == data_len
        return self.send_packet(data, seq)

    def send_all_allowed(self):
        """Send all data that the current state (window, congestion control) allows us to"""
        while self.send_one_segment() is not None: pass

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
        return packet

    def handle_ack(self, packet):
        """ Handle an incoming ACK. """
        self.trace('%s (%d) received ACK from %d for %d' % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.ack_number
        ))
        acked = self.send_buffer.slide(packet.ack_number)
        if acked > 0:
            self.congestion.send_successful(acked)
        if self.send_buffer.outstanding > 0 or self.congestion.skip_sending > 0:
            self.reset_timer()
        else:
            self.trace('%s cancel timer' % self.node.hostname)
            self.cancel_timer()
        if self.fast_retransmit > 0 and packet.ack_number == self.sequence:
            self.duplicate_acks += 1
            excess = self.duplicate_acks - 1 - self.fast_retransmit
            if excess < 0:
                self.trace('%s %d ACKs are duplicate' % (
                    self.node.hostname, self.duplicate_acks
                ))
            if excess >= 0:
                self.congestion.send_failed(self.send_buffer.outstanding, dup_acks=self.duplicate_acks)
            if excess == 0:
                self.retransmit(timer=False)
                return
        else:
            self.duplicate_acks = 0
        self.sequence = packet.ack_number
        self.send_all_allowed()

    def retransmit(self, timer=True):
        """ Retransmit data. """
        if timer:
            self.timer = None
            self.trace("%s (%d) TCP timeout fired, sequence %d" % (
                self.node.hostname, self.source_address, self.sequence))
            self.congestion.send_failed(self.send_buffer.outstanding)
        else:
            self.cancel_timer()
            self.trace('%s fast retransmit, sequence %d' % (
                self.node.hostname, self.sequence
            ))
        self.send_buffer.resend(0, reset=True)
        self.send_one_segment(resend=True)

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
        buf_ranges = self.receive_buffer.get_ranges()
        if buf_ranges:
            self.trace('%s receive buffer now has %s' % (
                self.node.hostname, range_format(*buf_ranges)
            ))
        data, seq = self.receive_buffer.get()
        if data:
            self.ack = seq + len(data)
            self.app.receive_data(data)
        if self.receive_buffer.buffer:
            gap_range = range(
                self.ack,
                self.receive_buffer.buffer[max(self.receive_buffer.buffer)].range.stop)
            self.trace('%s receive buffer is now missing %s' % (
                self.node.hostname, range_format(*range_subtract(gap_range, *self.receive_buffer.get_ranges()))
            ))
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
