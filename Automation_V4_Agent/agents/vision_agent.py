"""LangChain tool wrappers for screen verification (pattern match + OCR)."""
from __future__ import annotations
from langchain.tools import tool
from ..vision.pattern_match import ScreenVerifier, PatternMatcher
from ..vision.ocr_engine import OcrEngine
from ..hardware.video_capture import VideoCapture
from ..utils.logger import get_logger

log = get_logger("vision_agent")


class VisionAgent:
    """Wraps ScreenVerifier and OcrEngine with LangChain-compatible interface."""

    def __init__(self):
        from ..config.loader import get_hw_config
        cfg = get_hw_config()
        cam_cfg = cfg.get("camera", {})
        self._device_index: int = cam_cfg.get("device_index", 0)
        captured_folder: str = cam_cfg.get("captured_image_folder", "Images\\Captured\\Console\\")
        icon_folder: str = cam_cfg.get("icon_image_folder", "Images\\Icon\\XBoxConsole\\")

        self.capture: VideoCapture | None = None
        # ScreenVerifier is created with a PatternMatcher and folder paths.
        # The capture device is wired in lazily inside _ensure_capture().
        self.verifier = ScreenVerifier(
            capture_device=None,
            matcher=PatternMatcher(),
            captured_folder=captured_folder,
            icon_folder=icon_folder,
        )
        self.ocr = OcrEngine()

    def _ensure_capture(self):
        if self.capture is None:
            self.capture = VideoCapture(device_index=self._device_index)
            self.capture.open()
            # Wire the live capture device into the verifier now that it exists.
            self.verifier.capture = self.capture

    def capture_screen(self, save_path: str) -> str | None:
        self._ensure_capture()
        return self.capture.capture_and_save(save_path)

    def verify_pattern(self, captured_name: str, icon_name: str, timeout: int = 30) -> bool:
        return self.verifier.verify(captured_name, icon_name, timeout=timeout)

    def extract_ocr(self, image_path: str, region_label: str) -> str:
        return self.ocr.extract_text(image_path, region_label)


def build_vision_tools():
    """Return list of LangChain @tool functions for vision verification."""
    agent = VisionAgent()

    @tool
    def verify_screen_pattern(captured_name: str, icon_name: str, timeout_seconds: int = 30) -> str:
        """Verify that the captured screen matches the expected icon/template image.
        captured_name: name of captured screenshot (without extension).
        icon_name: name of reference icon image (without extension).
        timeout_seconds: how long to keep retrying."""
        try:
            result = agent.verify_pattern(captured_name, icon_name, timeout=timeout_seconds)
            return f"{'PASS' if result else 'FAIL'}: pattern match {icon_name}"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def read_screen_text(image_path: str, region_label: str) -> str:
        """Extract text from a screen region using OCR (pytesseract).
        image_path: absolute path to the captured image.
        region_label: label defined in ocr_regions.yaml (e.g. Account1, signIN_Top1)."""
        try:
            text = agent.extract_ocr(image_path, region_label)
            return f"OCR result: '{text}'"
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def capture_screenshot(save_path: str) -> str:
        """Capture a screenshot from the AVerMedia capture card and save to save_path."""
        try:
            path = agent.capture_screen(save_path)
            if path:
                return f"OK: screenshot saved to {path}"
            return "FAIL: could not capture screenshot"
        except Exception as exc:
            return f"ERROR: {exc}"

    return [verify_screen_pattern, read_screen_text, capture_screenshot]
