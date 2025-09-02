# CANChallenge/utils/flags.py
from io_can import send_can_frame

def chunk_and_send_flag(arb_id: int, flag_str: str):
    """
    Split flag string into 7-byte chunks and send each as a CAN frame.
    Byte0 = chunk index, Byte1..7 = ASCII chars (zero-padded if needed).
    """
    chunks = [flag_str[i:i+7] for i in range(0, len(flag_str), 7)]
    for idx, chunk in enumerate(chunks):
        data = [idx] + [ord(c) for c in chunk]
        # pad to 8 bytes
        while len(data) < 8:
            data.append(0x00)
        send_can_frame(arb_id, data)
    print(f"[FLAG] Sent flag on ID=0x{arb_id:03X}: {flag_str}")
