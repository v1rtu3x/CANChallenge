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

INTERVAL_S = 240         # broadcast period
FRAME_DELAY_S = 0.05       # 50 ms between consecutive frames
QUIET_GRACE_S = 0.2        # small settle time after pause

LEADING_ZERO_BYTES = 128   # prepend zeros so the start is easily visible
TRAILING_ZERO_BYTES = 128  # append zeros so the end is clearly visible

# Countdown lengths (seconds)
PRE_COUNTDOWN_S = 5
POST_COUNTDOWN_S = 3

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

def _get_bus_safe(existing_bus: Optional[can.Bus] = None) -> Optional[can.Bus]:
    """Best-effort to acquire a CAN bus (preferring io_can)."""
    if existing_bus is not None:
        return existing_bus
    try:
        return get_bus()
    except Exception:
        try:
            return can.interface.Bus(channel="vcan0", bustype="socketcan")
        except Exception as ex:
            print(f"[HEX] could not open CAN bus: {ex}")
            return None

def _send_chunk(chunk: bytes, arb_id: int, bus: Optional[can.Bus]) -> bool:
    """Send one 8-byte chunk. Returns True on success, False on failure."""
    try:
        send_can_frame(arb_id, chunk, bus=bus)
        return True
    except Exception:
        try:
            if bus is None:
                bus = _get_bus_safe(None)
            if bus is None:
                return False
            msg = can.Message(arbitration_id=arb_id, data=chunk, is_extended_id=False)
            bus.send(msg)
            return True
        except Exception as ex:
            print(f"[HEX] send failed: {ex}")
            return False

def _send_countdown(seconds: int, arb_id: int):
    """
    Broadcast a countdown to vcan0. For each whole second N (seconds down to 1),
    repeatedly send frames whose 8-byte payload is filled with 0xNN (e.g., N=5 -> 0x55...).
    """
    if seconds <= 0:
        return

    bus = _get_bus_safe(None)
    for n in range(seconds, 0, -1):
        # Build one 8-byte payload filled with the hex digit nn (e.g., 0x55)
        try:
            byte_val = int(f"{n}{n}", 16)  # 5->0x55, 4->0x44, ..., 1->0x11
        except ValueError:
            byte_val = 0x11  # fallback, shouldn't happen

        payload = bytes([byte_val]) * 8
        t_end = time.perf_counter() + 1.0

        print(f"[HEX] countdown second {n}: broadcasting {payload.hex()} on 0x{arb_id:03X}")
        while time.perf_counter() < t_end:
            ok = _send_chunk(payload, arb_id, bus)
            if not ok:
                # try to reopen bus once if we lost it
                bus = _get_bus_safe(bus)
            time.sleep(FRAME_DELAY_S)

def _send_bytes(blob: bytes, arb_id: int):
    bus = _get_bus_safe(None)

    # Add visible zero runway before and after
    blob = (b"\x00" * LEADING_ZERO_BYTES) + blob + (b"\x00" * TRAILING_ZERO_BYTES)

    total = len(blob)
    nframes = (total + 7) // 8
    print(f"[HEX] sending {total} bytes in {nframes} frames on 0x{arb_id:03X}")

    for i in range(0, total, 8):
        chunk = blob[i:i+8]
        if len(chunk) < 8:
            chunk = chunk + bytes(8 - len(chunk))
        ok = _send_chunk(chunk, arb_id, bus)
        if not ok:
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

        # ===== Pre-countdown (5 → 1) =====
        _send_countdown(PRE_COUNTDOWN_S, ARB_ID)

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

        # ===== Post-countdown (3 → 1) =====
        _send_countdown(POST_COUNTDOWN_S, ARB_ID)

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
