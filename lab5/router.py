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


class RoutingError(ValueError):
    pass


class Router:
    def __init__(self, node: Node, send_rate=30, link_timeout=90):
        self.node = node
        self.send_rate = send_rate
        self.link_timeout = link_timeout
        # Map dest links to the currently known cost
        self.distance_vector = defaultdict(lambda: math.inf)
        # A node knows the distance to its own link is 0
        for recv_link in self.node.recv_links:
            self.distance_vector[recv_link.address] = 0
        # Map dest host names to the set of known receiving links
        self.host_links = defaultdict(set)
        self.host_links[self.hostname] = {l.address for l in self.node.recv_links}
        self._transmit_timer = None
        self._neighbor_timers = {}
        # dvr = distance vector routing
        self.node.add_protocol('dvr', self)
        self.notify_neighbors()

    def _link_cost(self, link: Link):
        assert link.startpoint is self.node
        return 1

    @property
    def hostname(self) -> str:
        return self.node.hostname

    def trace(self, message: str):
        Sim.trace('router', message='%s: %s' % (self.hostname, message))

    def send_packet(self, hostname: str, packet: Packet):
        """Send a data packet along on the best known route (and link) to a host"""
        dest_addr = self.best_address(hostname)
        if dest_addr is None:
            raise RoutingError('Cannot find a route to %s' % hostname)
        packet.destination_address = dest_addr
        self.trace('Sending to host %s (address %d)' % (hostname, dest_addr))
        self.node.send_packet(packet=packet)

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
        new_data = False
        src_hostname = packet.src_hostname
        forward_link = self.node.get_link(src_hostname)
        if forward_link is None:
            self.trace('Could not find link for %s' % src_hostname)
            return
        assert forward_link.endpoint.hostname == src_hostname
        self.trace('Received dvr packet from %s - reply with %s' % (src_hostname, repr(forward_link)))
        self._reset_neighbor(forward_link.address)

        if forward_link.address not in self.host_links[src_hostname]:
            new_data = True
        # The neighbor we received this from has a known receiving link
        self.host_links[src_hostname].add(forward_link.address)
        # We also update our host links with each of the host links our neighbor knows
        for dest_hostname, links in packet.host_links.items():
            known = self.host_links[dest_hostname]
            l = len(known)
            known |= links
            if l < len(known):
                new_data = True

        # Check each vector entry from our neighbor
        for dest_link, new_cost in packet.distance_vector.items():
            new_cost += self._link_cost(forward_link)
            cur_cost = self.distance_vector[dest_link]
            if new_cost < cur_cost:
                self.trace('Update distance vector for %d from cost %f to %f using %s to forward' % (
                    dest_link, cur_cost, new_cost, repr(forward_link)
                ))
                new_data = True
                # Update our distance vector for this new cost
                self.distance_vector[dest_link] = new_cost
                self.node.add_forwarding_entry(dest_link, forward_link)

        if new_data:
            self.trace('New data detected in transmission, notify immediately')
            self.trace('Full distance vector: %s' % dict(self.distance_vector))
            self.trace('Forwarding table: %s' % dict(self.node.forwarding_table))
            self.trace('Host links: %s' % dict(self.host_links))
            self.notify_neighbors()

    def notify_neighbors(self, timeout=False, force=None):
        """Notify our neighbors about our distance vector"""
        if self._transmit_timer is not None and not timeout:
            Sim.scheduler.cancel(self._transmit_timer)
        self._transmit_timer = Sim.scheduler.add(
            delay=self.send_rate, event=True, handler=self.notify_neighbors)

        self.trace('Notifying neighbors of current info')
        # Create a broadcast DvrPacket
        p = DvrPacket(self.hostname, self.distance_vector, self.host_links,
                      ttl=1, destination_address=0)
        self.node.send_packet(p)

    def _reset_neighbor(self, forward_link: int):
        if forward_link in self._neighbor_timers:
            Sim.scheduler.cancel(self._neighbor_timers[forward_link])
        self._neighbor_timers[forward_link] = Sim.scheduler.add(
            delay=self.link_timeout, event=forward_link, handler=self._neighbor_timeout)

    def _neighbor_timeout(self, forward_link: int):
        self.trace('Timeout for link %s' % (
            next(l for l in self.node.links if l.address == forward_link)
        ))
        del self._neighbor_timers[forward_link]
        assert forward_link in self.distance_vector
        del self.distance_vector[forward_link]
        self.notify_neighbors()
