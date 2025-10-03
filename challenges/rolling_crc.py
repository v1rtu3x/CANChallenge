# CANChallenge/challenges/rolling_crc.py
import random
import threading
import time
from typing import Optional

import can

from io_can import send_can_frame
from state import get_state, update_state

try:
    # Preferred way: use the project's chunker so long flags are sent nicely.
    from utils.flags import chunk_and_send_flag
except Exception:  # pragma: no cover - fallback for dev
    chunk_and_send_flag = None

# Observe broadcast pause flag from dispatcher (optional import)
try:
    import dispatcher
except Exception:
    dispatcher = None

def _is_paused() -> bool:
    try:
        return bool(getattr(dispatcher, "DISPATCHER_PAUSED", False))
    except Exception:
        return False

ARB_ID = 0x2A1
TICK_SECONDS = 15.0

# ---------------- CRC impl (poly 0x2F, init 0xFF) -----------------
def crc8_2f(data: bytes) -> int:
    crc = 0xFF  # Init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:  # check MSB
                crc = ((crc << 1) ^ 0x2F) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc ^ 0xFF  # Apply XorOut


# --------------- Emission & state housekeeping --------------------
def _pack(counter: int) -> bytes:
    """Build 8-byte payload: [ctr, 0,0,0,0,0,0, crc]."""
    body = bytes([counter & 0xFF, 0, 0, 0, 0, 0, 0])
    c = crc8_2f(body)
    return body + bytes([c])

def _safe_send(arb: int, payload: bytes) -> None:
    """Send only when not paused; wait out broadcast windows."""
    while _is_paused():
        time.sleep(0.05)
    send_can_frame(arb, payload)

def _emit_current() -> None:
    st = get_state("rolling_crc") or {}
    ctr = st.get("counter", 0)
    payload = _pack(ctr)
    _safe_send(ARB_ID, payload)

def _ticker_loop():
    # Sleep in short steps so we can react quickly to pause/unpause
    STEP = 0.25
    acc = 0.0
    while True:
        # If a broadcast window is active, hold here (no ticking, no sending)
        while _is_paused():
            time.sleep(0.05)
            acc = 0.0  # reset accumulated sleep so we start a fresh 15s after resume

        time.sleep(STEP)
        acc += STEP
        if acc < TICK_SECONDS:
            continue
        acc = 0.0

        st = get_state("rolling_crc") or {}
        ctr = (st.get("counter", 0) + 1) & 0xFF
        update_state("rolling_crc", {"counter": ctr})
        payload = _pack(ctr)
        _safe_send(ARB_ID, payload)

_ticker_thread: Optional[threading.Thread] = None

def start():
    initial = random.randint(0, 254)
    update_state("rolling_crc", {"counter": initial})
    _emit_current()

    global _ticker_thread
    if _ticker_thread is None or not _ticker_thread.is_alive():
        _ticker_thread = threading.Thread(target=_ticker_loop, name="crc_ticker", daemon=True)
        _ticker_thread.start()

# --------------- Ingress handler ----------------------------------
def handle(msg: can.Message) -> None:
    # While paused, ignore incoming attempts (no flag emission during broadcast)
    if _is_paused():
        return

    if msg.arbitration_id != ARB_ID:
        return
    if msg.dlc != 8 or msg.is_error_frame or msg.is_remote_frame:
        return

    data = bytes(msg.data)
    body, rx_crc = data[:7], data[7]
    if crc8_2f(body) != rx_crc:
        return  # bad CRC

    st = get_state("rolling_crc") or {}
    ctr = st.get("counter", 0)
    expected = (ctr + 1) & 0xFF
    if body[0] != expected:
        return

    # Correct next value received -> emit flag on 0x2A1 (but not during broadcast)
    flag_text = "DMI{R0ll1ng_crc_s0lv3d}"
    if chunk_and_send_flag:
        try:
            # Wait out any broadcast window before chunking, to avoid interleaving
            while _is_paused():
                time.sleep(0.05)
            chunk_and_send_flag(ARB_ID, flag_text)
        except Exception:
            _safe_send(ARB_ID, flag_text.encode("ascii", errors="ignore")[:8])
    else:
        _safe_send(ARB_ID, flag_text.encode("ascii", errors="ignore")[:8])
