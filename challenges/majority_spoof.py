# challenges/majority_spoof.py
from __future__ import annotations
import time, can
from typing import Dict, Optional
from io_can import send_can_frame
from state import update_state
try:
    from utils.flags import chunk_and_send_flag
except Exception:
    chunk_and_send_flag = None

WHEEL_IDS = (0x120, 0x121, 0x122)
LOCK_ID   = 0x210
POKE_ID   = 0x2B0
FLAG_ID   = 0x7F3
ZERO_REQUIRED_S = 1.0
STATE_KEY = "majority_spoof"

_last_zero_start: Dict[int, Optional[float]] = {wid: None for wid in WHEEL_IDS}
_last_seen: Dict[int, Optional[float]]       = {wid: None for wid in WHEEL_IDS}
_lock_state: int = 0  # current lock bit (0/1)

def _save_state():
    update_state(STATE_KEY, {
        "last_zero_start": {hex(k): v for k, v in _last_zero_start.items()},
        "last_seen": {hex(k): v for k, v in _last_seen.items()},
        "lock_state": _lock_state,
    })

def _emit_flag():
    flag_text = "DMI{1_l0v3_d3m0cr4cy}"
    if chunk_and_send_flag:
        try:
            chunk_and_send_flag(FLAG_ID, flag_text); return
        except Exception:
            pass
    send_can_frame(FLAG_ID, flag_text.encode("ascii")[:8])

def _count_zeroed(now: float) -> int:
    return sum(
        1 for wid in WHEEL_IDS
        if (_last_zero_start[wid] is not None) and (now - _last_zero_start[wid] >= ZERO_REQUIRED_S)
    )

def handle(msg: can.Message) -> None:
    global _lock_state
    now = time.monotonic()
    arb = msg.arbitration_id

    if arb in WHEEL_IDS:
        _last_seen[arb] = now
        if msg.dlc >= 1:
            if int(msg.data[0]) == 0:
                if _last_zero_start[arb] is None:
                    _last_zero_start[arb] = now
            else:
                if _last_zero_start[arb] is not None:
                    _last_zero_start[arb] = None
        _save_state(); return

    if arb == LOCK_ID and msg.dlc >= 1:
        _lock_state = 1 if int(msg.data[0]) == 0x01 else 0
        _save_state(); return

    if arb == POKE_ID and msg.dlc >= 1 and int(msg.data[0]) == 0x55:
        zeros_ok = (_count_zeroed(now) >= 2)
        lock_ok  = (_lock_state == 1)
        if zeros_ok and lock_ok:
            _emit_flag()
        return
