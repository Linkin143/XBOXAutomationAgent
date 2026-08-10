#!/usr/bin/env python3
"""
EMUXONE Hardware Diagnostic
============================
Talks directly to the Arduino Leonardo (EMUXONE firmware) over COM8
and reports what the firmware says about its USB connection status.

Run: python diagnose_emuxone.py
"""
import serial
import time
import sys

COM_PORT  = "COM8"
BAUD_RATE = 500000   # GIMX initial baud rate for EMUXONE

print("=" * 60)
print("  EMUXONE Hardware Diagnostic")
print("=" * 60)
print(f"\n  Opening {COM_PORT} at {BAUD_RATE} baud...")

try:
    s = serial.Serial(
        port=COM_PORT,
        baudrate=BAUD_RATE,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=2,
    )
    print(f"  {COM_PORT} opened OK")
except Exception as e:
    print(f"  FAILED to open {COM_PORT}: {e}")
    sys.exit(1)

time.sleep(0.5)

# GIMX sends a 'get type' packet to EMUXONE: 0x00 0x00
print("\n  Sending GIMX 'get adapter type' probe (0x00 0x00)...")
s.write(bytes([0x00, 0x00]))
s.flush()
time.sleep(0.5)

response = s.read(s.in_waiting or 16)
print(f"  Response ({len(response)} bytes): {response.hex() if response else 'NONE'}")

if response:
    print(f"  Raw bytes: {list(response)}")
    if len(response) >= 2:
        adapter_type = response[0]
        status_byte  = response[1] if len(response) > 1 else 0
        print(f"\n  Adapter type byte : 0x{adapter_type:02X}")
        print(f"  Status byte       : 0x{status_byte:02X}")

        type_map = {
            0x01: "EMU360  (Xbox 360)",
            0x02: "EMUPS3  (PlayStation 3)",
            0x03: "EMUJOYSTICK",
            0x04: "EMUXONE (Xbox One) ✅",
            0x05: "EMUPS4  (PlayStation 4)",
            0x06: "EMUDF",
        }
        print(f"  Adapter type name : {type_map.get(adapter_type, f'Unknown (0x{adapter_type:02X})')}")

        # Status byte 0x06 means controller enumerated on USB
        # Status byte 0x00 means USB not connected / not enumerated
        if status_byte == 0x06:
            print("\n  USB STATUS: Xbox detected Leonardo as a controller ✅")
        elif status_byte == 0x00:
            print("\n  USB STATUS: No USB host detected — Leonardo not connected to Xbox ❌")
            print("  → Plug Leonardo USB into Xbox USB port and retry")
        else:
            print(f"\n  USB STATUS: Unexpected status 0x{status_byte:02X}")
else:
    print("\n  No response from Leonardo on COM8")
    print("  Possible causes:")
    print("  1. EMUXONE not flashed correctly — try reflashing with flash_emuxone.py")
    print("  2. Jumper wires TX/RX not correctly crossed")
    print("  3. FTDI adapter not powered / not connected to Leonardo pins")

# Try bumping baud to 2Mbps (what GIMX uses after handshake)
print("\n  Attempting baud rate negotiation to 2000000...")
s.baudrate = 2000000
time.sleep(0.2)
s.write(bytes([0x00, 0x00]))
s.flush()
time.sleep(0.5)
resp2 = s.read(s.in_waiting or 16)
print(f"  Response at 2Mbps ({len(resp2)} bytes): {resp2.hex() if resp2 else 'NONE'}")

s.close()
print(f"\n  {COM_PORT} closed.")
print("\n  Diagnostic complete.")
