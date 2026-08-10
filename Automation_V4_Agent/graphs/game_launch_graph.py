"""Sub-graph for game launch + verification flow."""
from __future__ import annotations
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from ..utils.logger import get_logger
from ..utils.helpers import wait_ms

log = get_logger("game_launch_graph")


class LaunchState(TypedDict):
    game_name: str
    console: int
    launch_icon: str
    home_icon: str
    launch_ok: bool
    error: Optional[str]


def _get_ctrl(console: int):
    """Build a GimxController from hardware_config.yaml for the given console."""
    from ..hardware.gimx_controller import GimxController, GimxConfig
    from ..config.loader import get_hw_config
    gimx = get_hw_config().get("gimx", {})
    key = "controller_1" if console == 1 else "controller_2"
    c = gimx.get(key, {})
    return GimxController(config=GimxConfig(
        host=c.get("host", "127.0.0.1"),
        port=c.get("port", 51914 if console == 1 else 51915),
        com_port=c.get("com_port", "COM8" if console == 1 else "COM6"),
    ))


def node_press_guide(state: LaunchState) -> LaunchState:
    log.debug(f"[{state['game_name']}] Pressing Guide button…")
    from ..hardware.gimx_controller import XboxButton
    ctrl = _get_ctrl(state["console"])
    ctrl.short_press(XboxButton.GUIDE)
    wait_ms(2000)
    return state


def node_navigate_to_game(state: LaunchState) -> LaunchState:
    log.debug(f"[{state['game_name']}] Navigating to game tile…")
    from ..hardware.gimx_controller import XboxButton
    ctrl = _get_ctrl(state["console"])
    ctrl.short_press(XboxButton.RIGHT)
    wait_ms(500)
    ctrl.short_press(XboxButton.A)
    wait_ms(5000)
    return state


def node_verify_launch(state: LaunchState) -> LaunchState:
    log.debug(f"[{state['game_name']}] Verifying launch icon…")
    from ..vision.pattern_match import ScreenVerifier
    verifier = ScreenVerifier()
    ok = verifier.verify("launch_cap", state["launch_icon"], timeout=60)
    return {**state, "launch_ok": ok, "error": None if ok else "Launch icon not found"}


def route_verify(state: LaunchState) -> str:
    return "success" if state["launch_ok"] else "failed"


def build_game_launch_graph():
    g = StateGraph(LaunchState)
    g.add_node("press_guide", node_press_guide)
    g.add_node("navigate", node_navigate_to_game)
    g.add_node("verify", node_verify_launch)
    g.set_entry_point("press_guide")
    g.add_edge("press_guide", "navigate")
    g.add_edge("navigate", "verify")
    g.add_conditional_edges("verify", route_verify,
                            {"success": END, "failed": END})
    return g.compile()