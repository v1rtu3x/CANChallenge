# CANChallenge/challenges/startup_flag.py
import time
from utils.flags import chunk_and_send_flag

# import dispatcher to observe the broadcast pause flag
try:
    import dispatcher
except Exception:
    dispatcher = None  # safe fallback if dispatcher is not importable

def _is_paused() -> bool:
    """Return True if the dispatcher/broadcast system is currently paused."""
    try:
        return bool(getattr(dispatcher, "DISPATCHER_PAUSED", False))
    except Exception:
        return False

def send_startup_flag():
    """
    Sends the startup Easter egg flag periodically, but will *not* send while
    dispatcher.DISPATCHER_PAUSED is True (i.e., during hex/ELF broadcast windows).
    """
    flag = "DMI{th15_0n3_w45_ez_r1ght_?}"
    try:
        while True:
            # If a broadcast window is active, wait until it finishes.
            # Poll quickly so we stop sending fast when a window opens.
            while _is_paused():
                time.sleep(0.05)

            # Safe to send now
            try:
                chunk_and_send_flag(0x555, flag)
            except Exception:
                # ignore send errors and continue
                pass

            # Sleep in small increments so we can react quickly if a broadcast starts.
            total_sleep = 15.0
            step = 0.25
            elapsed = 0.0
            while elapsed < total_sleep:
                if _is_paused():
                    break
                time.sleep(step)
                elapsed += step

            # loop around and check pause/send again
    except KeyboardInterrupt:
        print("Flag sender stopped by user.")
