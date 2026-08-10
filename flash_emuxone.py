#!/usr/bin/env python3
"""
EMUXONE.hex DFU Flash Helper
=============================
Watches for the Arduino Leonardo DFU bootloader COM port to appear,
then immediately fires avrdude to flash EMUXONE.hex.

INSTRUCTIONS:
  1. Plug Leonardo USB into PC
  2. Run this script
  3. When it says "WATCHING FOR BOOTLOADER..." — double-press reset on Leonardo
  4. Script detects the new port and flashes automatically
"""
import serial.tools.list_ports
import subprocess
import sys
import time

AVRDUDE   = r"C:\Program Files (x86)\GIMX\avrdude.exe"
AVRDUDE_CONF = r"C:\Program Files (x86)\GIMX\avrdude.conf"
FIRMWARE  = r"C:\Program Files (x86)\GIMX\firmware\EMUXONE.hex"

# Known ports BEFORE reset (to detect the new one)
KNOWN_BEFORE = {p.device for p in serial.tools.list_ports.comports()}

# Leonardo DFU bootloader VID:PID
LEONARDO_BOOT_VID_PID = {"2341:0036", "2341:8036", "2341:0037", "2341:8037",
                          "1B4F:9206", "1B4F:9207"}  # SparkFun variants too


def get_current_ports():
    return {p.device: p for p in serial.tools.list_ports.comports()}


def find_bootloader_port(before: set, timeout: int = 15):
    """Watch for a new COM port to appear — that's the bootloader."""
    print(f"\n  Watching for {timeout}s...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = get_current_ports()
        new_ports = set(current.keys()) - before
        if new_ports:
            port = list(new_ports)[0]
            info = current[port]
            print(f"\n  New port detected: {port} | {info.description} | {info.hwid}")
            return port
        time.sleep(0.2)
        print(".", end="", flush=True)
    return None


def flash(port: str) -> bool:
    """Run avrdude to flash EMUXONE.hex to Leonardo via avr109 (Caterina bootloader)."""
    cmd = [
        AVRDUDE,
        "-C", AVRDUDE_CONF,
        "-p", "atmega32u4",
        "-c", "avr109",          # Caterina / Leonardo bootloader protocol
        "-P", port,
        "-b", "57600",           # Caterina bootloader baud rate
        "-D",                    # Disable auto-erase (avr109 requirement)
        "-U", f"flash:w:{FIRMWARE}:i",
    ]
    print(f"\n  Running avrdude on {port}...")
    print(f"  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("  EMUXONE.hex DFU Flash Helper")
    print("=" * 60)
    print(f"\n  Firmware : {FIRMWARE}")
    print(f"  avrdude  : {AVRDUDE}")
    print(f"\n  Current ports (before reset): {sorted(KNOWN_BEFORE)}")
    print()
    print("  WAITING FOR BOOTLOADER...")
    print("  --> Double-press the RESET button on the Leonardo NOW <--")
    print("      (two quick presses in under 1 second)")
    print("      The LED will pulse/breathe when bootloader is active.")
    print()

    port = find_bootloader_port(KNOWN_BEFORE, timeout=30)

    if port is None:
        print("\n  TIMEOUT — no new port detected.")
        print("  Try again: double-press reset more quickly.")
        print("  If Leonardo still shows no new port, the DFU bootloader")
        print("  may need restoring first via Arduino IDE (burn bootloader).")
        sys.exit(1)

    print(f"\n  Bootloader port: {port}")
    print("  Starting flash in 1s...")
    time.sleep(1)

    success = flash(port)

    print()
    if success:
        print("  SUCCESS — EMUXONE.hex flashed to Leonardo!")
        print()
        print("  Next steps:")
        print("  1. Unplug Leonardo from PC")
        print("  2. Plug Leonardo USB into Xbox USB port")
        print("  3. Run GIMX:")
        print(r'     "C:\Program Files (x86)\GIMX\gimx.exe" --src 127.0.0.1:51914 -p COM8 --nograb --force-updates')
        print("  4. Run controller test:")
        print("     python Automation_V4_Agent/tests/controller_test.py --suite long_press")
    else:
        print("  FAILED — avrdude returned an error.")
        print("  Common causes:")
        print("  - Reset not double-pressed quickly enough (bootloader window expired)")
        print("  - Wrong COM port selected")
        print("  - Arduino IDE is open and holding the port — close it first")
        sys.exit(1)


if __name__ == "__main__":
    main()
