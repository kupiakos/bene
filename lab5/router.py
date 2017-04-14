import math
from collections import defaultdict
from typing import Mapping, AbstractSet, Optional

from src.link import Link
from src.node import Node
from src.packet import Packet
from src.sim import Sim


class DvrPacket(Packet):
    def __init__(self,
                 src_hostname: str,
                 distance_vector: Mapping[int, float],
                 host_links: Mapping[str, AbstractSet[int]],
                 *args, **kwargs):
        if 'protocol' not in kwargs:
            kwargs['protocol'] = 'dvr'
        super().__init__(*args, **kwargs)
        self.src_hostname = src_hostname
        self.distance_vector = distance_vector
        self.host_links = host_links


class Router:
    def __init__(self, node: Node):
        self.node = node
        # Map dest links to the currently known cost
        self.distance_vector = defaultdict(lambda: math.inf)
        # A node knows the distance to its own link is 0
        for recv_link in self.node.recv_links:
            self.distance_vector[recv_link.address] = 0
        # Map dest host names to the set of known receiving links
        self.host_links = defaultdict(set)
        self.host_links[self.hostname] = {l.address for l in self.node.recv_links}
        # dvr = distance vector routing
        self.node.add_protocol('dvr', self)

    def _link_cost(self, link: Link):
        assert link.startpoint is self.node
        return 1

    @property
    def hostname(self) -> str:
        return self.node.hostname

    def trace(self, message: str):
        Sim.trace('router', message='%s: %s' % (self.hostname, message))

    def send_packet(self, hostname: str):
        pass

    def best_address(self, hostname: str) -> Optional[int]:
        """Find the best known destination address for a given hostname, or None"""
        addresses = self.host_links[hostname]
        if not addresses:
            return None
        addr = min(addresses, key=lambda a: self.distance_vector[a])
        if math.isinf(self.distance_vector[addr]):
            return None
        return addr

    def receive_packet(self, packet: DvrPacket):
        # Our neighbor will only send vector data where it is the source
        src_hostname = packet.src_hostname
        forward_link = self.node.get_link(src_hostname)
        if forward_link is None:
            self.trace('Could not find link for %s' % src_hostname)
            return
        assert forward_link.endpoint.hostname == src_hostname
        self.trace('Received dvr packet from %s - reply with %s' % (src_hostname, repr(forward_link)))

        # The neighbor we received this from has a known receiving link
        self.host_links[src_hostname].add(forward_link.address)
        # We also update our host links with each of the host links our neighbor knows
        for dest_hostname, links in packet.host_links.items():
            self.host_links[dest_hostname] |= links

        # Check each vector entry from our neighbor
        for dest_link, new_cost in packet.distance_vector.items():
            new_cost += self._link_cost(forward_link)
            cur_cost = self.distance_vector[dest_link]
            if new_cost < cur_cost:
                self.trace('Update distance vector for %d from cost %f to %f using %s to forward' % (
                    dest_link, cur_cost, new_cost, repr(forward_link)
                ))
                # Update our distance vector for this new cost
                self.distance_vector[dest_link] = new_cost
                self.node.add_forwarding_entry(dest_link, forward_link)

    def notify_neighbors(self):
        """Notify our neighbors about our distance vector"""
        self.trace('Notifying neighbors of current info')
        # Create a broadcast DvrPacket
        p = DvrPacket(self.hostname, self.distance_vector, self.host_links,
                      ttl=1, destination_address=0)
        self.node.send_packet(p)
