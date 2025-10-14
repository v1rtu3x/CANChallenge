# CANChallenge

CANChallenge is a modular CAN-bus simulator and CTF platform that emulates multiple ECUs (challenges) entirely in software. It runs on Linux SocketCAN (vcan0) and requires no physical hardware — ideal for training, workshops, and small CTF events.

---

## Quick summary

Each challenge behaves like a realistic ECU function: counters, CRCs, timing windows, spoof-detection and other behaviours are implemented and must be discovered and exploited. Successful interactions emit short flags on dedicated service IDs.

The framework is lightweight and extensible: every challenge is a small handler under `challenges/` and wired through the central `dispatcher`.

---

## Features

* Pure Python (runs on Linux + SocketCAN).
* Modular: one challenge per file in `challenges/`.
* Background CAN noise generator for realism.
* Hex/ELF broadcaster that temporarily pauses normal traffic to stream payloads.
* Several included puzzles: timing-sensitive, CRC-token, majority-spoof and arbitration-window challenges.
* Terminal-friendly: designed to be used with `candump`, `cansend`, and small Python helpers.

---

## Requirements

* Linux with SocketCAN and the `vcan` kernel module.
* Python 3.8+ (3.10+ recommended).

Recommended tools (not required to run the simulator, but useful for interacting):

* `can-utils` (provides `candump`, `cansend`, `cangen`)
* `python-can`

---

## Quick start

```bash
# 1) Clone
git clone https://github.com/<youruser>/CANChallenge.git
cd CANChallenge

# 2) (optional) Create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3) Install runtime dependencies
pip install python-can

# 4) Create and bring up a virtual CAN interface (vcan0)
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# 5) Run the simulator
python3 main.py
```

You should see log lines from the dispatcher and each enabled challenge.

---

## Repository layout

```
CANChallenge/
├─ main.py                # Entrypoint
├─ dispatcher.py          # Routes incoming CAN messages to challenge handlers
├─ io_can.py              # CAN I/O helpers
├─ state.py               # Shared state store
├─ constants.py           # Global IDs and settings
├─ challenges/            # Challenge handlers (one file = one challenge)
│  ├─ timing_replay.py
│  ├─ rolling_crc.py
│  ├─ majority_spoof.py
│  ├─ arbitration.py
│  ├─ hex_broadcast.py
│  └─ startup_flag.py
└─ resources/
   └─ payload.hex         # Example payload streamed by hex_broadcast
```

---

## Implemented challenges (short summaries)

### Startup Flag - “Morning Broadcast”

A quiet diagnostic beacon comes alive in the factory’s overnight maintenance loop. When conditions are right it blurts out a mysterious startup message — but when the heavy broadcast system spins up, the beacon goes silent. Your mission: catch the message in the act.

**Flag Arbitration ID:** `0x555`

### Majority Spoof — “Three-Wheel Consensus”

Three redundant wheel sensors decide when the vehicle is truly at rest. If enough of them agree and the lock is engaged, a hidden rescue routine springs to life. Your job is to trick the system into that state and trigger the response.

**IDs:** Wheels `0x120`, `0x121`, `0x122`; Lock `0x210`; Poke `0x2B0`; Flag `0x7F3`

### Timing Replay — “The Ghost Injector”

In the shadows of the test bay, an **ECU** and a **ghost module** exchange a secret handshake — one that only completes when a **precise sequence of CAN frames** is delivered at the **perfect tempo**.

Your task is to **recreate this ritual**: transmit the required frame sequence in rhythm, and the rig will respond.

- **Arbitration ID (output):** `0x220`
- **Success flag (input):** `0x440`emitted on `0x7F4`

### Arbitration Window — “Flood the Bus, Swing the Gate”

You’re planning a coordinated assault on the bus. By hammering low-priority IDs fast enough you can force open a temporary grace window, then slip in a probe and a follow-up “kick” with the right signatures. Do it correctly and the gate unlocks.

**Key IDs:** Low IDs ≤`0x00F` (trigger), probe `0x014`, kick `0x215`; Flag `0x7F2`

### Rolling CRC — “The Clockwork Odometer”

A quiet node ticks every 15 seconds, publishing a counter plus a checksum. If you can anticipate its next step and answer with a valid frame, it will treat you as a trusted companion and reveal its secret.

**Arbitration ID (challenge &## Developer notes

- `dispatcher.py` is the central router — it prints every message it routes and calls the per-challenge `handle(msg)` function.
- `hex_broadcast.py` temporarily sets a global pause (`dispatcher.pause_dispatcher()`), kills any `cangen` processes, streams the `payload.hex` file in chunks, then resumes normal dispatching. Challenges check `dispatcher.DISPATCHER_PAUSED` and typically avoid sending flags during broadcast windows.
- Challenges may implement a `start()` function (for periodic behaviour) and are usually launched by `main.py`.
- Persistent per-challenge state is stored via `state.py` to allow multi-step interactions and retries.

 ### Hex Broadcast — “The Firmware Dump”

At intervals, a maintenance routine opens a window and streams a hidden firmware blob over the bus, padded by long runs of zeros at the start and end. Capture the right portion and you’ll recover the embedded payload.

**Arbitration ID:** `0x600`.

---

## Troubleshooting

- If the simulator won't start, ensure `vcan0` exists and `python-can` is installed.
- If flags don't appear, check that the corresponding challenge is not paused by the hex broadcaster (watch the logs for "paused" / "resumed").
- Use `candump vcan0` to verify traffic and timestamps; `cansend` to inject frames. flag):** `0x2A1`. 


## Developer notes

- `dispatcher.py` is the central router — it prints every message it routes and calls the per-challenge `handle(msg)` function.
- `hex_broadcast.py` temporarily sets a global pause (`dispatcher.pause_dispatcher()`), kills any `cangen` processes, streams the `payload.hex` file in chunks, then resumes normal dispatching. Challenges check `dispatcher.DISPATCHER_PAUSED` and typically avoid sending flags during broadcast windows.
- Challenges may implement a `start()` function (for periodic behaviour) and are usually launched by `main.py`.
- Persistent per-challenge state is stored via `state.py` to allow multi-step interactions and retries.

---

## Troubleshooting

- If the simulator won't start, ensure `vcan0` exists and `python-can` is installed.
- If flags don't appear, check that the corresponding challenge is not paused by the hex broadcaster (watch the logs for "paused" / "resumed").
- Use `candump vcan0` to verify traffic and timestamps; `cansend` to inject frames.
