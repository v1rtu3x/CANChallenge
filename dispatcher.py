# CANChallenge/dispatcher.py
import can
from challenges import arbitration, rolling_crc, timing_replay, majority_spoof

# Pause switch used by the ELF broadcaster to temporarily stop routing.
DISPATCHER_PAUSED = False

def pause_dispatcher():
    global DISPATCHER_PAUSED
    DISPATCHER_PAUSED = True
    print("[DISPATCH] paused")

def resume_dispatcher():
    global DISPATCHER_PAUSED
    DISPATCHER_PAUSED = False
    print("[DISPATCH] resumed")


def handle_can_message(msg: can.Message):
    """
    Central message dispatcher.
    Routes incoming CAN messages to the correct challenge handler.
    For now, only logs arbitration ID and data.
    """
    try:
        # Short-circuit when paused (ELF broadcast window)
        if DISPATCHER_PAUSED:
            return

        arb_id = msg.arbitration_id
        data = list(msg.data)

        print(f"[DISPATCH] ID=0x{arb_id:03X}, Data={[hex(b) for b in data]}")

        # Arbitration / low-id handler
        if arb_id <= 0x00F or arb_id in (0x014, 0x215):
            arbitration.handle(msg)
            return

        # Rolling CRC handler
        if arb_id == 0x2A1:
            rolling_crc.handle(msg)
            return

        # Timing replay
        if arb_id == 0x440:
            timing_replay.handle(msg)
            return

        # Majority spoof + related IDs
        if arb_id in (0x120, 0x121, 0x122, 0x210, 0x2B0):
            majority_spoof.handle(msg)
            return

        # Add other routes here (e.g., lfsr_token, startup flag is not message-driven)
    except Exception as e:
        print(f"[DISPATCH ERROR] {e}")
