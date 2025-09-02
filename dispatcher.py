# CANChallenge/dispatcher.py
import can

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

        # Placeholder routing (to be filled as we implement challenges)
        if arb_id == 0x2A1:
            # from challenges import rolling_crc
            # rolling_crc.handle(msg)
            pass
        elif arb_id <= 0x00F or arb_id in (0x014, 0x215):
            # from challenges import arbitration
            # arbitration.handle(msg)
            pass
        elif arb_id == 0x440:
            # from challenges import timing_replay
            # timing_replay.handle(msg)
            pass
        elif arb_id in (0x120, 0x121, 0x122, 0x210, 0x2B0):
            # from challenges import majority_vote
            # majority_vote.handle(msg)
            pass
        elif arb_id == 0x211:
            # from challenges import lfsr_token
            # lfsr_token.handle(msg)
            pass
        # Startup flag is emitted at boot, not triggered by messages

    except Exception as e:
        print(f"[DISPATCH ERROR] {e}")
