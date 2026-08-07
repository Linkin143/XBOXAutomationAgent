"""
Pattern Matching — Automation V4 Agent
========================================
Pure Python replacement for:
  - Hcl.eDAT.ImageCompare.dll
  - Emgu.CV (OpenCV .NET wrapper)
  - eDAT_Image_Pattern_Script.ps1
  - Match_Pattern() / Pattern_Verification() functions

Uses cv2.matchTemplate() — direct equivalent of OpenCV template matching.
"""

import cv2
import numpy as np
import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PatternMatchResult:
    """
    Mirrors eDAT result: $ret.Data.MatchFound / $ret.IsSuccess
    """
    match_found: bool = False
    confidence: float = 0.0
    location: Optional[tuple] = None   # (x, y) top-left of best match
    is_success: bool = False
    status_message: str = ""


class PatternMatcher:
    """
    Template-based pattern matching using OpenCV.
    Replaces: Hcl.eDAT.ImageCompare.dll + Match_Pattern() function.

    Usage:
        matcher = PatternMatcher()
        result = matcher.match(captured_img_path, icon_img_path)
        if result.match_found:
            # test passed
    """

    DEFAULT_THRESHOLD = 0.7    # Match confidence threshold (70%)
    RESIZE_BASE_WIDTH  = 1920  # From Constants.ps1 $Global:IconBaseWidth
    RESIZE_BASE_HEIGHT = 1080  # From Constants.ps1 $Global:IconBaseHeight

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold

    def _load_image(self, path: str) -> Optional[np.ndarray]:
        """Load image from path (BGR)"""
        img = cv2.imread(path)
        if img is None:
            logger.error(f"Cannot load image: {path}")
        return img

    def _resize_to_base(self, img: np.ndarray) -> np.ndarray:
        """
        Resize captured image to 1920x1080 base size for consistent matching.
        Replaces: icon base size matching in eDAT_Image_Pattern_Script.ps1
        """
        h, w = img.shape[:2]
        if w != self.RESIZE_BASE_WIDTH or h != self.RESIZE_BASE_HEIGHT:
            img = cv2.resize(img, (self.RESIZE_BASE_WIDTH, self.RESIZE_BASE_HEIGHT))
        return img

    def match(self, captured_img_path: str, template_img_path: str) -> PatternMatchResult:
        """
        Find template image within captured screen image.
        Replaces: Match_Pattern(-Cap_Img ... -Icon_Img ...) in eDAT scripts.

        Args:
            captured_img_path: Full screen capture (from AVerMedia)
            template_img_path: Icon/reference image to find

        Returns:
            PatternMatchResult with match_found, confidence, location
        """
        cap_img  = self._load_image(captured_img_path)
        tmpl_img = self._load_image(template_img_path)

        if cap_img is None or tmpl_img is None:
            return PatternMatchResult(
                is_success=False,
                status_message="Failed to load images"
            )

        return self.match_arrays(cap_img, tmpl_img)

    def match_arrays(
        self,
        captured_img: np.ndarray,
        template_img: np.ndarray
    ) -> PatternMatchResult:
        """
        Match using numpy arrays (for in-memory matching without disk I/O).
        """
        try:
            # Resize captured image to standard base resolution
            source = self._resize_to_base(captured_img.copy())

            # Convert both to grayscale for matching
            source_gray = cv2.cvtColor(source,   cv2.COLOR_BGR2GRAY)
            tmpl_gray   = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

            # Template must be smaller than source
            th, tw = tmpl_gray.shape[:2]
            sh, sw = source_gray.shape[:2]
            if tw > sw or th > sh:
                logger.warning(f"Template ({tw}x{th}) larger than source ({sw}x{sh}), skipping")
                return PatternMatchResult(
                    is_success=True,
                    match_found=False,
                    status_message="Template larger than source"
                )

            # Run template matching
            result = cv2.matchTemplate(source_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            match_found = max_val >= self.threshold
            logger.debug(
                f"Pattern match: confidence={max_val:.3f} "
                f"(threshold={self.threshold}), found={match_found}, loc={max_loc}"
            )

            return PatternMatchResult(
                match_found=match_found,
                confidence=float(max_val),
                location=max_loc,
                is_success=True,
                status_message=(
                    "Image Pattern Matched" if match_found
                    else "Image Pattern not Matched"
                )
            )

        except Exception as e:
            logger.error(f"Pattern match error: {e}")
            return PatternMatchResult(is_success=False, status_message=str(e))


class ScreenVerifier:
    """
    High-level screen verification with timeout and retry.
    Replaces: Pattern_Verification() in eDAT_Image_Pattern_Script.ps1

    Usage:
        verifier = ScreenVerifier(capture_device, matcher)
        success = verifier.verify(
            captured_name="Home_Icon",
            icon_name="Home_Icon",
            timeout=30
        )
    """

    def __init__(self, capture_device, matcher: PatternMatcher,
                 captured_folder: str, icon_folder: str):
        self.capture = capture_device
        self.matcher = matcher
        self.captured_folder = captured_folder
        self.icon_folder = icon_folder

    def verify(
        self,
        captured_name: str,
        icon_name: str,
        timeout: int = 30,
        poll_interval: float = 0.5,
    ) -> bool:
        """
        Poll for pattern match until timeout.
        Replaces: Pattern_Verification(-CapturedImage ... -IconImage ... -Timeout ...)

        Args:
            captured_name: Name for captured image (no extension)
            icon_name:     Name of reference/icon image (no extension)
            timeout:       Seconds to poll
            poll_interval: Seconds between captures

        Returns:
            True if pattern found within timeout, False otherwise
        """
        icon_path = str(Path(self.icon_folder) / f"{icon_name}.bmp")

        if not Path(icon_path).exists():
            logger.error(f"Icon image not found: {icon_path}")
            return False

        captured_path = str(Path(self.captured_folder) / f"{captured_name}.bmp")
        deadline = time.time() + timeout

        logger.info(f"Verifying pattern: {icon_name} (timeout={timeout}s)")

        while time.time() < deadline:
            # Capture current screen
            saved = self.capture.capture_and_save(captured_path)
            if saved is None:
                time.sleep(poll_interval)
                continue

            result = self.matcher.match(captured_path, icon_path)

            if result.match_found:
                logger.info(f"Pattern match SUCCESS: {icon_name} "
                             f"(confidence={result.confidence:.3f})")
                return True

            time.sleep(poll_interval)

        logger.warning(f"Pattern match TIMEOUT: {icon_name} after {timeout}s")
        return False

    def verify_ocr(
        self,
        captured_name: str,
        expected_text: str,
        region_label: str,
        ocr_engine,
        timeout: int = 10,
        poll_interval: float = 0.5,
    ) -> bool:
        """
        Poll for OCR text match until timeout.
        Replaces: VerifyOCRTextMatch() in eDAT scripts.
        """
        captured_path = str(Path(self.captured_folder) / f"{captured_name}.bmp")
        deadline = time.time() + timeout

        while time.time() < deadline:
            saved = self.capture.capture_and_save(captured_path)
            if saved:
                text = ocr_engine.extract_text(captured_path, region_label)
                if text and expected_text.lower() in text.lower():
                    logger.info(f"OCR match SUCCESS: '{expected_text}' found in region {region_label}")
                    return True
            time.sleep(poll_interval)

        logger.warning(f"OCR match TIMEOUT: '{expected_text}' not found in region {region_label}")
        return False
