"""Base game class — defines the launch / play / quit lifecycle."""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..hardware.gimx_controller import GimxController, XboxButton
from ..vision.pattern_match import ScreenVerifier
from ..vision.ocr_engine import OcrEngine
from ..hardware.video_capture import VideoCapture
from ..utils.logger import get_logger
from ..utils.helpers import wait_ms, timestamp_str

log = get_logger("base_game")


@dataclass
class GameResult:
    game_name: str
    launch_status: str = "NOT_RUN"     # PASS / FAIL / NOT_RUN
    quit_status: str = "NOT_RUN"
    latency_ms: float = 0.0
    notes: str = ""
    timestamp: str = field(default_factory=timestamp_str)


class BaseGame(ABC):
    """Abstract base for all game test scripts.

    Each concrete game subclass must implement:
      - game_name: str property
      - launch_icon_name: str property  (icon used to navigate to game)
      - home_icon_name: str property    (icon for Xbox home screen)
      - run_game_tests() method         (game-specific interactions)
    """

    def __init__(
        self,
        ctrl1: GimxController,
        ctrl2: Optional[GimxController] = None,
        capture: Optional[VideoCapture] = None,
        console: int = 1,
    ):
        self.ctrl1 = ctrl1
        self.ctrl2 = ctrl2 or ctrl1
        self.capture = capture
        self.console = console
        self.verifier = ScreenVerifier()
        self.ocr = OcrEngine()
        self._result = GameResult(game_name=self.game_name)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def game_name(self) -> str:
        """Human-readable game name (matches game_config.yaml key)."""

    @property
    @abstractmethod
    def launch_icon_name(self) -> str:
        """Icon filename (no extension) to verify after launching game."""

    @property
    @abstractmethod
    def home_icon_name(self) -> str:
        """Icon filename (no extension) for Xbox home / dashboard."""

    @abstractmethod
    def run_game_tests(self) -> None:
        """Override to implement game-specific test interactions."""

    # ------------------------------------------------------------------
    # Lifecycle methods
    # ------------------------------------------------------------------

    def launch(self) -> bool:
        """Navigate to and launch the game. Returns True on success."""
        log.info(f"[{self.game_name}] Launching…")
        start = time.time()
        try:
            # Press Xbox Guide → Home
            self._press(XboxButton.GUIDE)
            wait_ms(2000)
            # Navigate to game tile (A to launch)
            self._navigate_to_game()
            wait_ms(500)
            self._press(XboxButton.A)
            wait_ms(5000)
            # Verify launch
            ok = self.verifier.verify("captured_launch", self.launch_icon_name, timeout=60)
            self._result.latency_ms = (time.time() - start) * 1000.0
            self._result.launch_status = "PASS" if ok else "FAIL"
            log.info(f"[{self.game_name}] Launch → {self._result.launch_status}")
            return ok
        except Exception as exc:
            self._result.launch_status = "FAIL"
            self._result.notes += f" launch_error={exc}"
            log.error(f"[{self.game_name}] Launch exception: {exc}")
            return False

    def quit_game(self) -> bool:
        """Quit back to Xbox home screen. Returns True on success."""
        log.info(f"[{self.game_name}] Quitting…")
        try:
            # Hold Xbox Guide to trigger quick menu
            self._long_press(XboxButton.GUIDE, 1000)
            wait_ms(1000)
            # Navigate to Quit Game option
            self._press(XboxButton.DOWN)
            wait_ms(300)
            self._press(XboxButton.A)
            wait_ms(1000)
            self._press(XboxButton.A)  # Confirm
            wait_ms(3000)
            ok = self.verifier.verify("captured_home", self.home_icon_name, timeout=30)
            self._result.quit_status = "PASS" if ok else "FAIL"
            log.info(f"[{self.game_name}] Quit → {self._result.quit_status}")
            return ok
        except Exception as exc:
            self._result.quit_status = "FAIL"
            self._result.notes += f" quit_error={exc}"
            log.error(f"[{self.game_name}] Quit exception: {exc}")
            return False

    def run(self) -> GameResult:
        """Full test lifecycle: launch → run_game_tests → quit."""
        launched = self.launch()
        if launched:
            try:
                self.run_game_tests()
            except Exception as exc:
                log.error(f"[{self.game_name}] run_game_tests exception: {exc}")
                self._result.notes += f" game_test_error={exc}"
            self.quit_game()
        return self._result

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------

    def _press(self, button: XboxButton, console: int | None = None) -> None:
        ctrl = self.ctrl1 if (console or self.console) == 1 else self.ctrl2
        ctrl.short_press(button)

    def _long_press(self, button: XboxButton, hold_ms: int,
                    console: int | None = None) -> None:
        ctrl = self.ctrl1 if (console or self.console) == 1 else self.ctrl2
        ctrl.long_press(button, hold_ms=hold_ms)

    def _navigate_to_game(self) -> None:
        """Default: press RIGHT once to move off Guide button to game tile.
        Subclasses can override for custom navigation."""
        self._press(XboxButton.RIGHT)
        wait_ms(500)
