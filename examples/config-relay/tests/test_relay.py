import unittest
from relay import Relay
from settings import read_limit
from transport import Transport

class RelayTests(unittest.TestCase):
    def test_effective_limit(self):
        self.assertEqual(read_limit({'pending': 100}), 8)
        self.assertEqual(read_limit({'pending': 0}), 1)

    def test_duplicate_and_capacity(self):
        relay = Relay(Transport(), {'pending': 1})
        self.assertEqual(relay.accept({'device': 'a', 'seq': 1}), 'accepted')
        self.assertEqual(relay.accept({'device': 'a', 'seq': 1}), 'duplicate')
        self.assertEqual(relay.accept({'device': 'b', 'seq': 1}), 'capacity')

    def test_offline_acceptance_still_advances_deduplication(self):
        transport = Transport()
        transport.online = False
        relay = Relay(transport, {})
        self.assertEqual(relay.accept({'device': 'a', 'seq': 2}), 'accepted')
        self.assertEqual(relay.accept({'device': 'a', 'seq': 2}), 'duplicate')
        self.assertEqual(transport.sent, [])

    def test_reconfigure_rejects_shrink_without_epoch_change(self):
        relay = Relay(Transport(), {'pending': 3})
        for device in ('a', 'b'):
            relay.accept({'device': device, 'seq': 0})
        self.assertFalse(relay.configure({'pending': 1}))
        self.assertEqual((relay.limit, relay.epoch), (3, 0))

    def test_disconnect_releases_capacity(self):
        relay = Relay(Transport(), {'pending': 1})
        relay.accept({'device': 'a', 'seq': 1})
        relay.disconnect('a')
        self.assertEqual(relay.accept({'device': 'b', 'seq': 0}), 'accepted')

    def test_malformed_fields_fail_before_state_change(self):
        relay = Relay(Transport(), {})
        with self.assertRaises(KeyError): relay.accept({'device': 'a'})
        with self.assertRaises(ValueError): relay.accept({'device': 'a', 'seq': 'bad'})
        self.assertEqual(relay.latest, {})
