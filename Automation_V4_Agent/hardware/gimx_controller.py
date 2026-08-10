"""
GIMX Controller — Automation V4 Agent
======================================
Pure Python replacement for eDAT_ControllerV3_Script.ps1

Communicates with GIMX.exe via UDP (GIMX Network API):
  https://gimx.fr/wiki/index.php?title=Network_API

Physical path:
  Python → UDP socket → GIMX.exe → USB (XInput emulation) → Xbox Console
"""

import socket
import struct
import time
import subprocess
import logging
from enum import IntEnum
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Xbox One Pad Button / Axis Index Map
# Source: eDAT_ControllerV3_Script.ps1
# ─────────────────────────────────────────────
class XboxButton(IntEnum):
    LEFT_STICK_X  = 0
    LEFT_STICK_Y  = 1
    RIGHT_STICK_X = 2
    RIGHT_STICK_Y = 3
    VIEW          = 128   # Select / Back
    MENU          = 129   # Start / Menu
    GUIDE         = 130   # Xbox button
    UP            = 131   # D-pad Up
    RIGHT         = 132   # D-pad Right
    DOWN          = 133   # D-pad Down
    LEFT          = 134   # D-pad Left
    Y             = 135
    B             = 136
    A             = 137
    X             = 138
    LB            = 139
    RB            = 140
    LT            = 141   # Left Trigger (axis)
    RT            = 142   # Right Trigger (axis)
    LS            = 143   # Left Stick click
    RS            = 144   # Right Stick click


class ButtonValue(IntEnum):
    PRESSED            = 255
    RELEASED           = 0
    TRIGGER_FULL_PRESS = 1023
    STICK_FULL_RIGHT   = 32767
    STICK_FULL_DOWN    = 32767
    STICK_FULL_LEFT    = -32767
    STICK_FULL_UP      = -32767


@dataclass
class GimxConfig:
    host: str = "127.0.0.1"
    port: int = 51914
    com_port: str = "COM3"
    config_file: str = "XOnePadUsb.xml"
    short_press_ms: int = 110
    long_press_ms: int = 1500
    cooldown_ms: int = 220
    post_press_delay_ms: int = 1000


