"""
ViGEm Controller — Automation V4 Agent
========================================
Drop-in replacement for GimxController using vgamepad + ViGEmBus.

Signal path (no GIMX, no Arduino, no COM port needed):
    Python → vgamepad → ViGEmBus kernel driver → Virtual Xbox 360 controller
    Xbox Series S reads XInput — real controller in slot 0 provides auth.

Public API is identical to GimxController so all callers work unchanged.
"""
from __future__ import annotations
import time
import logging
from typing import Optional
import vgamepad as vg
from .gimx_controller import XboxButton, ButtonValue, GimxConfig

logger = logging.getLogger(__name__)

# ── XboxButton → XUSB_BUTTON mapping ─────────────────────────────────────────
_BUTTON_MAP: dict[int, vg.XUSB_BUTTON] = {
    XboxButton.A:     vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    XboxButton.B:     vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    XboxButton.X:     vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    XboxButton.Y:     vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    XboxButton.LB:    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    XboxButton.RB:    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    XboxButton.GUIDE: vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    XboxButton.MENU:  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    XboxButton.VIEW:  vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    XboxButton.UP:    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    XboxButton.DOWN:  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    XboxButton.LEFT:  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    XboxButton.RIGHT: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    XboxButton.LS:    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    XboxButton.RS:    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
}

_AXIS_BUTTONS = {
    XboxButton.LT, XboxButton.RT,
    XboxButton.LEFT_STICK_X, XboxButton.LEFT_STICK_Y,
    XboxButton.RIGHT_STICK_X, XboxButton.RIGHT_STICK_Y,
}



class VigemController:
    """Xbox controller emulation via ViGEmBus — identical API to GimxController."""

    def __init__(self, config: Optional[GimxConfig] = None):
        self.config = config or GimxConfig()
        self._pad: vg.VX360Gamepad = vg.VX360Gamepad()
        self._pad.reset()
        self._pad.update()
        logger.info("ViGEmController: VX360Gamepad registered with ViGEmBus")

    def _press(self, button: XboxButton) -> None:
        xusb = _BUTTON_MAP.get(int(button))
        if xusb is None:
            return
        self._pad.press_button(button=xusb)
        self._pad.update()

    def _release(self, button: XboxButton) -> None:
        xusb = _BUTTON_MAP.get(int(button))
        if xusb is None:
            return
        self._pad.release_button(button=xusb)
        self._pad.update()

    def short_press(self, button: XboxButton, console: int = 1) -> None:
        """Short press — identical signature to GimxController.short_press()."""
        if button in _AXIS_BUTTONS:
            self.send_axis(button, ButtonValue.PRESSED)
            time.sleep(self.config.short_press_ms / 1000.0)
            self.send_axis(button, ButtonValue.RELEASED)
        else:
            self._press(button)
            time.sleep(self.config.short_press_ms / 1000.0)
            self._release(button)
        time.sleep(self.config.cooldown_ms / 1000.0)
        logger.debug(f"ViGEm short_press: {button.name}")

    def long_press(self, button: XboxButton, hold_ms: Optional[int] = None,
                   console: int = 1) -> None:
        """Long press — identical signature to GimxController.long_press()."""
        duration = (hold_ms or self.config.long_press_ms) / 1000.0
        if button in _AXIS_BUTTONS:
            self.send_axis(button, ButtonValue.PRESSED)
            time.sleep(duration)
            self.send_axis(button, ButtonValue.RELEASED)
        else:
            self._press(button)
            time.sleep(duration)
            self._release(button)
        time.sleep(self.config.cooldown_ms / 1000.0)
        logger.debug(f"ViGEm long_press: {button.name} {hold_ms or self.config.long_press_ms}ms")

    def send_axis(self, button: XboxButton, value: int, console: int = 1) -> None:
        """Set axis value — identical signature to GimxController.send_axis()."""
        if button == XboxButton.LT:
            self._pad.left_trigger(value=max(0, min(255, abs(value))))
        elif button == XboxButton.RT:
            self._pad.right_trigger(value=max(0, min(255, abs(value))))
        elif button == XboxButton.LEFT_STICK_X:
            self._pad.left_joystick(x_value=value, y_value=0)
        elif button == XboxButton.LEFT_STICK_Y:
            self._pad.left_joystick(x_value=0, y_value=value)
        elif button == XboxButton.RIGHT_STICK_X:
            self._pad.right_joystick(x_value=value, y_value=0)
        elif button == XboxButton.RIGHT_STICK_Y:
            self._pad.right_joystick(x_value=0, y_value=value)
        else:
            self._press(button) if value != 0 else self._release(button)
            return
        self._pad.update()

    def move_stick(self, axis: XboxButton, value: int, console: int = 1) -> None:
        self.send_axis(axis, value)

    def combo_press(self, btn1: XboxButton, btn2: XboxButton, console: int = 1) -> None:
        self._press(btn1)
        self._press(btn2)
        time.sleep(self.config.short_press_ms / 1000.0)
        self._release(btn1)
        self._release(btn2)
        time.sleep(self.config.cooldown_ms / 1000.0)

    def left_stick_input(self, x: int = 0, y: int = 0, console: int = 1) -> None:
        self._pad.left_joystick(x_value=int(32767 * x / 100), y_value=int(32767 * y / 100))
        self._pad.update()

    def right_stick_input(self, x: int = 0, y: int = 0, console: int = 1) -> None:
        self._pad.right_joystick(x_value=int(32767 * x / 100), y_value=int(32767 * y / 100))
        self._pad.update()

    def check_status(self) -> bool:
        return self._pad is not None

    def start_gimx(self, wait_seconds: int = 20) -> bool:
        logger.info("ViGEmController: ViGEmBus is a kernel driver — no process needed")
        return True

    # Named shortcuts matching GimxController API
    def press_a(self, c=1): self.short_press(XboxButton.A, c)
    def press_b(self, c=1): self.short_press(XboxButton.B, c)
    def press_x(self, c=1): self.short_press(XboxButton.X, c)
    def press_y(self, c=1): self.short_press(XboxButton.Y, c)
    def press_up(self, c=1): self.short_press(XboxButton.UP, c)
    def press_down(self, c=1): self.short_press(XboxButton.DOWN, c)
    def press_left(self, c=1): self.short_press(XboxButton.LEFT, c)
    def press_right(self, c=1): self.short_press(XboxButton.RIGHT, c)
    def press_xbox(self, c=1): self.short_press(XboxButton.GUIDE, c)
    def press_menu(self, c=1): self.short_press(XboxButton.MENU, c)
    def press_view(self, c=1): self.short_press(XboxButton.VIEW, c)
    def press_lb(self, c=1): self.short_press(XboxButton.LB, c)
    def press_rb(self, c=1): self.short_press(XboxButton.RB, c)
    def long_press_xbox(self, c=1): self.long_press(XboxButton.GUIDE, console=c)

    def close(self) -> None:
        try:
            self._pad.reset()
            self._pad.update()
        except Exception:
            pass
        logger.info("ViGEmController: closed")

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
