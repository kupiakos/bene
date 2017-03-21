#!/usr/bin/env python3
import csv
import sys
from collections import namedtuple
from typing import io, Optional, MutableSet

sys.path.append('..')

from src.tcppacket import TCPPacket
from src.sim import Sim
from lab3.congestion import TCPTahoe, TCPReno
from lab3.nethelper import NetHelper
from lab3.tcp import TCP
from lab3.sniffer import PacketSniffer

import argparse
import io

MSS = 1000


class TransferTester:
    def __init__(self, file):
        self.send_file = open(file, 'rb')
        self.check_file = open(file, 'rb')
        self.check_file.seek(0, io.SEEK_END)
        self.length = self.check_file.tell()
        self.check_file.seek(0)
        self.errors = False

    def receive_data(self, data):
        Sim.trace('TransferTester', 'Received %d bytes' % (len(data)))
        seq = self.check_file.tell()
        if self.check_file.read(len(data)) != data:
            Sim.trace('TransferTester', 'Chunk %d-%d  is not correct!' % (seq, seq + len(data) - 1))
            self.errors = True

    def check(self):
        if not self.length == self.check_file.tell() == self.send_file.tell():
            print('=== The file was not fully written ===')
            self.errors = True
        if self.errors:
            print('=== There were errors in processing ===')
        else:
            print('=== File transferred successfully ===')
        self.send_file.close()
        self.check_file.close()

    def test(self, handler, chunk_size=1000):
        while True:
            data = self.send_file.read(chunk_size)
            if not data:
                break
            Sim.scheduler.add(delay=0, event=data, handler=handler)


class CongestionWindowPlotter(PacketSniffer):
    SequenceEntry = namedtuple('SequenceEntry', ('time', 'sequence', 'event'))
    CongestionEntry = namedtuple('CongestionEntry', ('time', 'cwnd', 'threshold'))

    def __init__(self, tcp: TCP, drops: MutableSet[int]):
        super().__init__(tcp.node, 'TCP', False)
        self.tcp = tcp
        self.drops = drops
        self.packets = []
        self.congestion = []

    @staticmethod
    def trace_congestion(message):
        Sim.trace('CongestionWindowPlotter', message=message)

    def add_entry(self, sequence: int, event: str):
        self.packets.append(self.SequenceEntry(Sim.scheduler.current_time(), sequence, event))
        self.congestion.append(self.CongestionEntry(
            Sim.scheduler.current_time(),
            self.tcp.congestion.max_outstanding,
            getattr(self.tcp.congestion, 'threshold', None)))

    def intercept_sent(self, packet: TCPPacket) -> Optional[TCPPacket]:
        if packet.sequence in self.drops:
            self.trace_congestion('Dropping packet %d' % packet.sequence)
            self.drops.remove(packet.sequence)
            self.add_entry(packet.sequence, 'drop')
            return None
        self.add_entry(packet.sequence, 'send')
        return super().intercept_sent(packet)

    def intercept_transmit(self, packet: TCPPacket) -> Optional[TCPPacket]:
        if packet.body:
            self.add_entry(packet.sequence, 'transmit')
        return super().intercept_transmit(packet)

    def intercept_received(self, packet: TCPPacket) -> Optional[TCPPacket]:
        self.add_entry(packet.ack_number - MSS, 'ack')
        return super().intercept_received(packet)

    def save_sequence(self, dest_file: str):
        print('=== Writing sequence capture to', dest_file, '===')
        with open(dest_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Time', 'Sequence Number', 'Event'])
            writer.writerows(self.packets)

    def save_cwnd(self, dest_file: str):
        print('=== Writing congestion capture to', dest_file, '===')
        with open(dest_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Time', 'Congestion Window', 'Threshold'])
            writer.writerows(self.congestion)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', type=str, nargs='?', default='internet-architecture.pdf', help='file to test with')
    parser.add_argument('sequence_file', type=str, nargs='?', help='the sequence CSV file')
    parser.add_argument('cwnd_file', type=str, nargs='?', help='the congestion window CSV file')

    parser.add_argument(
        '-d',
        type=lambda s: set(map(int, s.split(','))), default=set(), dest='drops',
        help='Drop the specified comma-separated sequence numbers'
    )

    parser.add_argument('-r', '--reno', action='store_true', help='Use TCP Reno')

    args = parser.parse_args()

    # parameters
    Sim.scheduler.reset()
    Sim.set_debug('TransferTester')
    Sim.set_debug('TCP')
    Sim.set_debug('Congestion')
    Sim.set_debug('CongestionWindowPlotter')
    # Sim.set_debug('Link')

    # setup network
    net = NetHelper('two_nodes.txt')

    # setup routes
    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    net.forward_links((n1, n2))

    # setup application
    tester = TransferTester(args.infile)

    congestion = TCPReno if args.reno else TCPTahoe
    c1, c2 = TCP.connect(net, n1, n2, app=tester, congestion_control=congestion, mss=MSS)
    capture = CongestionWindowPlotter(tcp=c1, drops=args.drops)

    tester.test(c1.send)

    # run the simulation
    Sim.scheduler.run()
    tester.check()
    if args.sequence_file:
        capture.save_sequence(args.sequence_file)
    if args.cwnd_file:
        capture.save_cwnd(args.cwnd_file)


if __name__ == '__main__':
    main()
