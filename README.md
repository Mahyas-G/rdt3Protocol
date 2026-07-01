# RDT 3.0 Protocol Implementation Project

## Introduction
Implementation of the Finite State Machine (FSM) for both sender and receiver of the Reliable Data Transfer (RDT) 3.0 protocol in Python.

---

## FSM Architecture

### Sender FSM (4 States)
| Current State | Event | Action | Next State |
|---------------|-------|--------|------------|
| `WAIT_CALL_0` | Data from app layer | Make pkt 0, Send, Start Timer | `WAIT_ACK_0` |
| `WAIT_ACK_0`  | Corrupt ACK OR ACK 1 | Ignore | `WAIT_ACK_0` |
| `WAIT_ACK_0`  | Timeout | Resend pkt 0, Restart Timer | `WAIT_ACK_0` |
| `WAIT_ACK_0`  | Receive valid ACK 0 | Stop Timer | `WAIT_CALL_1` |
| `WAIT_CALL_1` | Data from app layer | Make pkt 1, Send, Start Timer | `WAIT_ACK_1` |
| `WAIT_ACK_1`  | Corrupt ACK OR ACK 0 | Ignore | `WAIT_ACK_1` |
| `WAIT_ACK_1`  | Timeout | Resend pkt 1, Restart Timer | `WAIT_ACK_1` |
| `WAIT_ACK_1`  | Receive valid ACK 1 | Stop Timer | `WAIT_CALL_0` |

### Receiver FSM (2 States)
| Expected Seq | Event | Action | Next State |
|--------------|-------|--------|------------|
| `0` | Receive valid pkt 0 | Extract payload, `deliver_data()`, Send ACK 0 | `1` |
| `0` | Corrupt pkt OR pkt 1 | Send ACK 1 | `0` |
| `1` | Receive valid pkt 1 | Extract payload, `deliver_data()`, Send ACK 1 | `0` |
| `1` | Corrupt pkt OR pkt 0 | Send ACK 0 | `1` |

---

## Packet Structure
```text
| 16 bits Sequence Number | 16 bits Checksum (CRC16) | Payload (Padded to 16-bit) |

```

## How to Run

```bash
python main.py
python -m unittest test_rdt3.py -v

```
