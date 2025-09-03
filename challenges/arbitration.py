# challenges/arbitration.py
import time
import can
from state import get_state, update_state
from io_can import send_can_frame
from utils.flags import chunk_and_send_flag  # same helper you use for the startup flag

# --- Tunables / Spec constants ---
LOW_ID_MAX = 0x00F           # Track low IDs ≤ 0x00F
TRIGGER_RATE = 500           # ≥500 frames
TRIGGER_WINDOW_S = 1.0       # ...in a sliding 1s window
GRACE_WINDOW_S = 3.0         # open a 3s window
PROBE_ID = 0x014             # expect 0x014 with CAFE...
KICK_ID = 0x215              # then ≤2s expect 0x215 with BEEF...
KICK_DEADLINE_S = 2.0
FLAG_ID = 0x7F2

FLAG = "DMI{Arb_w1nd0w_p@ssed}"  # change to your desired flag text

def _prune(ts_list, now, span):
    cutoff = now - span
    return [t for t in ts_list if t >= cutoff]

def _has_prefix(data: bytes, prefix: bytes) -> bool:
    return len(data) >= len(prefix) and data[:len(prefix)] == prefix

def handle(msg: can.Message):
    """Arbitration-window challenge entrypoint."""
    st = get_state("arbitration")
    now = time.monotonic()

    # 1) Track low-ID frames for sliding 1s rate test
    if msg.arbitration_id <= LOW_ID_MAX:
        ts = st.get("timestamps", [])
        ts.append(now)
        ts = _prune(ts, now, TRIGGER_WINDOW_S)
        # Open (or extend) the 3s window if rate threshold is hit
        if len(ts) >= TRIGGER_RATE:
            st["window_until"] = max(st.get("window_until", 0.0), now + GRACE_WINDOW_S)
        st["timestamps"] = ts
        update_state("arbitration", st)
        return

    window_until = st.get("window_until", 0.0)

    # 2) If window expired, reset probe state
    if now > window_until and (st.get("probe_seen") or st.get("probe_time", 0)):
        st["probe_seen"] = False
        st["probe_time"] = 0.0
        update_state("arbitration", st)

    # 3) Probe: 0x014 with CAFE...
    if msg.arbitration_id == PROBE_ID and now <= window_until:
        data = bytes(msg.data or b"")
        if _has_prefix(data, b"\xCA\xFE"):
            st["probe_seen"] = True
            st["probe_time"] = now
            update_state("arbitration", st)
        return

    # 4) Kick: 0x215 with BEEF..., within 2s of probe, still inside grace window
    if msg.arbitration_id == KICK_ID and st.get("probe_seen"):
        data = bytes(msg.data or b"")
        probe_time = st.get("probe_time", 0.0)
        if _has_prefix(data, b"\xBE\xEF") and (now - probe_time) <= KICK_DEADLINE_S and now <= window_until:
            # Success → emit flag on 0x7F2
            try:
                chunk_and_send_flag(FLAG_ID, FLAG)
            except Exception:
                # If utils.flags isn't available, fall back to a single-frame marker
                send_can_frame(FLAG_ID, b"FLAG")
            # Reset window/probe state to avoid re-trigger spam
            st["window_until"] = 0.0
            st["probe_seen"] = False
            st["probe_time"] = 0.0
            update_state("arbitration", st)
        return
