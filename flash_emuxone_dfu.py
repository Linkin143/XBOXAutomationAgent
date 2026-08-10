#!/usr/bin/env python3
"""
EMUXONE.hex DFU Flash — correct method using avrdude flip2 programmer.

flip2 = Atmel FLIP USB DFU protocol — writes FULL firmware including USB
descriptor, so Leonardo becomes VID_F055 (GIMX adapter) not VID_2341 (Arduino).

Run as Administrator:
  python flash_emuxone_dfu.py

Then put Leonardo into HARDWARE DFU mode:
  - Plug Leonardo into PC
  - Short RESET pin to GND for 1 second (use a jumper wire)
  - Device Manager should show "ATmega32U4" under "Other devices" (NO COM port)
  - Script detects it and flashes automatically
"""
import subprocess
import sys
import time
import ctypes

AVRDUDE      = r"C:\Program Files (x86)\GIMX\avrdude.exe"
AVRDUDE_CONF = r"C:\Program Files (x86)\GIMX\avrdude.conf"
FIRMWARE     = r"C:\Program Files (x86)\GIMX\firmware\EMUXONE.hex"


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def wait_for_dfu(timeout: int = 30) -> bool:
    """Poll until avrdude can detect the ATmega32U4 in DFU mode."""
    import winreg
    print(f"\n  Watching for ATmega32U4 DFU device ({timeout}s)...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Quick probe: run avrdude with flip2, if it responds DFU is active
        probe = subprocess.run(
            [AVRDUDE, "-C", AVRDUDE_CONF, "-p", "atmega32u4",
             "-c", "flip2", "-n"],   # -n = don't write anything, just connect
            capture_output=True, timeout=5
        )
        output = probe.stdout.decode(errors="replace") + probe.stderr.decode(errors="replace")
        if "atmega32u4" in output.lower() or "initialization" not in output.lower():
            if probe.returncode == 0 or "reading" in output.lower():
                print(" DETECTED!")
                return True
        time.sleep(1)
        print(".", end="", flush=True)
    print(" TIMEOUT")
    return False


def flash() -> bool:
    """Flash EMUXONE.hex using avrdude flip2 (Atmel FLIP DFU protocol)."""
    cmd = [
        AVRDUDE,
        "-C", AVRDUDE_CONF,
        "-p", "atmega32u4",
        "-c", "flip2",          # Atmel FLIP USB DFU — writes full image
        "-U", f"flash:w:{FIRMWARE}:i",
    ]
    print(f"\n  Running avrdude flip2:")
    print(f"  {' '.join(cmd)}\n")
    print("  " + "-" * 56)
    result = subprocess.run(cmd)
    print("  " + "-" * 56)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("  EMUXONE.hex DFU Flash (flip2 — full firmware replacement)")
    print("=" * 60)
    print(f"\n  Firmware     : {FIRMWARE}")
    print(f"  avrdude      : {AVRDUDE}")
    print(f"  Programmer   : flip2 (Atmel FLIP USB DFU)")
    print(f"  Running as Admin: {is_admin()}")

    if not is_admin():
        print("\n  WARNING: Not running as Administrator.")
        print("  USB DFU access requires Admin. Please re-run as Administrator.")
        print("  Right-click Command Prompt → Run as Administrator")
        print("  Then: python flash_emuxone_dfu.py")
        sys.exit(1)

    print()
    print("  ─────────────────────────────────────────────────────────")
    print("  STEP 1: Plug Leonardo USB into PC (if not already)")
    print()
    print("  STEP 2: Put Leonardo into HARDWARE DFU mode:")
    print("    Method A — Jumper wire:")
    print("      Touch a wire between GND pin and RESET pin for 1 second")
    print("      (while Leonardo is powered via USB)")
    print()
    print("    Method B — Short circuit on ICSP header:")
    print("      Short the RST and GND pins on the ICSP 6-pin header")
    print()
    print("    SUCCESS sign: Device Manager shows 'ATmega32U4' under")
    print("    'Other devices' or 'Universal Serial Bus devices'")
    print("    (NO COM port number — that's the wrong mode)")
    print()
    print("    WRONG mode: 'Arduino Leonardo bootloader (COMxx)' = double-reset")
    print("    RIGHT mode: 'ATmega32U4' with no COM port = hardware DFU")
    print("  ─────────────────────────────────────────────────────────")
    print()
    input("  Press ENTER when Leonardo is in hardware DFU mode (ATmega32U4 visible)...")

    print("\n  Attempting to flash via flip2 DFU...")
    success = flash()

    print()
    if success:
        print("  SUCCESS — EMUXONE.hex flashed correctly!")
        print()
        print("  VERIFY: Unplug Leonardo from PC, wait 5s, plug back in.")
        print("  Device Manager should show:")
        print("    'GIMX adapter'  with NO COM port number")
        print("    VID_F055 PID_0004")
        print()
        print("  Then plug Leonardo into Xbox USB — Xbox should show")
        print("  a controller icon immediately.")
        print()
        print("  Then run GIMX (as Admin):")
        print(r'  "C:\Program Files (x86)\GIMX\gimx.exe" --src 127.0.0.1:51914 -p COM8 --nograb --force-updates')
        print()
        print("  Then run the controller test:")
        print("  python Automation_V4_Agent/tests/controller_test.py --suite long_press")
    else:
        print("  FAILED — avrdude could not connect via flip2.")
        print()
        print("  Possible causes:")
        print("  1. Leonardo not in hardware DFU mode — try the jumper wire method again")
        print("  2. UsbDk driver not working — it was installed but may need a reboot")
        print("  3. Try rebooting PC then run this script again as Admin")
        print()
        print("  Alternative: Use Atmel FLIP GUI application:")
        print("  Download: https://www.microchip.com/developmenttools/ProductDetails/flip")
        print("  Select ATmega32U4, connect via USB, load EMUXONE.hex, click Run")
        sys.exit(1)


if __name__ == "__main__":
    main()
