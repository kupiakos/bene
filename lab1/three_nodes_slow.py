#!/usr/bin/env python3

import sys
sys.path.append('..')

from src.nethelper import NetHelper
from lab1.reporthandler import ReportHandler

def main():
    net = NetHelper('three_nodes_slow.txt')

    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    n3 = net.get_node('n3')
    net.forward_route(net.find_route(n1, n3))

    net.add_protocol(protocol='report', handler=ReportHandler())
    net.default_protocol = 'report'
    net.default_length = 1000
    # Sim.set_debug('Node')

    with net:
        net.send_packet_stream(n1, n3, count=1000, length=1000)



if __name__ == '__main__':
    main()

