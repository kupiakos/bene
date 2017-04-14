import math
from collections import defaultdict
from typing import Mapping, AbstractSet

from src.link import Link
from src.node import Node
from src.packet import Packet
from src.sim import Sim


class DvrPacket(Packet):
    def __init__(self,
                 src_hostname: str,
                 distance_vector: Mapping[str, float],
                 host_best_dest: Mapping[str, int],
                 link_addresses: Mapping[str, AbstractSet[int]],
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.src_hostname = src_hostname
        self.host_best_dest = host_best_dest
        self.distance_vector = distance_vector
        self.link_addresses = link_addresses


class Router:
    def __init__(self, node: Node):
        self.node = node
        # Map dest host names to the currently known cost
        self.distance_vector = defaultdict(lambda: math.inf)
        # Map dest host names to best known recv link on host reachable from here
        self.host_best_dest = defaultdict(int)
        # Map dest host names to the set of known links
        self.link_addresses = defaultdict(set)
        self.link_addresses[self.node.hostname] = {l.address for l in self.node.recv_links}
        # dvr = distance vector routing
        self.node.add_protocol('dvr', self)

    def _link_cost(self, link: Link):
        return 1

    def trace(self, message: str):
        Sim.trace('router', message=message)

    def send_packet(self, hostname: str):
        pass

    def receive_packet(self, packet: DvrPacket):
        src_hostname = packet.src_hostname
        dest_link = self.node.get_link(src_hostname)
        if dest_link is None:
            self.trace('Could not find link for %s' % src_hostname)
            return
        assert dest_link.startpoint.hostname == src_hostname

        self.link_addresses[src_hostname].add(dest_link.address)
        for dest_hostname, links in packet.link_addresses:
            self.link_addresses[dest_hostname] |= links

        # Check each vector entry
        for dest_hostname, new_cost in packet.distance_vector:
            new_cost += self._link_cost(dest_link)
            cur_cost = self.distance_vector[dest_hostname]
            if new_cost < cur_cost:
                # Update our distance vector for this new cost
                self.distance_vector[dest_hostname] = new_cost
                # Update the forwarding table for the new "best" link
                best_dest = packet.host_best_dest[dest_hostname]
                self.host_best_dest[dest_hostname] = best_dest
                self.node.add_forwarding_entry(best_dest, dest_link)

