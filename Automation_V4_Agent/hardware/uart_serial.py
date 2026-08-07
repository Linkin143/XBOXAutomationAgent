"""
UART / Serial Communication — Automation V4 Agent
===================================================
Pure Python replacement for:
  - Hcl.eDAT.SerialCommunication.dll
  - Hcl.eDAT.Serial.dll
  - eDAT_Serial_Script.ps1

Physical path:
  Python → pyserial → COM port → UART → jumper cables (TX↔RX, RX↔TX, GND↔GND)
         → Arduino UNO → USB → Xbox Console (hardware KBM)
         → COM8 → Relay board
         → COM6 → Digital Pot
"""

import serial
import serial.tools.list_ports
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SerialPortConfig:
    """
    Serial port configuration.
    Replaces XML config in eDAT_Serial_Configuration.xml
    """
    label: str
    port: str
    baud_rate: int = 9600
    data_bits: int = 8
    parity: str = "N"           # N=None, E=Even, O=Odd
    stop_bits: float = 1
    flow_control: str = "none"  # none, xonxoff, rtscts
    read_timeout_ms: int = 4000
    write_timeout_ms: int = 1000
    wait_for_data_ms: int = 4000

    def _parity_map(self) -> str:
        return {"None": "N", "Even": "E", "Odd": "O", "N": "N", "E": "E", "O": "O"}.get(
            self.parity, "N"
        )


@dataclass
class SerialResult:
    """
    Mirrors eDAT result object (IsSuccess, StatusMessage, Data).
    Replaces: $bRet.IsSuccess / $bRet.StatusMessage / $bRet.Data
    """
    is_success: bool = False
    status_message: str = ""
    data: Optional[bytes] = None


