import struct
import threading
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rdt3")

HEADER_FORMAT = "!HH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def pad_to_multiple_of_16(data: bytes) -> bytes:
    remainder = len(data) % 2
    if remainder != 0:
        data += b'\x00'
    return data

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return crc

def make_pkt(seq: int, data: bytes) -> bytes:
    payload = pad_to_multiple_of_16(data)
    seq_bytes = struct.pack("!H", seq)
    checksum = crc16(seq_bytes + payload)
    return struct.pack(HEADER_FORMAT, seq, checksum) + payload

def parse_pkt(raw: bytes) -> dict:
    seq, chk = struct.unpack_from(HEADER_FORMAT, raw, 0)
    payload = raw[HEADER_SIZE:]
    return {"sequence": seq, "checksum": chk, "payload": payload}

def is_corrupt(pkt_dict: dict) -> bool:
    seq_bytes = struct.pack("!H", pkt_dict["sequence"])
    expected = crc16(seq_bytes + pkt_dict["payload"])
    return expected != pkt_dict["checksum"]

class Timer:
    def __init__(self, timeout_ms: float, callback):
        self.timeout_ms = timeout_ms
        self.callback = callback
        self._timer = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self._cancel_internal()
            self._timer = threading.Timer(self.timeout_ms / 1000.0, self._timer_trigger)
            self._timer.daemon = True
            self._timer.start()
        log.debug(f"Timer started: {self.timeout_ms} ms")

    def stop(self):
        with self._lock:
            self._cancel_internal()

    def _cancel_internal(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _timer_trigger(self):
        self.callback()

class UnreliableChannel:
    def __init__(self, loss_prob=0.1, corrupt_prob=0.1):
        self.loss_prob = loss_prob
        self.corrupt_prob = corrupt_prob
        self.sender_buffer = []
        self.receiver_buffer = []
        self._lock = threading.Lock()
        self.receiver = None

    def set_receiver(self, receiver):
        self.receiver = receiver

    def send_udt(self, packet: bytes, to_sender=False):
        if random.random() < self.loss_prob:
            log.warning("Packet dropped by channel!")
            return

        if random.random() < self.corrupt_prob:
            pkt_arr = bytearray(packet)
            if len(pkt_arr) > 0:
                idx = random.randint(0, len(pkt_arr) - 1)
                pkt_arr[idx] ^= 0xFF
            packet = bytes(pkt_arr)
            log.warning("Packet corrupted by channel!")

        with self._lock:
            if to_sender:
                self.sender_buffer.append(packet)
            else:
                self.receiver_buffer.append(packet)

        if not to_sender and self.receiver:
            self.receiver.process_incoming()

    def rdt_rcv(self, from_sender=False) -> bytes | None:
        with self._lock:
            buffer = self.sender_buffer if from_sender else self.receiver_buffer
            if buffer:
                return buffer.pop(0)
        return None

class RDT3Receiver:
    def __init__(self, channel: UnreliableChannel):
        self.channel = channel
        self.expected_seq = 0

    def deliver_data(self, data: bytes):
        log.info(f"Data delivered to application layer: {data}")

    def process_incoming(self):
        while True:
            raw = self.channel.rdt_rcv(from_sender=False)
            if raw is None:
                break

            pkt = parse_pkt(raw)
            if is_corrupt(pkt):
                log.warning("Receiver detected corruption. Resending previous ACK.")
                ack_pkt = make_pkt(1 - self.expected_seq, b"")
                self.channel.send_udt(ack_pkt, to_sender=True)
                continue

            if pkt["sequence"] == self.expected_seq:
                payload = pkt["payload"].rstrip(b'\x00')
                self.deliver_data(payload)
                ack_pkt = make_pkt(self.expected_seq, b"")
                log.info(f"Receiver sending ACK {self.expected_seq}")
                self.channel.send_udt(ack_pkt, to_sender=True)
                self.expected_seq = 1 - self.expected_seq
            else:
                log.warning(f"Receiver got unexpected seq {pkt['sequence']}. Resending ACK {1 - self.expected_seq}")
                ack_pkt = make_pkt(1 - self.expected_seq, b"")
                self.channel.send_udt(ack_pkt, to_sender=True)

class RDT3Sender:
    def __init__(self, channel: UnreliableChannel, timeout_ms=500):
        self.channel = channel
        self.state = "WAIT_CALL_0"
        self.sndpkt = None
        self.timeout_occurred = False
        self.timer = Timer(timeout_ms, self._on_timeout)
        self.stats = {"sent": 0, "retransmit": 0, "ack_received": 0, "corrupt_ack": 0, "timeouts": 0}

    def _on_timeout(self):
        self.timeout_occurred = True
        self.stats["timeouts"] += 1

    def send_rdt(self, data: bytes):
        if self.state == "WAIT_CALL_0":
            self.sndpkt = make_pkt(0, data)
            self.channel.send_udt(self.sndpkt, to_sender=False)
            self.timer.start()
            self.stats["sent"] += 1
            self.state = "WAIT_ACK_0"
            self._wait_for_ack(0, "WAIT_CALL_1")
        elif self.state == "WAIT_CALL_1":
            self.sndpkt = make_pkt(1, data)
            self.channel.send_udt(self.sndpkt, to_sender=False)
            self.timer.start()
            self.stats["sent"] += 1
            self.state = "WAIT_ACK_1"
            self._wait_for_ack(1, "WAIT_CALL_0")

    def _wait_for_ack(self, expected_seq: int, next_state: str):
        self.timeout_occurred = False
        while True:
            if self.timeout_occurred:
                log.warning(f"Timeout! Resending packet seq={expected_seq}")
                self.timeout_occurred = False
                self.channel.send_udt(self.sndpkt, to_sender=False)
                self.timer.start()
                self.stats["retransmit"] += 1
                continue

            raw = self.channel.rdt_rcv(from_sender=True)
            if raw is None:
                time.sleep(0.01)
                continue

            pkt = parse_pkt(raw)
            if is_corrupt(pkt):
                log.warning("Sender received corrupt ACK. Ignoring.")
                self.stats["corrupt_ack"] += 1
                continue

            if pkt["sequence"] == expected_seq:
                self.timer.stop()
                self.stats["ack_received"] += 1
                self.state = next_state
                log.info(f"ACK {expected_seq} received. State -> {self.state}")
                break
            else:
                log.warning(f"Sender received wrong ACK seq={pkt['sequence']}. Ignoring.")
                continue

    def print_stats(self):
        print("\n" + "=" * 45)
        print("       RDT 3.0 Sender Statistics")
        print("=" * 45)
        print(f"  Packets Sent           : {self.stats['sent']}")
        print(f"  Retransmissions        : {self.stats['retransmit']}")
        print(f"  ACKs Received          : {self.stats['ack_received']}")
        print(f"  Corrupt ACKs           : {self.stats['corrupt_ack']}")
        print(f"  Timeouts               : {self.stats['timeouts']}")
        total = self.stats["sent"] + self.stats["retransmit"]
        if total > 0:
            eff = self.stats["ack_received"] / total * 100
            print(f"  Channel Efficiency     : {eff:.1f}%")
        print("=" * 45 + "\n")
