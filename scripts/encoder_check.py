#!/usr/bin/env python3
"""Roomba 600 wheel encoder check (stdlib only, no pyserial needed).

Usage: python3 encoder_check.py [/dev/roomba] [--seconds N] [--drive [--mm N]]
Default: passive mode, prints encoder counts while you turn the wheels by hand.
--drive: safe mode, drives both wheels forward at 50 mm/s for --mm N mm
         (default 100) and compares the counts. Keep 2x that distance clear.
"""
import os, sys, termios, time, struct, select

COUNTS_PER_REV = 508.8
WHEEL_DIAMETER_MM = 72.0
MM_PER_COUNT = WHEEL_DIAMETER_MM * 3.14159265 / COUNTS_PER_REV

args = sys.argv[1:]
port = next((a for a in args if a.startswith("/dev/")), "/dev/roomba")
seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else 15.0
drive = "--drive" in args
drive_mm = float(args[args.index("--mm") + 1]) if "--mm" in args else 100.0

fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
attrs = termios.tcgetattr(fd)
attrs[0] = attrs[1] = attrs[3] = 0
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[4] = attrs[5] = termios.B115200
attrs[6][termios.VMIN] = 0
attrs[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, attrs)

def read_n(n, timeout=0.5):
    buf, end = b"", time.time() + timeout
    while len(buf) < n and time.time() < end:
        r, _, _ = select.select([fd], [], [], end - time.time())
        if r:
            buf += os.read(fd, n - len(buf))
    return buf

def read_sensors():
    """Query packets 7 (bumps/wheel drops), 43 (left enc), 44 (right enc)."""
    termios.tcflush(fd, termios.TCIFLUSH)
    os.write(fd, bytes([149, 3, 7, 43, 44]))
    data = read_n(5)
    if len(data) != 5:
        return None
    bumps, left, right = struct.unpack(">BHH", data)
    return bumps, left, right

def delta(now, start):
    """Encoder counts are unsigned 16-bit and wrap around."""
    d = (now - start) & 0xFFFF
    return d - 0x10000 if d >= 0x8000 else d

os.write(fd, bytes([128]))               # START -> passive mode
time.sleep(0.2)

first = read_sensors()
if first is None:
    print("NG - no response from Roomba (check power / wiring)")
    sys.exit(1)
_, left0, right0 = first
print(f"start counts: left={left0} right={right0}")

ok = True
try:
    if drive:
        os.write(fd, bytes([131]))                        # SAFE mode
        time.sleep(0.1)
        os.write(fd, bytes([145]) + struct.pack(">hh", 50, 50))  # drive direct: R, L mm/s
        time.sleep(drive_mm / 50.0)
        os.write(fd, bytes([145, 0, 0, 0, 0]))            # stop
        time.sleep(0.3)
        s = read_sensors()
        if s is None:
            raise RuntimeError("no response after drive")
        bumps, left, right = s
        dl, dr = delta(left, left0), delta(right, right0)
        print(f"after drive: left {dl:+d} counts ({dl*MM_PER_COUNT:+.0f} mm), "
              f"right {dr:+d} counts ({dr*MM_PER_COUNT:+.0f} mm)  [expected ~+{drive_mm:.0f} mm]")
        if bumps & 0x0C:
            print("  !! wheel drop detected - Safe mode refuses to drive when lifted")
        for name, d in (("left", dl), ("right", dr)):
            if d <= 0:
                print(f"  !! {name} encoder did not count forward")
                ok = False
        if ok and abs(dl - dr) > 0.2 * max(dl, dr):
            print("  !! left/right differ by more than 20% - check wheel or encoder")
            ok = False
    else:
        print(f"Turn each wheel by hand for {seconds:.0f} s (Ctrl+C to stop early)...")
        seen = {"left": False, "right": False}
        end = time.time() + seconds
        while time.time() < end:
            s = read_sensors()
            if s:
                _, left, right = s
                dl, dr = delta(left, left0), delta(right, right0)
                seen["left"] |= dl != 0
                seen["right"] |= dr != 0
                print(f"\r  left {dl:+6d} ({dl*MM_PER_COUNT:+7.0f} mm)   "
                      f"right {dr:+6d} ({dr*MM_PER_COUNT:+7.0f} mm)", end="", flush=True)
            time.sleep(0.1)
        print()
        for name, moved in seen.items():
            print(f"  {name} encoder: {'counting' if moved else 'NO CHANGE'}")
        ok = all(seen.values())
except KeyboardInterrupt:
    print()
finally:
    os.write(fd, bytes([145, 0, 0, 0, 0]))   # make sure wheels are stopped
    os.write(fd, bytes([128]))               # back to passive
    os.write(fd, bytes([173]))               # STOP -> OI off
    os.close(fd)

print("RESULT:", "OK" if ok else "NG")
sys.exit(0 if ok else 1)