class SerialController:
    """
    Manages a single serial port connection.
    Replaces: Hcl.eDAT.Custom.Controller.SerialController in eDAT_Serial_Script.ps1

    Usage example:
        config = SerialPortConfig(label="PortLabel2", port="COM8", baud_rate=9600)
        ctrl = SerialController(config)
        ctrl.initialize()
        ctrl.connect()
        ctrl.write_hex(bytes([0x43, 0x02]))  # relay command
        ctrl.disconnect()
    """

    def __init__(self, config: SerialPortConfig):
        self.config = config
        self._port: Optional[serial.Serial] = None

    def initialize(self) -> SerialResult:
        """
        Replaces: Intialize_Serial($SerialPort) in eDAT_Serial_Script.ps1
        Validates port configuration without opening.
        """
        try:
            available = [p.device for p in serial.tools.list_ports.comports()]
            if self.config.port not in available:
                msg = f"Port {self.config.port} not found. Available: {available}"
                logger.warning(msg)
                return SerialResult(False, msg)
            logger.info(f"Serial initialized: {self.config.label} on {self.config.port}")
            return SerialResult(True, f"Serial {self.config.port} initialized")
        except Exception as e:
            return SerialResult(False, str(e))

    def connect(self) -> SerialResult:
        """
        Open serial port. Replaces: Connect_Serial($SerialPort)
        """
        try:
            xonxoff = self.config.flow_control.lower() == "xonxoff"
            rtscts  = self.config.flow_control.lower() == "rtscts"

            self._port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=self.config.data_bits,
                parity=self.config._parity_map(),
                stopbits=self.config.stop_bits,
                timeout=self.config.read_timeout_ms / 1000,
                write_timeout=self.config.write_timeout_ms / 1000,
                xonxoff=xonxoff,
                rtscts=rtscts,
            )
            logger.info(f"Serial connected: {self.config.port} @ {self.config.baud_rate} baud")
            return SerialResult(True, f"Connected to {self.config.port}")
        except serial.SerialException as e:
            logger.error(f"Serial connect failed: {e}")
            return SerialResult(False, str(e))

    def write_data(self, data: str) -> SerialResult:
        """
        Write string data. Replaces: WriteData($SerialPort, $SendData)
        """
        try:
            encoded = data.encode("utf-8")
            self._port.write(encoded)
            logger.debug(f"Serial write (str): {data!r} → {self.config.port}")
            return SerialResult(True, f"Wrote {len(encoded)} bytes")
        except Exception as e:
            return SerialResult(False, str(e))

    def write_hex(self, byte_data: bytes) -> SerialResult:
        """
        Write raw bytes. Replaces: WriteDatainHex($SerialPort, $bytData)

        Example (relay board from Constants.ps1):
            write_hex(bytes([0x43, 0x02]))  # PortOne + two = press A button via relay
        """
        try:
            self._port.write(byte_data)
            logger.debug(f"Serial write (hex): {byte_data.hex()} → {self.config.port}")
            return SerialResult(True, f"Wrote {len(byte_data)} hex bytes")
        except Exception as e:
            return SerialResult(False, str(e))

    def read_data(self, num_bytes: int = 256) -> SerialResult:
        """Read up to num_bytes. Replaces: ReadPortData($SerialPort)"""
        try:
            data = self._port.read(num_bytes)
            return SerialResult(True, "Read OK", data)
        except Exception as e:
            return SerialResult(False, str(e))

    def read_line(self) -> SerialResult:
        """Read until newline. Replaces: ReadLineData($SerialPort)"""
        try:
            line = self._port.readline()
            return SerialResult(True, "Read line OK", line)
        except Exception as e:
            return SerialResult(False, str(e))

    def verify_byte(self, expected: bytes) -> SerialResult:
        """
        Read and compare bytes. Replaces: VerifySerialByte()
        """
        result = self.read_data(len(expected))
        if not result.is_success:
            return result
        if result.data == expected:
            return SerialResult(True, "Byte match verified")
        return SerialResult(False, f"Byte mismatch: got {result.data!r} expected {expected!r}")

    def discard_tx_buffer(self) -> SerialResult:
        """Replaces: DiscardTransmission($SerialPort)"""
        try:
            self._port.reset_output_buffer()
            return SerialResult(True, "TX buffer discarded")
        except Exception as e:
            return SerialResult(False, str(e))

    def discard_rx_buffer(self) -> SerialResult:
        """Replaces: DiscardRecieveBuffer($SerialPort)"""
        try:
            self._port.reset_input_buffer()
            return SerialResult(True, "RX buffer discarded")
        except Exception as e:
            return SerialResult(False, str(e))

    def disconnect(self) -> SerialResult:
        """Close serial port. Replaces: Disconnect_Serial($SerialPort)"""
        try:
            if self._port and self._port.is_open:
                self._port.close()
            logger.info(f"Serial disconnected: {self.config.port}")
            return SerialResult(True, "Disconnected")
        except Exception as e:
            return SerialResult(False, str(e))

    def is_connected(self) -> bool:
        return self._port is not None and self._port.is_open

    def __enter__(self):
        self.initialize()
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()


# ─────────────────────────────────────────────
# Relay Controller
# Source: Constants.ps1 port/byte constants + XBoxConsoleRelay.ps1
# ─────────────────────────────────────────────

