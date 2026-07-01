import time
import unittest
import threading
from rdt3 import (
    pad_to_multiple_of_16, crc16, make_pkt, parse_pkt,
    is_corrupt, Timer, UnreliableChannel, RDT3Sender, RDT3Receiver
)

class TestPadding(unittest.TestCase):
    def test_already_multiple(self):
        data = b"AB"
        self.assertEqual(pad_to_multiple_of_16(data), data)

    def test_needs_padding(self):
        data = b"A"
        padded = pad_to_multiple_of_16(data)
        self.assertEqual(len(padded), 2)
        self.assertEqual(padded[1], 0)

class TestCRC16(unittest.TestCase):
    def test_known_value(self):
        self.assertEqual(crc16(b"123456789"), 0x29B1)

    def test_corrupt_detection(self):
        pkt = bytearray(make_pkt(0, b"test data"))
        pkt[-1] ^= 0xFF
        self.assertTrue(is_corrupt(parse_pkt(bytes(pkt))))

class TestTimer(unittest.TestCase):
    def test_timer_thread_safety(self):
        fired = []
        t = Timer(100, lambda: fired.append(True))
        t.start()
        t.start()
        t.stop()
        time.sleep(0.2)
        self.assertEqual(len(fired), 0)

class TestNetworkConditions(unittest.TestCase):
    def test_packet_loss_and_timeout(self):
        channel = UnreliableChannel(loss_prob=1.0, corrupt_prob=0.0)
        receiver = RDT3Receiver(channel)
        channel.set_receiver(receiver)
        sender = RDT3Sender(channel, timeout_ms=50)

        def run_sender():
            sender.send_rdt(b"timeout_test")

        t = threading.Thread(target=run_sender)
        t.daemon = True
        t.start()

        time.sleep(0.15)
        
        self.assertGreater(sender.stats["timeouts"], 0)
        self.assertGreater(sender.stats["retransmit"], 0)
        sender.timer.stop()

    def test_corrupt_ack(self):
        channel = UnreliableChannel(loss_prob=0.0, corrupt_prob=0.0)
        receiver = RDT3Receiver(channel)
        channel.set_receiver(receiver)
        sender = RDT3Sender(channel, timeout_ms=200)

        ack = bytearray(make_pkt(0, b""))
        ack[-1] ^= 0xFF
        channel.send_udt(bytes(ack), to_sender=True)
        
        raw = channel.rdt_rcv(from_sender=True)
        self.assertTrue(is_corrupt(parse_pkt(raw)))

class TestFSM(unittest.TestCase):
    def test_ideal_channel(self):
        channel = UnreliableChannel(loss_prob=0.0, corrupt_prob=0.0)
        receiver = RDT3Receiver(channel)
        channel.set_receiver(receiver)
        sender = RDT3Sender(channel, timeout_ms=300)
        
        for msg in [b"Hello", b"World", b"Test!"]:
            sender.send_rdt(msg)
            
        self.assertEqual(sender.stats["retransmit"], 0)
        self.assertEqual(sender.stats["ack_received"], 3)

    def test_sequence_alternates(self):
        channel = UnreliableChannel(0.0, 0.0)
        receiver = RDT3Receiver(channel)
        channel.set_receiver(receiver)
        sender = RDT3Sender(channel, timeout_ms=300)

        self.assertEqual(sender.state, "WAIT_CALL_0")
        sender.send_rdt(b"msg1")
        self.assertEqual(sender.state, "WAIT_CALL_1")
        sender.send_rdt(b"msg2")
        self.assertEqual(sender.state, "WAIT_CALL_0")

if __name__ == "__main__":
    unittest.main(verbosity=2)
