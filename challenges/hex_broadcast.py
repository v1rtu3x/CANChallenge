# challenges/hex_broadcast.py
import os
import re
import time
import threading
import subprocess
from typing import Optional

import can
from io_can import get_bus, send_can_frame
import dispatcher

HEX_PATH = "resources/payload.hex"  # text file with hex bytes (any separators/whitespace ok)
ARB_ID = 0x600

INTERVAL_S = 240           # broadcast period
FRAME_DELAY_S = 0.05        # 50 ms between consecutive frames
QUIET_GRACE_S = 0.2         # small settle time after pause

LEADING_ZERO_BYTES = 128     # prepend zeros so the start is easily visible
TRAILING_ZERO_BYTES = 128    # append zeros so the end is clearly visible

_thread: Optional[threading.Thread] = None

def _pkill(signal: str):
    """Send a signal to any running cangen processes (STOP or CONT)."""
    try:
        subprocess.run(["pkill", f"-{signal}", "-f", "cangen"], check=False)
        print(f"[HEX] sent SIG{signal} to cangen (if running)")
    except Exception as e:
        print(f"[HEX] pkill {signal} failed: {e}")

def _parse_hex_file(path: str) -> bytes:
    """
    Parse a text file containing hex bytes into raw bytes.
    Accepts multi-line content with arbitrary separators/whitespace/comments.
    Strategy: extract all pairs of hex digits and pack them.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    pairs = re.findall(r"(?i)[0-9a-f]{2}", text)
    return bytes(int(p, 16) for p in pairs)

def _send_bytes(blob: bytes, arb_id: int):
    try:
        bus = get_bus()
    except Exception:
        bus = None

    # Add visible zero runway before and after
    blob = (b"\x00" * LEADING_ZERO_BYTES) + blob + (b"\x00" * TRAILING_ZERO_BYTES)

    total = len(blob)
    nframes = (total + 7) // 8
    print(f"[HEX] sending {total} bytes in {nframes} frames on 0x{arb_id:03X}")

    for i in range(0, total, 8):
        chunk = blob[i:i+8]
        if len(chunk) < 8:
            chunk = chunk + bytes(8 - len(chunk))
        try:
            send_can_frame(arb_id, chunk, bus=bus)
        except Exception:
            try:
                if bus is None:
                    bus = can.interface.Bus(channel="vcan0", bustype="socketcan")
                msg = can.Message(arbitration_id=arb_id, data=chunk, is_extended_id=False)
                bus.send(msg)
            except Exception as ex:
                print(f"[HEX] send failed: {ex}")
                return
        time.sleep(FRAME_DELAY_S)

    print("[HEX] broadcast complete")

def _loop():
    while True:
        time.sleep(INTERVAL_S)

        print("[HEX] broadcast window opening: pausing dispatcher + cangen")
        dispatcher.pause_dispatcher()
        _pkill("STOP")
        time.sleep(QUIET_GRACE_S)

        if not os.path.isfile(HEX_PATH):
            print(f"[HEX] file not found: {HEX_PATH}")
        else:
            try:
                blob = _parse_hex_file(HEX_PATH)
                if len(blob) == 0:
                    print(f"[HEX] parsed 0 bytes from {HEX_PATH} (check file contents)")
                else:
                    _send_bytes(blob, ARB_ID)
            except Exception as e:
                print(f"[HEX] error while parsing/sending: {e}")

        time.sleep(QUIET_GRACE_S)
        _pkill("CONT")
        dispatcher.resume_dispatcher()
        print("[HEX] window closed: normal operation resumed")

def start():
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(target=_loop, name="hex_broadcast", daemon=True)
        _thread.start()
        print("[HEX] broadcaster started")
