"""LangChain tool wrappers for GimxController (Xbox gamepad emulation)."""
from __future__ import annotations
import json
from typing import Optional
from langchain.tools import tool
from ..hardware.gimx_controller import GimxController, XboxButton
from ..utils.logger import get_logger

log = get_logger("controller_agent")

_ctrl1: Optional[GimxController] = None
_ctrl2: Optional[GimxController] = None


def _get_controller(console: int) -> GimxController:
    global _ctrl1, _ctrl2
    if console == 1:
        if _ctrl1 is None:
            from ..config.loader import get_hw_config
            cfg = get_hw_config()
            gc = cfg.get("gimx", {})
            _ctrl1 = GimxController(
                host=gc.get("host", "127.0.0.1"),
                port=gc.get("port_c1", 51914),
            )
        return _ctrl1
    else:
        if _ctrl2 is None:
            from ..config.loader import get_hw_config
            cfg = get_hw_config()
            gc = cfg.get("gimx", {})
            _ctrl2 = GimxController(
                host=gc.get("host", "127.0.0.1"),
                port=gc.get("port_c2", 51915),
            )
        return _ctrl2


class ControllerAgent:
    """Wraps GimxController with LangChain-compatible interface."""

    def __init__(self, console: int = 1):
        self.console = console
        self.ctrl = _get_controller(console)

    def short_press(self, button_name: str) -> bool:
        btn = XboxButton[button_name.upper()]
        self.ctrl.short_press(btn)
        log.info(f"C{self.console} short_press {button_name}")
        return True

    def long_press(self, button_name: str, hold_ms: int = 3000) -> bool:
        btn = XboxButton[button_name.upper()]
        self.ctrl.long_press(btn, hold_ms=hold_ms)
        log.info(f"C{self.console} long_press {button_name} {hold_ms}ms")
        return True

    def move_stick(self, axis_name: str, value: int) -> bool:
        axis = XboxButton[axis_name.upper()]
        self.ctrl.send_axis(axis, value)
        log.info(f"C{self.console} move_stick {axis_name}={value}")
        return True


def build_controller_tools(console: int = 1):
    """Return list of LangChain @tool functions for controller *console*."""
    agent = ControllerAgent(console)

    @tool
    def press_xbox_button(button_name: str) -> str:
        """Short-press an Xbox button. button_name must be one of: A, B, X, Y,
        LB, RB, LT, RT, VIEW, MENU, GUIDE, UP, DOWN, LEFT, RIGHT, LS, RS."""
        try:
            agent.short_press(button_name)
            return f"OK: short_press {button_name} on console {console}"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def long_press_xbox_button(button_name: str, hold_ms: int = 3000) -> str:
        """Long-press an Xbox button for hold_ms milliseconds."""
        try:
            agent.long_press(button_name, hold_ms)
            return f"OK: long_press {button_name} {hold_ms}ms on console {console}"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def move_xbox_stick(axis_name: str, value: int) -> str:
        """Move an Xbox analog stick/trigger. axis_name: LEFT_STICK_X, LEFT_STICK_Y,
        RIGHT_STICK_X, RIGHT_STICK_Y, LT, RT. value: -32767 to 32767."""
        try:
            agent.move_stick(axis_name, value)
            return f"OK: move_stick {axis_name}={value} on console {console}"
        except Exception as exc:
            return f"ERROR: {exc}"

    return [press_xbox_button, long_press_xbox_button, move_xbox_stick]
