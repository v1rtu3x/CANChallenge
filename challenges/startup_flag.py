# CANChallenge/challenges/startup_flag.py
import threading
import time
from utils.flags import chunk_and_send_flag

def send_startup_flag():
    """
    Sends the startup Easter egg flag once at simulator start.
    """
    flag = "DMI{th15_0n3_w45_ez_r1ght_?}"
    try:
        while True:
            chunk_and_send_flag(0x555, flag)
            time.sleep(15)
    except KeyboardInterrupt:
        print("Flag sender stopped by user.")
