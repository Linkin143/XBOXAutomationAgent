"""Sub-graph for screen verification with retry logic."""
from __future__ import annotations
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from ..utils.logger import get_logger
from ..utils.helpers import wait_ms

log = get_logger("verification_graph")


class VerificationState(TypedDict):
    captured_name: str
    icon_name: str
    timeout_seconds: int
    retry_count: int
    max_retries: int
    verified: bool
    ocr_region: Optional[str]
    expected_text: Optional[str]
    ocr_result: Optional[str]
    error: Optional[str]


def node_capture(state: VerificationState) -> VerificationState:
    log.debug(f"Capturing screen for {state['captured_name']}…")
    from ..hardware.video_capture import VideoCapture
    from ..config.loader import get_hw_config
    idx = get_hw_config().get("camera", {}).get("device_index", 0)
    cap = VideoCapture(device_index=idx)
    cap.open()
    from ..vision.image_utils import build_captured_path
    path = build_captured_path(state["captured_name"])
    cap.capture_and_save(path)
    return state


def node_pattern_match(state: VerificationState) -> VerificationState:
    log.debug(f"Pattern matching {state['icon_name']}…")
    from ..vision.pattern_match import PatternMatcher
    from ..vision.image_utils import build_captured_path, build_icon_path
    matcher = PatternMatcher()
    result = matcher.match(
        build_captured_path(state["captured_name"]),
        build_icon_path(state["icon_name"]),
    )
    if result.matched:
        log.debug(f"Match found (score={result.score:.3f})")
        return {**state, "verified": True, "error": None}
    log.debug(f"No match (score={result.score:.3f})")
    return {**state, "verified": False,
            "error": f"Pattern score {result.score:.3f} below threshold"}


def node_ocr_verify(state: VerificationState) -> VerificationState:
    if not state.get("ocr_region") or not state.get("expected_text"):
        return state
    log.debug(f"OCR verify region={state['ocr_region']} expected={state['expected_text']}")
    from ..vision.ocr_engine import OcrEngine
    from ..vision.image_utils import build_captured_path
    engine = OcrEngine()
    text = engine.extract_text(build_captured_path(state["captured_name"]),
                               state["ocr_region"])
    matched = state["expected_text"].lower() in text.lower()
    return {**state, "ocr_result": text, "verified": matched}


def node_retry(state: VerificationState) -> VerificationState:
    retry = state.get("retry_count", 0) + 1
    log.debug(f"Retry {retry}/{state['max_retries']}…")
    wait_ms(1000)
    return {**state, "retry_count": retry}


def route_match_result(state: VerificationState) -> str:
    if state["verified"]:
        return "done"
    if state.get("retry_count", 0) < state.get("max_retries", 5):
        return "retry"
    return "done"


def build_verification_graph():
    g = StateGraph(VerificationState)
    g.add_node("capture", node_capture)
    g.add_node("pattern_match", node_pattern_match)
    g.add_node("ocr_verify", node_ocr_verify)
    g.add_node("retry", node_retry)
    g.set_entry_point("capture")
    g.add_edge("capture", "pattern_match")
    g.add_edge("pattern_match", "ocr_verify")
    g.add_conditional_edges("ocr_verify", route_match_result,
                            {"done": END, "retry": "retry"})
    g.add_edge("retry", "capture")
    return g.compile()