#!/usr/bin/env python3

import sys
sys.path.append('..')

from src.sim import Sim
from lab1.nethelper import NetHelper
from lab1.reporthandler import ReportHandler

def main():
    net = NetHelper('two_nodes.txt')

    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    net.forward_links((n1, n2))

    net.add_protocol(protocol='report', handler=ReportHandler())
    net.default_protocol = 'report'
    net.default_length = 1000

    print('1 Mbps, 1 sec')
    # Sim.set_debug('Node')
    with net:
        net.reset_all_links(propagation=1., bandwidth=1.*10**6)
        net.send_packet(0, n1, n2)

    print('\n100 bps, 10 ms')
    with net:
        net.reset_all_links(propagation=1/1000, bandwidth=100.)
        net.send_packet(0, n1, n2)

    print('\n1 Mbps, 10 ms')
    with net:
        net.reset_all_links(propagation=1/1000, bandwidth=1.*10**6)
        for _ in range(3):
            net.send_packet(0, n1, n2)
        net.send_packet(2, n1, n2)



if __name__ == '__main__':
    main()