class GimxController:
    """
    Sends Xbox One controller input to GIMX via UDP.

    Replaces:
      - eDAT_ControllerV3_Script.ps1 (all functions)
      - ShortPressButton_C1, LongPressButton_C1, MoveStick_C1, etc.
    """

    # Installed at Program Files (x86) — confirmed via filesystem check
    GIMX_EXECUTABLE = r"C:\Program Files (x86)\GIMX\gimx.exe"
    # GIMX user config dir (XOnePadUsb.xml lives here)
    GIMX_CONFIG_DIR = r"C:\Users\testx\AppData\Roaming\gimx\config"

    def __init__(self, config: GimxConfig):
        self.config = config
        self._sock: Optional[socket.socket] = None
        self._gimx_process: Optional[subprocess.Popen] = None
        self._connect()

    def _connect(self):
        """Open UDP socket to GIMX (equivalent to $Sock = New-Object System.Net.Sockets.Socket)"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.connect((self.config.host, self.config.port))
        logger.info(f"GIMX UDP socket connected: {self.config.host}:{self.config.port}")

    def _build_packet(self, changes: dict[int, int]) -> bytes:
        """
        Build GIMX Network API 'Send report' packet.

        Packet format (big-endian):
          [0x01] [axis_count] ([axis_id] [int32 value]) * axis_count

        Replaces: create_changes_packet() in eDAT_ControllerV3_Script.ps1
        """
        packet = bytearray()
        packet.append(0x01)                    # Constant first byte
        packet.append(len(changes))            # Number of axis changes

        for axis_id, value in changes.items():
            packet.append(axis_id & 0xFF)
            # Big-endian 4-byte signed int (HostToNetworkOrder equivalent)
            packet += struct.pack(">i", value)

        return bytes(packet)

    def _send(self, packet: bytes):
        """Send packet to GIMX via UDP"""
        if self._sock:
            self._sock.send(packet)

    def check_status(self) -> bool:
        """
        Verify GIMX is running by sending a minimal report packet and checking
        the OS does not refuse the connection.

        GIMX Network API is send-only (Python → GIMX); GIMX never sends replies.
        The reliable indicator that GIMX is listening is:
          - send succeeds  → GIMX is up            (return True)
          - ConnectionRefusedError / no process    → GIMX not running (return False)
          - WinError 10054 (connection reset)       → GIMX is up but Xbox not yet
                                                      enumerated — still return True
                                                      so we don't falsely re-launch.

        Replaces: Check-XboxControllerStatus() in eDAT_ControllerV3_Script.ps1
        """
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.settimeout(1.0)
            temp_sock.connect((self.config.host, self.config.port))
            # Send a null (all-released) report — GIMX accepts and ignores it
            null_report = self._build_packet({})
            temp_sock.send(null_report)
            temp_sock.close()
            logger.info("GIMX: UDP port reachable — process is running")
            return True
        except ConnectionRefusedError:
            logger.warning("GIMX: ConnectionRefused — process not running")
            return False
        except OSError as e:
            # WinError 10054 = connection reset by remote — GIMX IS running
            # but Xbox controller not yet enumerated. Treat as running.
            if hasattr(e, "winerror") and e.winerror == 10054:
                logger.info("GIMX: Running (Xbox controller enumerating…)")
                return True
            logger.warning(f"GIMX: OSError — {e}")
            return False

    def start_gimx(self, wait_seconds: int = 20) -> bool:
        """
        Start GIMX process if not already running.
        Replaces: Init_HwV3() in eDAT_ControllerV3_Script.ps1
        """
        if self.check_status():
            logger.info("GIMX: Reusing existing process")
            return True

        # Proxy mode: --config Xbox_latest.xml supplies the real Xbox Series S
        # controller connected to PC for GIP security auth (Series S requires this).
        # --src lets Python inject button values via UDP on top of the auth stream.
        import pathlib
        config_file = self.config.config_file
        user_config = pathlib.Path(self.GIMX_CONFIG_DIR) / config_file
        config_path = str(user_config) if user_config.exists() else config_file

        cmd = [
            self.GIMX_EXECUTABLE,
            "--config", config_path,
            "--src", f"{self.config.host}:{self.config.port}",
            "-p", self.config.com_port,
            "--nograb",
            "--force-updates",
        ]
        logger.info(f"Starting GIMX (proxy+UDP mode): {' '.join(cmd)}")

        # Launch GIMX in a new console window so its output is visible separately
        self._gimx_process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        # Poll until GIMX is ready (up to wait_seconds)
        logger.info(f"Waiting up to {wait_seconds}s for GIMX to initialise…")
        for elapsed in range(wait_seconds):
            time.sleep(1)
            if self.check_status():
                logger.info(f"GIMX: Ready after {elapsed + 1}s")
                return True
            logger.debug(f"GIMX: Waiting… ({elapsed + 1}s)")

        logger.error("GIMX: Failed to start or controller not detected on Xbox")
        return False

    def stop_gimx(self):
        """Stop GIMX process if we started it. Replaces: Disconnect_HwV3()"""
        if self._gimx_process:
            self._gimx_process.terminate()
            self._gimx_process = None
            logger.info("GIMX: Process stopped")

    # ─────────────────────────────────────────────
    # Core press functions
    # ─────────────────────────────────────────────

    def short_press(self, button: XboxButton, console: int = 1):
        """
        Short button press (press + release).
        Replaces: ShortPressButton_C1() / ShortPressButton_C2()
        """
        full_press = (ButtonValue.TRIGGER_FULL_PRESS
                      if button in (XboxButton.LT, XboxButton.RT)
                      else ButtonValue.PRESSED)

        press_packet   = self._build_packet({button: full_press})
        release_packet = self._build_packet({button: ButtonValue.RELEASED})

        self._send(press_packet)
        logger.debug(f"Short press: {button.name} on Console {console}")
        time.sleep(self.config.short_press_ms / 1000)
        self._send(release_packet)
        time.sleep(self.config.cooldown_ms / 1000)
        time.sleep(self.config.post_press_delay_ms / 1000)

    def long_press(self, button: XboxButton, hold_ms: Optional[int] = None, console: int = 1):
        """
        Long button press. Replaces: LongPressButton_C1() / CustomLongPressButton_C1()
        """
        hold_time = (hold_ms or self.config.long_press_ms) / 1000
        full_press = (ButtonValue.TRIGGER_FULL_PRESS
                      if button in (XboxButton.LT, XboxButton.RT)
                      else ButtonValue.PRESSED)

        press_packet   = self._build_packet({button: full_press})
        release_packet = self._build_packet({button: ButtonValue.RELEASED})

        self._send(press_packet)
        logger.debug(f"Long press: {button.name} ({hold_ms or self.config.long_press_ms}ms) on Console {console}")
        time.sleep(hold_time)
        self._send(release_packet)
        time.sleep(self.config.cooldown_ms / 1000)

    def combo_press(self, button1: XboxButton, button2: XboxButton, console: int = 1):
        """
        Press two buttons simultaneously.
        Replaces: ComboPressButton_C1() — used for 360Guide (View+Menu)
        """
        def _full(b):
            return (ButtonValue.TRIGGER_FULL_PRESS
                    if b in (XboxButton.LT, XboxButton.RT)
                    else ButtonValue.PRESSED)

        press_packet   = self._build_packet({button1: _full(button1), button2: _full(button2)})
        release_packet = self._build_packet({button1: ButtonValue.RELEASED, button2: ButtonValue.RELEASED})

        self._send(press_packet)
        logger.debug(f"Combo press: {button1.name} + {button2.name}")
        time.sleep(self.config.short_press_ms / 1000)
        self._send(release_packet)
        time.sleep(self.config.cooldown_ms / 1000)

    def hold_button(self, button: XboxButton, console: int = 1):
        """Hold button down (no release). Replaces: HoldButton_C1()"""
        full_press = (ButtonValue.TRIGGER_FULL_PRESS
                      if button in (XboxButton.LT, XboxButton.RT)
                      else ButtonValue.PRESSED)
        self._send(self._build_packet({button: full_press}))
        time.sleep(self.config.cooldown_ms / 1000)

    def release_button(self, button: XboxButton, console: int = 1):
        """Release a held button. Replaces: ReleaseButton_C1()"""
        self._send(self._build_packet({button: ButtonValue.RELEASED}))
        time.sleep(self.config.cooldown_ms / 1000)

    def move_stick(self, stick_axis: XboxButton, position: int, console: int = 1):
        """
        Move analog stick to position, then release.
        Replaces: MoveStick_C1() / MoveStick_C2()
        """
        press_packet   = self._build_packet({stick_axis: position})
        release_packet = self._build_packet({stick_axis: ButtonValue.RELEASED})
        self._send(press_packet)
        time.sleep(self.config.short_press_ms / 1000)
        self._send(release_packet)
        time.sleep(self.config.cooldown_ms / 1000)

    def left_stick_input(self, x: int = 0, y: int = 0, console: int = 1):
        """
        Set left stick to percentage (-100 to 100).
        Replaces: LeftStickInput() in eDAT_ControllerV3_Script.ps1
        """
        x_val = int(ButtonValue.STICK_FULL_RIGHT * (x * 0.01))
        y_val = int(ButtonValue.STICK_FULL_DOWN  * (y * 0.01))
        packet = self._build_packet({
            XboxButton.LEFT_STICK_X: x_val,
            XboxButton.LEFT_STICK_Y: y_val,
        })
        self._send(packet)

    def right_stick_input(self, x: int = 0, y: int = 0, console: int = 1):
        """
        Set right stick to percentage. Replaces: RightStickInput()
        """
        x_val = int(ButtonValue.STICK_FULL_RIGHT * (x * 0.01))
        y_val = int(ButtonValue.STICK_FULL_DOWN  * (y * 0.01))
        packet = self._build_packet({
            XboxButton.RIGHT_STICK_X: x_val,
            XboxButton.RIGHT_STICK_Y: y_val,
        })
        self._send(packet)

    # ─────────────────────────────────────────────
    # High-level named button shortcuts
    # Replaces: ControllerCommands-HWv3.ps1
    # ─────────────────────────────────────────────

    def press_up(self, console: int = 1):
        self.short_press(XboxButton.UP, console)

    def press_down(self, console: int = 1):
        self.short_press(XboxButton.DOWN, console)

    def press_left(self, console: int = 1):
        self.short_press(XboxButton.LEFT, console)

    def press_right(self, console: int = 1):
        self.short_press(XboxButton.RIGHT, console)

    def press_a(self, console: int = 1):
        self.short_press(XboxButton.A, console)

    def press_b(self, console: int = 1):
        self.short_press(XboxButton.B, console)

    def press_x(self, console: int = 1):
        self.short_press(XboxButton.X, console)

    def press_y(self, console: int = 1):
        self.short_press(XboxButton.Y, console)

    def press_xbox(self, console: int = 1):
        self.short_press(XboxButton.GUIDE, console)

    def long_press_xbox(self, console: int = 1):
        """Long press Xbox button (power off / sync). Replaces: CtrllerPwr"""
        self.long_press(XboxButton.GUIDE, console=console)

    def press_menu(self, console: int = 1):
        self.short_press(XboxButton.MENU, console)

    def long_press_menu(self, console: int = 1):
        self.long_press(XboxButton.MENU, console=console)

    def press_view(self, console: int = 1):
        self.short_press(XboxButton.VIEW, console)

    def press_lb(self, console: int = 1):
        self.short_press(XboxButton.LB, console)

    def press_rb(self, console: int = 1):
        self.short_press(XboxButton.RB, console)

    def press_lt(self, console: int = 1):
        self.short_press(XboxButton.LT, console)

    def press_rt(self, console: int = 1):
        self.short_press(XboxButton.RT, console)

    def press_360_guide(self, console: int = 1):
        """Combo: View + Menu (replaces ConsoleOne_360Guide)"""
        self.combo_press(XboxButton.VIEW, XboxButton.MENU, console)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None


class DualGimxController:
    """
    Manages two GIMX controllers simultaneously.
    Replaces: Init_HwV3_TwoControllers() + C1/C2 functions.
    """

    def __init__(self, config1: GimxConfig, config2: GimxConfig):
        self.c1 = GimxController(config1)
        self.c2 = GimxController(config2)

    def start(self) -> bool:
        c1_ok = self.c1.check_status()
        c2_ok = self.c2.check_status()
        if c1_ok and c2_ok:
            logger.info("Dual GIMX: Reusing both existing controllers")
            return True
        if c1_ok or c2_ok:
            logger.error("Dual GIMX: Only one controller found. Please restart GIMX with 2-controller config.")
            return False
        return self.c1.start_gimx() and self.c2.check_status()

    def close(self):
        self.c1.close()
        self.c2.close()
