"""Celeste — game test script for Automation V4."""
from __future__ import annotations
from ..hardware.gimx_controller import XboxButton
from ..utils.helpers import wait_ms
from ..utils.logger import get_logger
from .base_game import BaseGame

log = get_logger("game.celeste")


class CelesteGame(BaseGame):
    """Tests for Celeste on Xbox."""

    @property
    def game_name(self) -> str:
        return "Celeste"

    @property
    def launch_icon_name(self) -> str:
        return "celeste_main_menu"

    @property
    def home_icon_name(self) -> str:
        return "xbox_home_icon"

    def run_game_tests(self) -> None:
        log.info("[Celeste] Starting game tests…")
        # Wait for main menu
        wait_ms(3000)
        # Press A to start
        self._press(XboxButton.A)
        wait_ms(2000)
        # Navigate to Chapter 1
        self._press(XboxButton.A)
        wait_ms(5000)
        # Verify chapter loaded
        ok = self.verifier.verify("celeste_chapter1", "celeste_chapter1_icon", timeout=20)
        log.info(f"[Celeste] Chapter 1 loaded: {ok}")
        wait_ms(2000)
        # Press menu to pause
        self._press(XboxButton.MENU)
        wait_ms(1000)
        # Return to main menu
        self._press(XboxButton.B)
        wait_ms(2000)
        log.info("[Celeste] Game tests complete.")
