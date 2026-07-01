# RDT 3.0 Protocol Implementation Project

## Introduction
Implementation of the Finite State Machine (FSM) for both sender and receiver of the Reliable Data Transfer (RDT) 3.0 protocol in Python.

---

## Requirements
- Python 3.10+
- Modules (All from Python Standard Library):
  - `struct`
  - `threading`
  - `random`
  - `logging`
  - `time`
  - `unittest`

---

## Project Structure
```text
rdt3_project/
│
├── rdt3.py
├── main.py
├── test_rdt3.py
├── README.md
└── messages.json

```

---

## FSM Architecture

### Sender FSM (4 States)

| Current State | Event | Action | Next State |
| --- | --- | --- | --- |
| `WAIT_CALL_0` | Data from app layer | Make sndpkt 0, Send, Start Timer | `WAIT_ACK_0` |
| `WAIT_ACK_0` | Corrupt ACK OR ACK 1 | Ignore | `WAIT_ACK_0` |
| `WAIT_ACK_0` | Timeout | Resend sndpkt 0, Restart Timer | `WAIT_ACK_0` |
| `WAIT_ACK_0` | Receive valid ACK 0 | Stop Timer | `WAIT_CALL_1` |
| `WAIT_CALL_1` | Data from app layer | Make sndpkt 1, Send, Start Timer | `WAIT_ACK_1` |
| `WAIT_ACK_1` | Corrupt ACK OR ACK 0 | Ignore | `WAIT_ACK_1` |
| `WAIT_ACK_1` | Timeout | Resend sndpkt 1, Restart Timer | `WAIT_ACK_1` |
| `WAIT_ACK_1` | Receive valid ACK 1 | Stop Timer | `WAIT_CALL_0` |

### Receiver FSM (2 States)

| Expected Seq | Event | Action | Next State |
| --- | --- | --- | --- |
| `0` | Receive valid rcvpkt 0 | Extract payload, `deliver_data()`, Send ACK 0 | `1` |
| `0` | Corrupt rcvpkt OR rcvpkt 1 | Send ACK 1 | `0` |
| `1` | Receive valid rcvpkt 1 | Extract payload, `deliver_data()`, Send ACK 1 | `0` |
| `1` | Corrupt rcvpkt OR rcvpkt 0 | Send ACK 0 | `1` |

---

## Packet Structure

```text
Header (32 bits)
Sequence: 16 bits
Checksum: 16 bits
Payload: variable length padded to multiple of 16 bits

```

## How to Run

```bash
python main.py
python -m unittest test_rdt3.py -v

```

