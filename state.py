# CANChallenge/state.py
import time

# Global state dictionary
state = {}


def init_state():
    """
    Initialize/reset state for all challenges.
    Called once at simulator startup.
    """
    global state
    state = {
        "rolling_crc": {
            "last_counter": None,
        },
        "arbitration": {
            "timestamps": [],   # recent low-ID frame times
            "window_until": 0,  # grace window end time
            "probe_seen": False,
            "probe_time": 0,
        },
        "timing_replay": {
            "expected_index": 0,
            "last_ts": None,
        },
        "majority_vote": {
            "wheel_logs": {
                0x120: [],
                0x121: [],
                0x122: [],
            },
            "lock_state": 0,
        },
        "lfsr_token": {
            "last_counter": None,
        },
        "elf_broadcast": {
            "last_broadcast": 0,
        },
    }
    print("[STATE] Initialized all challenge states")


def get_state(challenge):
    """Retrieve state dictionary for a specific challenge."""
    return state.get(challenge, {})


def update_state(challenge, new_values: dict):
    """Update state for a specific challenge."""
    if challenge not in state:
        state[challenge] = {}
    state[challenge].update(new_values)
