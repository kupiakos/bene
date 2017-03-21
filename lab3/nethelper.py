from collections import deque
from typing import Tuple, Optional, List, Union

from networks.network import Network
from src.link import Link
from src.node import Node
from src.packet import Packet
from src.sim import Sim


class NetHelper(Network):
    default_protocol = None
    default_length = None
    ident = 0

    def __enter__(self):
        Sim.scheduler.__enter__()
        self.ident = 0

    def __exit__(self, exc_type, exc_val, exc_tb):
        return Sim.scheduler.__exit__(exc_type, exc_val, exc_tb)

    def add_protocol(self, protocol: str, handler):
        for node in self.nodes.values():
            node.add_protocol(protocol=protocol, handler=handler)

    @staticmethod
    def find_route(src: Node, dest: Node) -> Optional[List[Link]]:
        # breadth-first search
        assert src is not dest
        for src_link in src.links:
            seen = set()
            q = deque([src_link])
            parent = {src_link.address: None}
            while q:
                c = q.pop()  # type: Link
                if c.endpoint is dest:
                    route = []
                    while c is not None:
                        route.append(c)
                        c = parent[c.address]
                    route.reverse()
                    return route
                for link in c.endpoint.links:
                    if link.address in seen: continue
                    if c.endpoint is not src:
                        parent[link.address] = c
                    seen.add(link.address)
                    q.appendleft(link)
        return None

    # @staticmethod
    # def find_route(src: Node, dest: Node) -> Optional[List[Link]]:
    #     # breadth-first search
    #     assert src is not dest
    #     for dest_link in dest.links:
    #         seen = set()
    #         q = deque([dest_link])
    #         parents = {dest_link.address: None}
    #         while q:
    #             c = q.pop()  # type: Link
    #             if c.startpoint is src:
    #                 route = []
    #                 while c is not None:
    #                     route.append(c)
    #                     c = parents[c.address]
    #                 route.reverse()
    #                 return route
    #             for link in c.startpoint.links:
    #                 if link.address in seen: continue
    #                 parents[link.address] = c
    #                 seen.add(link.address)
    #                 q.appendleft(link)
    #     return None

    @staticmethod
    def forward_links(*links: Tuple[Tuple[Node, Node]]):
        for n1, n2 in links:
            link1 = n1.get_link(n2.hostname)
            if link1 is not None:
                n1.add_forwarding_entry(address=n1.get_address(n2.hostname), link=link1)

            link2 = n2.get_link(n1.hostname)
            if link2 is not None:
                n2.add_forwarding_entry(address=n2.get_address(n1.hostname), link=link2)

    @staticmethod
    def forward_route(route: List[Link], full: bool = True):
        for i, src_link in enumerate(route):
            node = src_link.startpoint
            for dest_link in (route[i:] if full else (route[-1],)):
                node.add_forwarding_entry(address=dest_link.address, link=src_link)

    def forward_all_links(self):
        # TODO
        raise NotImplementedError()
        # links = {link.address: link for n in self.nodes.values() for link in n.links}
        # possible weighting for better links could be done if multiple links exist!
        # for node in self.nodes.values():
        #     # dijkstra's
        #     q = [[math.inf, c, n, None] for c, n in enumerate(self.nodes)]
        #     q[next(n for n, i in enumerate(q) if i[2] is node)][0] = 0.
        #     dist = {node.hostname: 0}
        #     targets = {}
        #     seen = set()
        #     while q:
        #         cost, _, n1, closest_link = heapq.heappop(q)
        #         for link in n1.links:
        #             assert link.startpoint is n1
        #             n2 = link.endpoint
        #             new_cost = cost + 1
        #             if n2.hostname not in dist or new_cost < dist[n2.hostname]:
        #                 entry = q[next(n for n, i in enumerate(q) if i[2] is n2)]
        #                 entry[0] = new_cost
        #                 dist[n2.hostname] = new_cost
        #                 heapq.heapify(q)
        #                 if closest_link is None:
        #                     assert n1 is node
        #                     closest_link = link
        #                 entry[3] = closest_link
        #                 targets[n2.hostname] = closest_link
        #     for target, closest_link in targets.items():
        #         node.add_forwarding_entry()
        #
        # for name, n1 in self.nodes.items():
        #     for link in n1.links:
        #         n2 = link.endpoint
        #         n1.add_forwarding_entry(address=n2.get_address(n1.hostname), link=link)

    @staticmethod
    def reset_link(link: Link, propagation: float = None, bandwidth: float = None):
        if propagation is not None:
            link.propagation = propagation
        if bandwidth is not None:
            link.bandwidth = bandwidth

    def reset_all_links(self, propagation: float = None, bandwidth: float = None):
        for name, node in self.nodes.items():
            for link in node.links:
                self.reset_link(link, propagation, bandwidth)

    def resolve_dest_address(self, src: Node, dest: Union[Node, Link, int]) -> Optional[int]:
        if isinstance(dest, int):
            return dest
        if isinstance(dest, Link):
            return dest.address
        route = self.find_route(src, dest)
        return route and route[-1].address

    def send_packet(self, delay: int,
                    src: Node, dest: Union[Node, Link, int],
                    ident: int = None, protocol: str = None, length: int = None,
                    **kwargs) -> Packet:
        if ident is None:
            ident = self.ident
            self.ident += 1
        if protocol is None:
            if self.default_protocol is None:
                raise Exception('No default protocol set')
            protocol = self.default_protocol
        if length is None:
            if self.default_length is None:
                raise Exception('No default length set')
            length = self.default_length
        dest_addr = self.resolve_dest_address(src, dest)
        if dest_addr is None:
            raise Exception('Could not find a route to node!')
        p = Packet(destination_address=dest_addr,
                   ident=ident, protocol=protocol, length=length, **kwargs)
        Sim.scheduler.add(delay=delay, event=p, handler=src.send_packet)
        return p

    def send_packet_stream(self, src: Node, dest: Union[Node, Link, int], count: int,
                           delay: int = 0, length: int = None, **kwargs):
        dest_addr = self.resolve_dest_address(src, dest)
        if dest_addr is None:
            raise Exception('Could not find a route to node!')
        first_link = src.forwarding_table.get(dest_addr)
        if first_link is None:
            raise Exception('No forwarded route available from %s to %d' % (src.hostname, dest_addr))
        if length is None:
            if self.default_length is None:
                raise Exception('No default length set')
            length = self.default_length

        packet_delay = (8 * length) / first_link.bandwidth
        for _ in range(count):
            self.send_packet(delay, src, dest, length=length, **kwargs)
            delay += packet_delay
