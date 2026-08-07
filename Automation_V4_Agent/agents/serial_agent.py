"""LangChain tool wrappers for serial communication (relay board + Arduino KBM)."""
from __future__ import annotations
from langchain.tools import tool
from ..hardware.uart_serial import RelayController, ArduinoKBMController, PORT_ONE, PORT_TWO, PORT_THREE
from ..utils.logger import get_logger

log = get_logger("serial_agent")

_relay: RelayController | None = None
_arduino: ArduinoKBMController | None = None

RELAY_PORT_MAP = {
    "PORT_ONE": PORT_ONE,
    "PORT_TWO": PORT_TWO,
    "PORT_THREE": PORT_THREE,
}


def _get_relay() -> RelayController:
    global _relay
    if _relay is None:
        from ..config.loader import get_hw_config
        cfg = get_hw_config()
        sp = cfg.get("serial_ports", {})
        relay_cfg = sp.get("relay", {})
        _relay = RelayController(
            port=relay_cfg.get("port", "COM8"),
            baud_rate=relay_cfg.get("baud_rate", 9600),
        )
        _relay.serial.connect()
    return _relay


def _get_arduino() -> ArduinoKBMController:
    global _arduino
    if _arduino is None:
        from ..config.loader import get_hw_config
        cfg = get_hw_config()
        sp = cfg.get("serial_ports", {})
        kbm_cfg = sp.get("arduino_kbm", {})
        _arduino = ArduinoKBMController(
            port=kbm_cfg.get("port", "COM3"),
            baud_rate=kbm_cfg.get("baud_rate", 115200),
        )
        _arduino.serial.connect()
    return _arduino


class SerialAgent:
    """Wraps serial hardware controllers."""

    def press_relay(self, port_name: str, hold_ms: int = 100) -> bool:
        cmd = RELAY_PORT_MAP.get(port_name.upper())
        if cmd is None:
            raise ValueError(f"Unknown relay port: {port_name}")
        _get_relay().press_button(cmd, hold_ms=hold_ms)
        log.info(f"Relay {port_name} pressed for {hold_ms}ms")
        return True

    def send_key(self, key_code: int, hold_ms: int = 100) -> bool:
        _get_arduino().send_key(key_code, hold_ms=hold_ms)
        log.info(f"Arduino KBM key 0x{key_code:02X} held {hold_ms}ms")
        return True


def build_serial_tools():
    """Return list of LangChain @tool functions for serial control."""
    agent = SerialAgent()

    @tool
    def press_relay_button(port_name: str, hold_ms: int = 100) -> str:
        """Press a hardware relay button via serial.
        port_name: PORT_ONE, PORT_TWO, or PORT_THREE.
        hold_ms: duration in milliseconds to hold the relay closed."""
        try:
            agent.press_relay(port_name, hold_ms)
            return f"OK: relay {port_name} pressed {hold_ms}ms"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def send_arduino_key(key_code: int, hold_ms: int = 100) -> str:
        """Send a keycode to Arduino KBM controller via UART.
        key_code: integer HID keycode (e.g. 0x04 = 'a').
        hold_ms: duration in milliseconds."""
        try:
            agent.send_key(key_code, hold_ms)
            return f"OK: key 0x{key_code:02X} sent {hold_ms}ms"
        except Exception as exc:
            return f"ERROR: {exc}"

    return [press_relay_button, send_arduino_key]