class RelayController:
    """
    Controls the relay board (NCD Relay) via COM8 @ 9600 baud.
    
    Port byte map from Constants.ps1:
        PortOne = 0x43, PortTwo = 0x46, PortThree = 0x4A
    Button byte values:
        zero=0, one=0x01, two=0x02, three=0x04, four=0x08,
        five=0x10, six=0x20, seven=0x40, eight=0x80
    """

    PORT_ONE   = 0x43
    PORT_TWO   = 0x46
    PORT_THREE = 0x4A

    ZERO  = 0x00
    ONE   = 0x01
    TWO   = 0x02
    THREE = 0x04
    FOUR  = 0x08
    FIVE  = 0x10
    SIX   = 0x20
    SEVEN = 0x40
    EIGHT = 0x80

    def __init__(self, serial_ctrl: SerialController):
        self._serial = serial_ctrl

        # Button byte commands from Constants.ps1
        self.CTRLLER1_A = bytes([self.PORT_ONE,   self.TWO])
        self.CTRLLER1_B = bytes([self.PORT_ONE,   self.ONE])
        self.CTRLLER1_X = bytes([self.PORT_ONE,   self.THREE])
        self.CTRLLER1_Y = bytes([self.PORT_ONE,   self.FOUR])
        self.CTRLLER1_UP    = bytes([self.PORT_TWO,   self.TWO])
        self.CTRLLER1_DOWN  = bytes([self.PORT_ONE,   self.EIGHT])
        self.CTRLLER1_LEFT  = bytes([self.PORT_TWO,   self.ONE])
        self.CTRLLER1_RIGHT = bytes([self.PORT_ONE,   self.SEVEN])
        self.CTRLLER1_XBOX  = bytes([self.PORT_TWO,   self.THREE])
        self.CTRLLER1_MENU  = bytes([self.PORT_ONE,   self.FIVE])
        self.CTRLLER1_VIEW  = bytes([self.PORT_ONE,   self.SIX])
        self.CTRLLER1_LB    = bytes([self.PORT_TWO,   self.FOUR])
        self.CTRLLER1_RB    = bytes([self.PORT_TWO,   self.FIVE])

        self.CTRLLER2_A    = bytes([self.PORT_TWO,   self.SIX])
        self.CTRLLER2_B    = bytes([self.PORT_TWO,   self.FIVE])
        self.CTRLLER2_X    = bytes([self.PORT_TWO,   self.SEVEN])
        self.CTRLLER2_Y    = bytes([self.PORT_TWO,   self.EIGHT])
        self.CTRLLER2_XBOX = bytes([self.PORT_THREE, self.SEVEN])
        self.CTRLLER2_RT   = bytes([self.PORT_THREE, self.THREE])
        self.CTRLLER2_LT   = bytes([self.PORT_THREE, self.FIVE])
        self.CTRLLER2_UP   = bytes([self.PORT_THREE, self.SIX])
        self.CTRLLER2_DOWN = bytes([self.PORT_THREE, self.FOUR])
        self.CTRLLER2_MENU = bytes([self.PORT_THREE, self.ONE])
        self.CTRLLER2_VIEW = bytes([self.PORT_THREE, self.TWO])

    def press_button(self, button_cmd: bytes, hold_ms: int = 100, console: int = 1):
        """Send relay command (press + release)"""
        init_cmd = bytes([button_cmd[0], self.ZERO])  # init port
        self._serial.write_hex(init_cmd)
        time.sleep(0.05)
        self._serial.write_hex(button_cmd)
        time.sleep(hold_ms / 1000)
        self._serial.write_hex(init_cmd)   # release
        logger.debug(f"Relay press: {button_cmd.hex()} on Console {console}")


# ─────────────────────────────────────────────
# Arduino KBM Controller
# Replaces: Hcl.eDAT.Teensy.dll + Arduino COM3
# ─────────────────────────────────────────────

class ArduinoKBMController:
    """
    Sends keyboard/mouse HID commands to Arduino UNO.
    Arduino is connected: PC ↔ UART ↔ jumpers ↔ Arduino ↔ USB ↔ Xbox

    The Arduino firmware should implement a serial protocol
    where byte commands trigger keyboard/mouse actions on the console.
    """

    def __init__(self, serial_ctrl: SerialController):
        self._serial = serial_ctrl

    def send_command(self, cmd: bytes):
        """Send raw command bytes to Arduino"""
        self._serial.write_hex(cmd)
        time.sleep(0.05)

    def send_key(self, key_code: int, hold_ms: int = 100):
        """Press and release a HID key"""
        self._serial.write_hex(bytes([0x01, key_code]))  # press
        time.sleep(hold_ms / 1000)
        self._serial.write_hex(bytes([0x00, key_code]))  # release
        logger.debug(f"Arduino key: 0x{key_code:02X} for {hold_ms}ms")


def list_available_ports() -> list[str]:
    """List all available COM ports on the system"""
    ports = serial.tools.list_ports.comports()
    result = []
    for p in ports:
        result.append(f"{p.device}: {p.description}")
    return result
