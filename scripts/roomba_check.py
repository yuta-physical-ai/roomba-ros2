#!/usr/bin/env python3
"""Roomba 600 OI connection check (stdlib only, no pyserial needed).

Usage: python3 roomba_check.py [/dev/ttyACM0] [--beep]
Sends START (passive mode), reads sensor group 3 (battery), optionally beeps.
"""
import os, sys, termios, time, struct, select

port = next((a for a in sys.argv[1:] if a.startswith("/dev/")), "/dev/ttyACM0")
beep = "--beep" in sys.argv

fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
attrs = termios.tcgetattr(fd)
attrs[0] = 0                                   # iflag: raw
attrs[1] = 0                                   # oflag: raw
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[3] = 0                                   # lflag: raw
attrs[4] = attrs[5] = termios.B115200
attrs[6][termios.VMIN] = 0
attrs[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, attrs)
termios.tcflush(fd, termios.TCIOFLUSH)

def read_n(n, timeout=1.0):
    buf, end = b"", time.time() + timeout
    while len(buf) < n and time.time() < end:
        r, _, _ = select.select([fd], [], [], end - time.time())
        if r:
            buf += os.read(fd, n - len(buf))
    return buf

os.write(fd, bytes([128]))          # START -> passive mode
time.sleep(0.2)
termios.tcflush(fd, termios.TCIFLUSH)   # discard any boot text

os.write(fd, bytes([142, 3]))       # SENSORS, packet group 3 (10 bytes)
data = read_n(10)
print(f"port={port}  received {len(data)}/10 bytes: {data.hex(' ')}")

ok = len(data) == 10
if ok:
    chg, volt, cur, temp, charge, cap = struct.unpack(">BHhbHH", data)
    states = ["Not charging", "Reconditioning", "Full charging", "Trickle", "Waiting", "Fault"]
    print(f"  charging state : {states[chg] if chg < 6 else chg}")
    print(f"  voltage        : {volt/1000:.2f} V")
    print(f"  current        : {cur} mA")
    print(f"  temperature    : {temp} C")
    print(f"  charge/capacity: {charge}/{cap} mAh"
          + (f" ({charge*100//cap}%)" if cap else ""))
    if not (10000 < volt < 20000):
        print("  !! voltage out of range -> probably garbage (check TX/RX, GND, baud)")
        ok = False

if ok and beep:
    os.write(fd, bytes([131]))                          # SAFE mode
    time.sleep(0.1)
    os.write(fd, bytes([140, 0, 2, 72, 16, 76, 16]))    # song 0: C5, E5
    os.write(fd, bytes([141, 0]))                       # play
    time.sleep(0.8)
    os.write(fd, bytes([128]))                          # back to passive

os.write(fd, bytes([173]))          # STOP -> OI off
os.close(fd)

print("RESULT:", "OK - Roomba OI responded" if ok else "NG - no valid response")
sys.exit(0 if ok else 1)
