# CANChallenge/dispatcher.py
import can
from challenges import arbitration, rolling_crc, timing_replay, majority_spoof, lfsr_token

def handle_can_message(msg: can.Message):
    """
    Central message dispatcher.
    Routes incoming CAN messages to the correct challenge handler.
    For now, only logs arbitration ID and data.
    """
    try:
        arb_id = msg.arbitration_id
        data = list(msg.data)

        print(f"[DISPATCH] ID=0x{arb_id:03X}, Data={[hex(b) for b in data]}")
        if arb_id <= 0x00F or arb_id in (0x014, 0x215):
            arbitration.handle(msg)
            return

        # Placeholder routing (to be filled as we implement challenges)
        # Rolling counter + CRC (0x2A1)
        if arb_id == 0x2A1:
            rolling_crc.handle(msg)
            return
        elif arb_id <= 0x00F or arb_id in (0x014, 0x215):
            # from challenges import arbitration
            # arbitration.handle(msg)
            return
        elif arb_id == 0x440:
            timing_replay.handle(msg)
            return
        elif arb_id in (0x120, 0x121, 0x122, 0x210, 0x2B0):
            majority_spoof.handle(msg)
            return

    except Exception as e:
        print(f"[DISPATCH ERROR] {e}")
