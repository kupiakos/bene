from functools import wraps
from typing import Optional

from src.node import Node
from src.packet import Packet
from src.sim import Sim


class PacketSniffer:
    def __init__(self, node: Node, protocol: str, keep=True):
        self.packets = []
        self.keep = keep
        self.forward = node.protocols.get(protocol)
        original_add = node.add_protocol
        node.add_protocol(protocol, self)

        @wraps(node.add_protocol)
        def add_protocol_wrapped(this_protocol, handler):
            if this_protocol == protocol:
                self.forward = handler
            original_add(this_protocol, handler)

        node.add_protocol = add_protocol_wrapped

    @staticmethod
    def trace(message):
        Sim.trace('PacketSniffer', message)

    def intercept_packet(self, packet: Packet) -> Optional[Packet]:
        return packet

    def receive_packet(self, packet: Packet):
        if self.keep:
            self.packets.append(packet)
        self.trace('Captured packet %d, length %d' % (packet.ident, packet.length))
        packet = self.intercept_packet(packet)
        if self.forward is not None and packet is not None:
            self.forward.receive_packet(packet)
