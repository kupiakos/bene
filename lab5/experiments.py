#!/usr/bin/env python3

import sys
from typing import Callable

sys.path.append('..')

import itertools

from src.sim import Sim
from networks.nethelper import NetHelper
from src.packet import Packet
from src.sniffer import PacketSniffer
from lab5.router import Router, DvrPacket


class ReportSniffer(PacketSniffer):

    def receive_packet(self, packet: Packet):
        super().receive_packet(packet)
        if packet.protocol == 'dvr':
            assert isinstance(packet, DvrPacket)
            Sim.trace('sniff', 'dvr %s -> %s (%s)' % (packet.src_hostname, self.node.hostname, dict(packet.distance_vector)))

    def forward_packet(self, packet: Packet):
        super().forward_packet(packet)
        if packet.protocol == 'trace':
            Sim.trace('sniff', 'hop %s' % packet.link)


def send_test_packet(router, src, dest, packet, delay):
    def send(_):
        Sim.trace('sniff', '\r%s\n== Sending packet %s -> %s ==' % (' ' * 40, src, dest))
        router.send_packet(dest, packet)
    Sim.scheduler.add(delay, None, send)


def test_packets(routers):
    rkeys = routers.keys()
    ident = 1
    for src in sorted(rkeys):
        for dest in sorted(rkeys - {src}):
            send_test_packet(routers[src], src, dest,
                             Packet(ident=ident, protocol='trace'), ident)
            ident += 1


def report_links(net: NetHelper):
    links = {
        l.address: l for node in net.nodes.values()
        for l in itertools.chain(node.links, node.recv_links)
    }
    print('All links:')
    for addr in sorted(links):
        print(links[addr])


def test_ring():
    Sim.scheduler.reset()
    Sim.set_debug('sniff')
    # Sim.set_debug('router')
    net = NetHelper('../networks/five-ring.txt')
    report_links(net)
    routers = {name: Router(node) for name, node in net.nodes.items()}
    for node in net.nodes.values():
        ReportSniffer(node, None)
    # Wait for the DVR packets to propagate before testing packets
    Sim.scheduler.add(5, routers, test_packets)
    Sim.scheduler.add(25, None, net.get_node('n1').get_link('n5').down)
    Sim.scheduler.add(25, None, net.get_node('n5').get_link('n1').down)
    # Should be detected broken by now
    Sim.scheduler.add(95, routers, test_packets)

    Sim.scheduler.run_until(119)


def test_row():
    Sim.scheduler.reset()
    Sim.set_debug('sniff')
    # Sim.set_debug('router')
    net = NetHelper('../networks/five-row.txt')
    report_links(net)
    routers = {name: Router(node) for name, node in net.nodes.items()}
    for node in net.nodes.values():
        ReportSniffer(node, None)
    # Wait for the DVR packets to propagate before testing packets
    Sim.scheduler.add(5, routers, test_packets)
    Sim.scheduler.run_until(29)


def test_big():
    Sim.scheduler.reset()
    Sim.set_debug('sniff')
    # Sim.set_debug('router')
    net = NetHelper('../networks/fifteen-nodes.txt')
    report_links(net)
    routers = {name: Router(node) for name, node in net.nodes.items()}
    for node in net.nodes.values():
        ReportSniffer(node, None)
    # Wait for the DVR packets to propagate before testing packets
    Sim.scheduler.add(5, routers, test_packets)
    Sim.scheduler.run_until(29)


def main():
    # test_row()
    # test_ring()
    test_big()


if __name__ == '__main__':
    main()
