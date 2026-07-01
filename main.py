import json
import time
import logging
from rdt3 import RDT3Sender, UnreliableChannel, RDT3Receiver

def run_scenario(name: str, loss: float, corrupt: float, messages: list, timeout_ms=500):
    print("\n" + "#" * 50)
    print(f"  Scenario: {name}")
    print(f"  loss={loss*100:.0f}%  corrupt={corrupt*100:.0f}%  timeout={timeout_ms}ms")
    print("#" * 50)

    channel = UnreliableChannel(loss_prob=loss, corrupt_prob=corrupt)
    receiver = RDT3Receiver(channel)
    channel.set_receiver(receiver)
    sender = RDT3Sender(channel, timeout_ms=timeout_ms)

    start = time.time()
    for msg in messages:
        data = msg.encode("utf-8")
        sender.send_rdt(data)

    elapsed = time.time() - start
    print(f"\n  Total time: {elapsed*1000:.1f} ms for {len(messages)} messages")
    sender.print_stats()

def main():
    try:
        with open("messages.json", "r", encoding="utf-8") as f:
            msgs = json.load(f)["messages"]
    except Exception:
        msgs = ["Default Message 1", "Default Message 2"]

    run_scenario("Ideal Channel (No errors)", 0.0, 0.0, msgs)
    run_scenario("Packet Loss 20%", 0.2, 0.0, msgs)
    run_scenario("Corruption 20%", 0.0, 0.2, msgs)
    run_scenario("Loss 15% + Corruption 15%", 0.15, 0.15, msgs, timeout_ms=300)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    main()
