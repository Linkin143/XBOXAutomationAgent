#!/usr/bin/env python3
"""
EMUXONE.hex Flash Helper v2
=============================
Uses gimx-loader.exe (the correct GIMX flashing tool) instead of avrdude directly.
gimx-loader handles the full EMUXONE flashing protocol including USB descriptor replacement.

Run: python flash_emuxone_v2.py
Then double-press reset on Leonardo when prompted.
"""
import serial.tools.list_ports
import subprocess
import sys
import time

GIMX_LOADER = r"C:\Program Files (x86)\GIMX\gimx-loader.exe"
FIRMWARE    = r"C:\Program Files (x86)\GIMX\firmware\EMUXONE.hex"

# Known VID:PIDs for Arduino Leonardo bootloader
BOOTLOADER_VIDS = {"2341", "1B4F", "16C0"}
BOOTLOADER_PIDS_2341 = {"0036", "8036"}

def get_ports():
    return {p.device: p for p in serial.tools.list_ports.comports()}

def find_new_port(before: set, timeout: int = 20):
    print(f"  Watching for new port ({timeout}s)...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = get_ports()
        new = set(current.keys()) - before
        if new:
            port = list(new)[0]
            info = current[port]
            print(f"\n  Detected: {port} | {info.description} | {info.hwid}")
            return port
        time.sleep(0.2)
        print(".", end="", flush=True)
    return None

def main():
    print("=" * 60)
    print("  EMUXONE.hex Flash Helper v2 — using gimx-loader.exe")
    print("=" * 60)
    print(f"\n  Loader   : {GIMX_LOADER}")
    print(f"  Firmware : {FIRMWARE}")

    before = set(get_ports().keys())
    print(f"\n  Current ports: {sorted(before)}")
    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  ACTION: Double-press the RESET button on Arduino Leonardo")
    print("          (two quick presses within 0.5 seconds)")
    print("          LED will pulse/breathe — bootloader active for 8s")
    print("  ─────────────────────────────────────────────────────────")
    print()

    port = find_new_port(before, timeout=30)

    if port is None:
        print("\n  TIMEOUT — no new port appeared.")
        print("  Try double-pressing reset faster (within 0.5s).")
        sys.exit(1)

    print(f"\n  Using port: {port}")
    time.sleep(0.5)  # Let bootloader settle

    # Use gimx-loader.exe — this is the correct tool for EMUXONE
    # It handles the complete firmware replacement including USB descriptors
    cmd = [GIMX_LOADER, "--port", port, "--file", FIRMWARE]
    print(f"\n  Running: {' '.join(cmd)}\n")
    print("  " + "-" * 56)

    result = subprocess.run(cmd)

    print("  " + "-" * 56)

    if result.returncode == 0:
        print("\n  SUCCESS — EMUXONE.hex flashed via gimx-loader!")
        print()
        print("  Verification — unplug Leonardo from PC, wait 5s,")
        print("  plug back into PC and check Device Manager.")
        print("  Should show:  GIMX adapter  (VID_F055 PID_0004)")
        print("  NOT:          Arduino Leonardo  (VID_2341 PID_8036)")
        print()
        print("  Then:")
        print("  1. Unplug Leonardo from PC")
        print("  2. Plug Leonardo USB into Xbox")
        print("  3. Xbox should show controller icon immediately")
        print("  4. Run GIMX:")
        print(r'     "C:\Program Files (x86)\GIMX\gimx.exe" --src 127.0.0.1:51914 -p COM8 --nograb --force-updates')
    else:
        print(f"\n  FAILED — gimx-loader returned code {result.returncode}")
        print()
        print("  Try:")
        print("  1. Run this script as Administrator")
        print("  2. Double-press reset more quickly")
        print("  3. Make sure no other program has the COM port open")

if __name__ == "__main__":
    main()
