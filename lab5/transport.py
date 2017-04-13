from functools import partial

from .ranges import range_merge, range_subtract, range_overlap, range_format
from src.sim import Sim
from src.tcppacket import TCPPacket


class Transport(object):
    def __init__(self, node):
        self.node = node
        self.binding = {}
        self.drops = {}
        self.node.add_protocol(protocol="TCP", handler=self)

    def bind(self, connection, source_address, source_port,
             destination_address, destination_port):
        # setup binding so that packets we receive for this combination
        # are sent to the right socket
        address_data = (destination_address, destination_port,
                        source_address, source_port)
        self.binding[address_data] = connection

    def receive_packet(self, packet):
        address_data = (packet.source_address, packet.source_port,
                        packet.destination_address, packet.destination_port)
        self.binding[address_data].receive_packet(packet)

    def trace(self, message):
        Sim.trace('TCP', message=message)

    def send_packet(self, packet):
        assert len(packet.body) == packet.length
        packet_range = range(packet.sequence, packet.sequence + packet.length)
        skips = list(filter(None, map(partial(range_overlap, packet_range), self.drops)))
        if skips:
            self.send_split_packet(packet, skips)
        else:
            Sim.scheduler.add(delay=0, event=packet, handler=self.node.send_packet)

    def send_split_packet(self, packet, skips):
        assert isinstance(packet, TCPPacket)
        # Could possibly be made more efficient?
        to_skip = range_merge(skips)
        packet_range = range(packet.sequence, packet.sequence + packet.length)
        to_send = range_subtract(packet_range, *to_skip)
        self.trace('%s skipping ranges %s as scheduled' % (
            self.node.hostname, range_format(*to_skip)
        ))
        for skip in self.drops.copy():
            overlap = range_overlap(skip, packet_range)
            if not overlap:
                continue
            n = self.drops[skip]
            untouched = range_subtract(skip, packet_range)
            del self.drops[skip]

            self.trace('%s skip %s has %d left' % (
                self.node.hostname, range_format(overlap), n - 1
            ))
            if untouched:
                self.trace('%s untouched range %s gets another %d left' % (
                    self.node.hostname, range_format(*untouched), n
                ))
            for r in untouched:
                self.drops[r] = self.drops.get(r, 0) + n
            if n > 2:
                self.drops[skip] = n - 1
        for send_range in to_send:
            data = packet.body[send_range.start - packet.sequence:send_range.stop - packet.sequence]
            assert len(data) == len(send_range)
            split = TCPPacket(
                source_address=packet.source_address,
                source_port=packet.source_port,
                destination_address=packet.destination_address,
                destination_port=packet.destination_port,
                body=data,
                sequence=send_range.start, ack_number=packet.ack_number)
            self.trace('%s sending split range %d-%d' % (
                self.node.hostname, send_range.start, send_range.stop - 1
            ))
            Sim.scheduler.add(delay=0, event=split, handler=self.node.send_packet)

    def drop_data(self, seq_start, seq_end, times=1):
        seq_range = range(seq_start, seq_end)
        n = self.drops.get(seq_range, 0) + times
        self.drops[seq_range] = n
        self.trace('%s will drop the range %s %d times' % (
            self.node.hostname, range_format(seq_range), n
        ))
