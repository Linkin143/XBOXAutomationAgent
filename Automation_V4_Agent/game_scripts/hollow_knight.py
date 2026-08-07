"""Hollow Knight — game test script for Automation V4."""
from __future__ import annotations
from ..hardware.gimx_controller import XboxButton
from ..utils.helpers import wait_ms
from ..utils.logger import get_logger
from .base_game import BaseGame

log = get_logger("game.hollow_knight")


class HollowKnightGame(BaseGame):
    """Tests for Hollow Knight on Xbox."""

    @property
    def game_name(self) -> str:
        return "Hollow Knight"

    @property
    def launch_icon_name(self) -> str:
        return "hollow_knight_main_menu"

    @property
    def home_icon_name(self) -> str:
        return "xbox_home_icon"

    def run_game_tests(self) -> None:
        log.info("[HollowKnight] Starting game tests…")
        wait_ms(4000)
        # Accept any controller prompt
        self._press(XboxButton.A)
        wait_ms(2000)
        # Verify main menu logo
        ok = self.verifier.verify("hk_menu_cap", "hollow_knight_menu_icon", timeout=30)
        log.info(f"[HollowKnight] Menu verified: {ok}")
        # Navigate to New Game
        self._press(XboxButton.DOWN)
        wait_ms(400)
        self._press(XboxButton.A)
        wait_ms(5000)
        # Back
        self._press(XboxButton.B)
        wait_ms(2000)
        log.info("[HollowKnight] Game tests complete.")
