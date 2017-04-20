from functools import wraps
from typing import Optional, Callable

from src.node import Node
from src.packet import Packet
from src.sim import Sim


class PacketSniffer:
    def __init__(self, node: Node, protocol: Optional[str], keep=True):
        self.received = []
        self.sent = []
        self.keep = keep
        self.forward_send = node.send_packet
        self.forward_transmit = {}

        if protocol is None:
            self.forward_receive = node.receive_packet
            @wraps(node.receive_packet)
            def receive_packet_wrapped(packet: Packet):
                self.receive_packet(packet)
            node.receive_packet = receive_packet_wrapped
        else:
            self.forward_receive = (
                node.protocols[protocol].receive_packet
                if protocol in node.protocols else None)
            original_add = node.add_protocol
            node.add_protocol(protocol, self)
            @wraps(node.add_protocol)
            def add_protocol_wrapped(this_protocol, handler):
                if this_protocol == protocol or protocol is None:
                    if handler is None:
                        self.forward_receive = None
                    else:
                        self.forward_receive = handler.receive_packet
                original_add(this_protocol, handler)

            node.add_protocol = add_protocol_wrapped

        @wraps(node.send_packet)
        def send_packet_wrapped(packet: Packet):
            if packet.protocol == protocol or protocol is None:
                if packet.destination_address == 0:
                    for link in node.links:
                        self._wrap_link(packet, link)
                else:
                    link = node.forwarding_table[packet.destination_address]
                    self._wrap_link(packet, link)
                self.send_packet(packet)
            else:
                self.forward_send(packet)

        node.send_packet = send_packet_wrapped

        self.forward_forward = node.forward_packet
        @wraps(node.forward_packet)
        def forward_packet_wrapped(packet: Packet):
            if packet.protocol == protocol or protocol is None:
                self.forward_packet(packet)
            else:
                self.forward_forward(packet)
        node.forward_packet = forward_packet_wrapped

        self.node = node


    def _wrap_link(self, packet, link):
        if not hasattr(link, '_wrapping'):
            link._wrapping = set()
        link._wrapping.add(packet)
        if hasattr(link, '_orig_transmit'):
            return
        link._orig_transmit = link.transmit

        @wraps(link.transmit)
        def transmit(this_packet):
            if this_packet in link._wrapping:
                self.transmit_packet(link._orig_transmit, this_packet)
                link._wrapping.remove(this_packet)
            else:
                link._orig_transmit(this_packet)

        link.transmit = transmit

    @staticmethod
    def trace(message):
        Sim.trace('PacketSniffer', message)

    def intercept_sent(self, packet: Packet) -> Optional[Packet]:
        return packet

    def intercept_received(self, packet: Packet) -> Optional[Packet]:
        return packet

    def intercept_transmit(self, packet: Packet) -> Optional[Packet]:
        return packet

    def intercept_forward(self, packet: Packet) -> Optional[Packet]:
        return packet

    def send_packet(self, packet: Packet):
        if self.keep:
            self.sent.append(packet)
        self.trace('Captured sent packet %d, length %d' % (packet.ident, packet.length))
        packet = self.intercept_sent(packet)
        if self.forward_send is not None and packet is not None:
            self.forward_send(packet)

    def receive_packet(self, packet: Packet):
        if self.keep:
            self.received.append(packet)
        self.trace('Captured received packet %d, length %d' % (packet.ident, packet.length))
        packet = self.intercept_received(packet)
        if self.forward_receive is not None and packet is not None:
            self.forward_receive(packet)

    def transmit_packet(self, forward_transmit: Callable[[Packet], None], packet: Packet):
        self.trace('Captured transmit packet %d, length %d' % (packet.ident, packet.length))
        packet = self.intercept_transmit(packet)
        if forward_transmit is not None and packet is not None:
            forward_transmit(packet)

    def forward_packet(self, packet: Packet):
        self.trace('Captured forwarding packet %d, length %d' % (packet.ident, packet.length))
        packet = self.intercept_forward(packet)
        if self.forward_forward is not None and packet is not None:
            self.forward_forward(packet)

