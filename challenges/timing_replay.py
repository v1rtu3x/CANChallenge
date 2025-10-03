# challenges/timing_replay.py

import time
import can
from io_can import send_can_frame
from state import get_state, update_state

try:
    from utils.flags import chunk_and_send_flag
except Exception:  # pragma: no cover
    chunk_and_send_flag = None

IN_ID   = 0x440
FLAG_ID = 0x7F4

# Strict window (inclusive). Adjust if your shell is jittery.
T_MIN = 0.080
T_MAX = 0.120

SEQ = [
    bytes.fromhex("1122334455667788"),
    bytes.fromhex("99AABBCCDDEEF012"),
    bytes.fromhex("21436587090A0B0C"),
    bytes.fromhex("DEADBEEF00000001"),
    bytes.fromhex("FEEDFACE12345678"),
]

STATE_KEY = "timing_replay"
# State fields:
#   idx: next expected index in SEQ (0 = waiting for first)
#   last_ts: timestamp of last ACCEPTED frame (float)
#   use_msg_ts: True -> use msg.timestamp, False -> use time.monotonic()

def _get_state():
    st = get_state(STATE_KEY) or {}
    return int(st.get("idx", 0)), st.get("last_ts", None), st.get("use_msg_ts", None)

def _set_state(idx, last_ts, use_msg_ts):
    update_state(STATE_KEY, {"idx": idx, "last_ts": last_ts, "use_msg_ts": use_msg_ts})

def _reset():
    print("[timing_replay] RESET")
    _set_state(0, None, None)

def _success():
    print("[timing_replay] SUCCESS -> sending flag on 0x7F4")
    flag_text = "DMI{t1m1ng_replay_ok}"
    if chunk_and_send_flag:
        try:
            chunk_and_send_flag(FLAG_ID, flag_text)
        except Exception:
            send_can_frame(FLAG_ID, flag_text.encode("ascii", errors="ignore")[:8])
    else:
        send_can_frame(FLAG_ID, flag_text.encode("ascii", errors="ignore")[:8])
    _reset()

def _now_from_msg(msg: can.Message, use_msg_ts: bool | None):
    has_ts = hasattr(msg, "timestamp") and isinstance(msg.timestamp, (int, float))
    if use_msg_ts is None:
        # Decide on first accept
        if has_ts:
            return float(msg.timestamp), True
        return time.monotonic(), False
    if use_msg_ts and has_ts:
        return float(msg.timestamp), True
    return time.monotonic(), False

def handle(msg: can.Message) -> None:
    # Only consider data frames with DLC=8 on IN_ID
    if msg.arbitration_id != IN_ID or msg.is_error_frame or msg.is_remote_frame:
        return
    if msg.dlc != 8:
        return

    idx, last_ts, use_msg_ts = _get_state()
    now, use_msg_ts = _now_from_msg(msg, use_msg_ts)
    data = bytes(msg.data)

    # DEBUG: show every 0x440 we see (comment out if too chatty)
    # print(f"[timing_replay] seen idx={idx} data={data.hex()}")

    if idx == 0:
        # Waiting for the first payload only
        if data == SEQ[0]:
            _set_state(1, now, use_msg_ts)
            print("[timing_replay] accepted #1, waiting for #2")
        # Ignore everything else while idle
        return

    # Only the expected payload or the first payload can affect the state
    expected = SEQ[idx]

    if data == expected:
        if last_ts is None:
            # Shouldn't happen after idx>0, but guard anyway
            _set_state(idx, now, use_msg_ts)
            return
        dt = now - float(last_ts)
        if T_MIN <= dt <= T_MAX:
            idx += 1
            _set_state(idx, now, use_msg_ts)
            print(f"[timing_replay] accepted #{idx} (dt={dt:.6f}s)")
            if idx >= len(SEQ):
                _success()
            return
        else:
            print(f"[timing_replay] wrong timing for expected #{idx+1}: dt={dt:.6f}s (need {T_MIN}-{T_MAX})")
            # Don’t reset due to noise; allow immediate restart if first payload arrives
            return

    if data == SEQ[0]:
        # Convenience restart from the first payload
        _set_state(1, now, use_msg_ts)
        print("[timing_replay] restart: accepted #1, waiting for #2")
        return

    # Ignore arbitrary noise on 0x440
    return
