import unittest
from typing import Dict

import math

from lab5.nethelper import NetHelper
from lab5.router import Router, DvrPacket
from src.node import Node
from src.sim import Sim


class TestRouter(unittest.TestCase):
    def setUp(self):
        Sim.scheduler.reset()
        self.net = NetHelper('networks/fifteen-nodes.txt')
        self.r = {  # type: Dict[str, Router]
            name: Router(node)
            for name, node in self.net.nodes.items()
        }
        self.n = self.net.nodes  # type: Dict[str, Node]
        self.assertEqual(len(self.r), 15)
        for name, router in self.r.items():
            self.assertIsInstance(router, Router)
            node = self.n[name]
            self.assertIs(node, router.node)
            self.assertIs(node.protocols.get('dvr'), router)

    def test_initial_state(self):
        r = self.r['n2']  # type: Router
        self.assertDictEqual(r.distance_vector, {rl.address: 0 for rl in r.node.recv_links})
        self.assertDictEqual(r.host_links, {'n2': {l.address for l in r.node.recv_links}})

    def test_receive_packet(self):
        # This is actually an integration test, but who's keeping score?
        r = self.r['n1']  # type: Router
        n1 = self.n['n1']
        n2 = self.n['n2']  # type: Node
        tol_n2 = n1.get_link('n2')
        cost_n2 = r._link_cost(tol_n2)
        n2ls = {l.endpoint.hostname: l.address for l in n2.links}
        n15l = self.n['n15'].recv_links[0].address
        dv = {
            tol_n2.address: 0,
            n2ls['n8']: 2,
            n2ls['n3']: 1,
            n2ls['n14']: 2,
            n15l: 5,
        }
        hl = {
            # Include a fake link not in the distance vector
            'n13': {1000},
            'n3': {n2ls['n3']},
            'n15': {n15l},
            # Purposefully leave out link for n8, n14
        }
        p = DvrPacket('n2', dv, hl)
        r.receive_packet(p)

        dv_check = dv.copy()
        # Each distance vector entry will be increased by the cost from n1->n2
        for a in dv_check:
            dv_check[a] += cost_n2
        # A node knows the cost to its own links is 0
        for rl in n1.recv_links:
            dv_check[rl.address] = 0

        self.assertDictEqual(r.distance_vector, dv_check)

        hl_check = hl.copy()
        # A node knows about its own links
        hl_check['n1'] = {l.address for l in r.node.recv_links}
        # n1 knows about n2 due to the packet being sent
        hl_check['n2'] = {tol_n2.address}
        self.assertDictEqual(r.host_links, hl_check)

        forward_check = {d: tol_n2 for d in dv.keys()}
        self.assertDictEqual(n1.forwarding_table, forward_check)

        # Working connections
        self.assertEqual(r.best_address('n3'), n2ls['n3'])
        self.assertEqual(r.best_address('n15'), n15l)
        # Included in the host links but no known distance
        self.assertIsNone(r.best_address('n13'))
        # Included in the distance vector but no known host link
        self.assertIsNone(r.best_address('n8'))
        self.assertIsNone(r.best_address('n14'))
        # Should be able to send to "localhost"
        self.assertIsNotNone(r.best_address('n1'))

        # Test with an update of existing data
        n4 = self.n['n4']
        n4ls = {l.endpoint.hostname: l.address for l in n4.links}
        tol_n4 = n1.get_link('n4')
        cost_n4 = r._link_cost(tol_n4)
        n8l = next(l.address for l in self.n['n8'].recv_links if l.address != n2ls['n8'])
        n14l = next(l.address for l in self.n['n14'].recv_links if l.address != n2ls['n14'])
        dv2 = {
            tol_n4.address: 0,
            # Pointing to n1, should be ignored
            n4ls['n1']: 1,
            # Beating n2's cost for n15 with the same address
            n15l: 2,
            # Beating n2's cost for n8 with a different address
            n8l: 1,
            # Not beating n2's cost with the same address
            n2ls['n3']: 1,
            # Not beating n2's cost with a different address
            n14l: 3,
        }
        hl2 = {
            'n8': {n2ls['n8'], n8l},
            'n14': {n14l, n2ls['n14']},
        }
        p = DvrPacket('n4', dv2, hl2)
        r.receive_packet(p)

        dv_check[tol_n4.address] = cost_n4
        dv_check[n15l] = dv2[n15l] + cost_n4
        dv_check[n8l] = dv2[n8l] + cost_n4
        dv_check[n14l] = dv2[n14l] + cost_n4
        # Was created as a side-effect of the tests above
        dv_check[1000] = math.inf

        self.assertDictEqual(r.distance_vector, dv_check)

        hl_check.update(hl2)
        # n1 knows about n4 due to the packet being sent
        hl_check['n4'] = {tol_n4.address}
        self.assertDictEqual(r.host_links, hl_check)

        forward_check[tol_n4.address] = tol_n4
        forward_check[n15l] = tol_n4
        forward_check[n8l] = tol_n4
        forward_check[n14l] = tol_n4
        self.assertDictEqual(n1.forwarding_table, forward_check)

        # Working connections
        self.assertEqual(r.best_address('n3'), n2ls['n3'])
        self.assertEqual(r.best_address('n15'), n15l)
        self.assertEqual(r.best_address('n8'), n8l)
        self.assertEqual(r.best_address('n14'), n2ls['n14'])
        # Included in the host links but no known distance
        self.assertIsNone(r.best_address('n13'))
        # Should be able to send to "localhost"
        self.assertIsNotNone(r.best_address('n1'))






if __name__ == '__main__':
    unittest.main()
