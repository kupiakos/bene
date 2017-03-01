
from __future__ import print_function

import sys

sys.path.append('..')

from src.sim import Sim
from src.transport import Transport
from src.tcp import TCP
from lab1.nethelper import NetHelper

import optparse
import os
import subprocess


class AppHandler(object):
    def __init__(self, filename):
        self.filename = filename
        self.directory = 'received'
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.f = open(os.path.join(self.directory, self.filename), 'wb')

    def receive_data(self, data):
        Sim.trace('AppHandler', "application got %d bytes" % (len(data)))
        self.f.write(data)
        self.f.flush()


class Main(object):
    def __init__(self):
        self.directory = 'received'
        self.parse_options()
        self.run()
        self.diff()
        self.filename = None
        self.loss = None

    def parse_options(self):
        parser = optparse.OptionParser(usage="%prog [options]",
                                       version="%prog 0.1")

        parser.add_option("-f", "--filename", type="str", dest="filename",
                          default='test.txt',
                          help="filename to send")

        parser.add_option("-l", "--loss", type="float", dest="loss",
                          default=0.0,
                          help="random loss rate")

        (options, args) = parser.parse_args()
        self.filename = options.filename
        self.loss = options.loss

    def diff(self):
        args = ['diff', '-u', self.filename, os.path.join(self.directory, self.filename)]
        result = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
        print()
        if not result:
            print("File transfer correct!")
        else:
            print("File transfer failed. Here is the diff:")
            print()
            print(result)

    def run(self):
        # parameters
        Sim.scheduler.reset()
        Sim.set_debug('AppHandler')
        Sim.set_debug('TCP')
        Sim.set_debug('Link')

        # setup network
        net = NetHelper('../networks/one-hop.txt')
        net.loss(self.loss)

        # setup routes
        n1 = net.get_node('n1')
        n2 = net.get_node('n2')
        net.forward_links((n1, n2))

        # setup transport
        t1 = Transport(n1)
        t2 = Transport(n2)

        # setup application
        a = AppHandler(self.filename)

        # setup connection
        n1_n2 = net.resolve_dest_address(n1, n2)
        n2_n1 = net.resolve_dest_address(n2, n1)

        c1 = TCP(t1, n2_n1, 1, n1_n2, 1, a, window=3000)
        c2 = TCP(t2, n1_n2, 1, n2_n1, 1, a, window=3000)

        # send a file
        with open(self.filename, 'rb') as f:
            while True:
                data = f.read(1000)
                if not data:
                    break
                Sim.scheduler.add(delay=0, event=data, handler=c1.send)

        # run the simulation
        Sim.scheduler.run()


if __name__ == '__main__':
    m = Main()
