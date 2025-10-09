# main.py
import sys
import threading
import can
from io_can import setup_vcan, start_cangen
from constants import VCAN_INTERFACE
from dispatcher import handle_can_message
from state import init_state
from challenges.startup_flag import send_startup_flag
from challenges import rolling_crc
from challenges import timing_replay
from challenges import hex_broadcast

def main():
    print("[INFO] Starting UDS ECU simulation with PCI")

    if not setup_vcan():
        print("[FATAL] Failed to setup vcan interface. Exiting.")
        return

    init_state()
    rolling_crc.start()
    timing_replay.start()
    threading.Thread(target=send_startup_flag, daemon=True).start()

    # Start normal sim traffic as before (unaltered)
    start_cangen()

    # Start periodic HEX broadcaster (pauses/resumes around bursts)
    hex_broadcast.start()

    bus = None
    try:
        bus = can.interface.Bus(channel=VCAN_INTERFACE, bustype='socketcan')
        print(f"[INFO] Listening on {VCAN_INTERFACE}... Ctrl+C to exit.")
        while True:
            msg = bus.recv(timeout=1.0)
            if msg is not None:
                handle_can_message(msg)

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt received. Shutting down cleanly...")

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

    finally:
        if bus is not None:
            try:
                bus.shutdown()
            except Exception:
                pass

if __name__ == "__main__":
    main()
