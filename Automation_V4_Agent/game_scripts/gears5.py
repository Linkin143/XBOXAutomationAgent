"""Gears 5 — game test script for Automation V4."""
from __future__ import annotations
from ..hardware.gimx_controller import XboxButton
from ..utils.helpers import wait_ms
from ..utils.logger import get_logger
from .base_game import BaseGame

log = get_logger("game.gears5")


class Gears5Game(BaseGame):
    """Tests for Gears 5 on Xbox."""

    @property
    def game_name(self) -> str:
        return "Gears 5"

    @property
    def launch_icon_name(self) -> str:
        return "gears5_main_menu"

    @property
    def home_icon_name(self) -> str:
        return "xbox_home_icon"

    def run_game_tests(self) -> None:
        log.info("[Gears5] Starting game tests…")
        # Wait for main menu to fully load
        wait_ms(8000)
        # Press A to confirm any prompt
        self._press(XboxButton.A)
        wait_ms(3000)
        # Verify main menu
        ok = self.verifier.verify("gears5_menu_cap", "gears5_main_menu_icon", timeout=30)
        log.info(f"[Gears5] Main menu verified: {ok}")
        # Navigate to Campaign
        self._press(XboxButton.DOWN)
        wait_ms(500)
        self._press(XboxButton.A)
        wait_ms(5000)
        # Back to main menu
        self._press(XboxButton.B)
        wait_ms(2000)
        log.info("[Gears5] Game tests complete.")
