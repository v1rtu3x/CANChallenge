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

### Timing-Sensitive Replay — ID `0x440`

Send five exact 8-byte payloads **in order** with inter-frame gaps in **0.080–0.120 s** to receive a flag on `0x7F4`.

### Rolling CRC Counter — ID `0x2A1`

Observe the rolling counter, compute the next counter and CRC-8 (poly `0x2F`, init `0xFF`, final XOR), then send a valid frame to trigger a flag on `0x2A1`.

### Majority / Consensus Spoof — IDs `0x120/0x121/0x122` (+ `0x210`, probe `0x2B0`)

Force ≥2 simulated wheel ECUs to report `0 km/h` for ≥1 s while `0x210` reports `lock=1`, then `cansend vcan0 2B0#55` → flag on `0x7F3`.

### Arbitration Window Exploit — low IDs

Flood low IDs (≤ `0x00F`) to open a maintenance window, then send a probe (
