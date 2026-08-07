"""Sea of Stars — game test script for Automation V4."""
from __future__ import annotations
from ..hardware.gimx_controller import XboxButton
from ..utils.helpers import wait_ms
from ..utils.logger import get_logger
from .base_game import BaseGame

log = get_logger("game.sea_of_stars")


class SeaOfStarsGame(BaseGame):
    """Tests for Sea of Stars on Xbox."""

    @property
    def game_name(self) -> str:
        return "Sea of Stars"

    @property
    def launch_icon_name(self) -> str:
        return "sea_of_stars_main_menu"

    @property
    def home_icon_name(self) -> str:
        return "xbox_home_icon"

    def run_game_tests(self) -> None:
        log.info("[SeaOfStars] Starting game tests…")
        wait_ms(5000)
        # Press A through any splash screens
        for _ in range(3):
            self._press(XboxButton.A)
            wait_ms(1500)
        # Verify main menu
        ok = self.verifier.verify("sos_menu_cap", "sea_of_stars_menu_icon", timeout=30)
        log.info(f"[SeaOfStars] Menu verified: {ok}")
        # Open Settings
        self._press(XboxButton.VIEW)
        wait_ms(2000)
        self._press(XboxButton.B)
        wait_ms(1000)
        log.info("[SeaOfStars] Game tests complete.")
