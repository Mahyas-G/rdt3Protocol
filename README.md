# Reliable Data Transfer (RDT 3.0) Simulation

A clean, thread-safe Python implementation of the **RDT 3.0 (Stop-and-Wait)** protocol operating over an unreliable network layer. This project simulates packet transmission, bit corruption, packet loss, timeout handling, and automatic retransmissions using a standard CRC-16 checksum algorithm.

## Project Structure

The project consists of three core Python files:
* **`rdt3.py`**: The core implementation containing the `RDT3Sender` and `RDT3Receiver` Finite State Machines (FSMs), the `Timer` utility, the `UnreliableChannel` simulation, and helper functions for CRC-16 error-detection and 16-bit word alignment padding.
* **`main.py`**: An automated test harness that runs multiple network simulation scenarios (Ideal Channel, 20% Packet Loss, 20% Packet Corruption, and Mixed Conditions) to measure channel performance and efficiency.
* **`test_rdt3.py`**: A robust unit-testing suite covering bit-level validation, packet padding, FSM transitions, and behavior under simulated packet losses/corruptions.


## Requirements

* **Python 3.8 or higher**
* No external packages or dependencies are required; the project relies entirely on Python's built-in `struct`, `threading`, `time`, `random`, and `unittest` modules.

## How to Run

### 1. Running the Main Simulation

To run the automated scenarios and view performance statistics (such as packet loss recoveries, timeout frequencies, and overall channel efficiency metrics), execute:

```bash
python main.py

```

### 2. Running Unit Tests

To verify individual structural layers, state transitions, integrity checks, and thread safety across the protocol framework, run the testing module:

```bash
python test_rdt3.py

```

Alternatively, you can run it via the standard unittest CLI:

```bash
python -m unittest test_rdt3.py -v

```

## Simulation Scenarios Explained

When executing `main.py`, the simulation steps through four major network environments:

1. **Ideal Channel:** Proves protocol behavior when zero drops or modifications occur.
2. **Packet Loss (20%):** Tests the sender's millisecond-based countdown timer and automatic retransmission triggers.
3. **Corruption (20%):** Evaluates the CRC-16 error-detection mechanism where the receiver silently drops corrupt packets, forcing a sender timeout and subsequent recovery.
4. **Mixed Loss & Corruption (15% each):** Validates the full structural robustness of the stop-and-wait FSM under complex, unpredictable transmission faults.
