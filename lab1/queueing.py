#!/usr/bin/env python3
import random
import sys
sys.path.append('..')

from src.node import Node
from src.sim import Sim
from lab2.nethelper import NetHelper

class DelayHandler:
    utilization = 0
    def receive_packet(self, packet):
        print('%f,%f' % (self.utilization, packet.queueing_delay))

class Generator(object):
    def __init__(self, net: NetHelper, src: Node, dest: Node, load: float, duration: float):
        self.net = net
        self.src = src
        self.dest = dest
        self.load = load
        self.duration = duration
        self.start = 0

    def handle(self, event):
        # quit if done
        now = Sim.scheduler.current_time()
        if (now - self.start) > self.duration:
            return

        # generate a packet
        self.net.send_packet(0, self.src, self.dest)
        # schedule the next time we should generate a packet
        Sim.scheduler.add(delay=random.expovariate(self.load), event='generate', handler=self.handle)

def main():
    net = NetHelper('two_nodes.txt')

    n1 = net.get_node('n1')
    n2 = net.get_node('n2')
    net.forward_links((n1, n2))
    handler = DelayHandler()

    bandwidth = 1.*10**3
    size = 1000
    duration = 100000
    delta = .02
    start = .02

    net.add_protocol(protocol='report', handler=handler)
    net.default_protocol = 'report'
    net.default_length = size
    net.reset_all_links(propagation=1., bandwidth=bandwidth)

    # Sim.set_debug('Node')
    handler.utilization = start
    while handler.utilization < 1:
        max_rate = bandwidth / (size * 8)
        load = handler.utilization * max_rate
        gen = Generator(net, n1, n2, load, duration)
        with net:
            Sim.scheduler.add(delay=0, event='generate', handler=gen.handle)
        handler.utilization += delta

if __name__ == '__main__':
    main()

