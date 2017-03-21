#!/usr/bin/env python3
import sys
from typing import io

sys.path.append('..')

from src.sim import Sim
from lab2.transport import Transport
from lab2.nethelper import NetHelper
from lab2.tcp import TCP
from lab2.sniffer import PacketSniffer

import argparse
import io


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
        if self.errors:
            print(' === There were errors in processing ===')
        else:
            print(' === File transferred successfully ===')
        self.send_file.close()
        self.check_file.close()

    def test(self, handler, chunk_size=1000):
        while True:
            data = self.send_file.read(chunk_size)
            if not data:
                break
            Sim.scheduler.add(delay=0, event=data, handler=handler)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'infile',
        type=str, default='internet-architecture.pdf', nargs='?',
        help='file to test with')

    parser.add_argument(
        '-l', '--loss',
        type=float, default=0.2,
        help='random loss rate')

    parser.add_argument(
        '-w', '--window',
        type=int, default=3000,
        help='the window size')

    parser.add_argument(
        '-f', '--fast-retransmit',
        type=int, default=3,
        help='the number of duplicate ACKs for a fast retransmit. 0 to disable.'
    )

    parser.add_argument(
        '-q', '--queue',
        type=int, nargs='?',
        help='the queue size, infinite by default'
    )

    args = parser.parse_args()

    # parameters
    Sim.scheduler.reset()
    Sim.set_debug('TransferTester')
    Sim.set_debug('TCP')
    Sim.set_debug('Link')

    # setup network
    net = NetHelper('two_nodes.txt')
    net.loss(args.loss)
    if args.queue is not None:
        net.queue(args.queue)

    # setup routes
    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    net.forward_links((n1, n2))

    # setup transport
    t1 = Transport(n1)
    t2 = Transport(n2)

    capture = PacketSniffer(n2, 'TCP')
    # setup application
    tester = TransferTester(args.infile)

    # setup connection
    n1_n2 = net.resolve_dest_address(n1, n2)
    n2_n1 = net.resolve_dest_address(n2, n1)

    c1 = TCP(t1, n2_n1, 1, n1_n2, 1, tester, window=args.window, fast_retransmit=args.fast_retransmit)
    c2 = TCP(t2, n1_n2, 1, n2_n1, 1, tester, window=args.window, fast_retransmit=args.fast_retransmit)

    tester.test(c1.send)

    # run the simulation
    Sim.scheduler.run()
    tester.check()
    p = capture.packets[-1]
    print('Transmission: %5f' % (8 * tester.length / (p.enter_queue + p.transmission_delay + p.propagation_delay)))
    print('QueueDelay: %5f' % (sum(p.queueing_delay for p in capture.packets) / len(capture.packets)))


if __name__ == '__main__':
    main()
