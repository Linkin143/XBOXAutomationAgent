"""
OCR Engine — Automation V4 Agent
===================================
Pure Python replacement for:
  - Hcl.eDAT.OCR.dll
  - Hcl.eDAT.Tesseract.dll
  - libtesseract400.dll / eng.traineddata
  - eDAT_OCR_DefaultOCR1_Script.ps1
  - ExtractTessaractSingle() function

Uses pytesseract (Python Tesseract wrapper) with region-based extraction.
"""

import cv2
import numpy as np
import pytesseract
import logging
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Point pytesseract to Tesseract executable (Windows default path)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass
class OcrRegion:
    """
    Defines a screen region for OCR extraction.
    Replaces: XML region definitions in eDAT_OCR_XBOX_Configuration.xml
    """
    x: int
    y: int
    width: int
    height: int
    description: str = ""


class OcrEngine:
    """
    Extracts text from images using Tesseract OCR.
    Replaces: Hcl.eDAT.OCR.dll + ExtractTessaractSingle() in eDAT scripts.

    Usage:
        engine = OcrEngine(regions_config_path="config/ocr_regions.yaml")
        text = engine.extract_text(image_path, region_label="Account1")
        if text == expected_text:
            # match
    """

    def __init__(
        self,
        regions_config_path: str = "",
        lang: str = "eng",
        config: str = "--psm 6",
    ):
        self.lang = lang
        self.config = config
        self.regions: dict[str, OcrRegion] = {}
        # Resolve default path relative to this file so it works regardless of cwd
        if not regions_config_path:
            from pathlib import Path
            regions_config_path = str(
                Path(__file__).parent.parent / "config" / "ocr_regions.yaml"
            )
        self._load_regions(regions_config_path)

    def _load_regions(self, config_path: str):
        """Load OCR region definitions from YAML config"""
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
            for label, region in data.get("regions", {}).items():
                self.regions[label] = OcrRegion(
                    x=region["x"],
                    y=region["y"],
                    width=region["width"],
                    height=region["height"],
                    description=region.get("description", ""),
                )
            logger.info(f"OCR: Loaded {len(self.regions)} regions from {config_path}")
        except FileNotFoundError:
            logger.warning(f"OCR regions config not found: {config_path}")
        except Exception as e:
            logger.error(f"OCR regions load error: {e}")

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        - Upscale, grayscale, threshold
        """
        # Upscale by 2x (matches V3's tessdata preprocessing)
        h, w = img.shape[:2]
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply binary threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        return thresh

    def extract_text(
        self,
        image_path: str,
        region_label: str,
        preprocess: bool = True,
    ) -> str:
        """
        Extract text from a specific region of an image.
        Replaces: ExtractTessaractSingle(-img_path ... -label ... -reg_label ...)

        Args:
            image_path:    Path to screenshot (.bmp)
            region_label:  Region name defined in ocr_regions.yaml
            preprocess:    Apply preprocessing for better accuracy

        Returns:
            Extracted text string (lowercase, stripped)
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"OCR: Cannot load image: {image_path}")
            return ""

        if region_label not in self.regions:
            logger.warning(f"OCR: Region '{region_label}' not defined, using full image")
            region_img = img
        else:
            r = self.regions[region_label]
            region_img = img[r.y:r.y + r.height, r.x:r.x + r.width]
            if region_img.size == 0:
                logger.warning(f"OCR: Empty region crop for '{region_label}'")
                return ""

        if preprocess:
            region_img = self._preprocess(region_img)

        try:
            raw_text = pytesseract.image_to_string(
                region_img, lang=self.lang, config=self.config
            )
            extracted = raw_text.strip().lower()
            logger.debug(f"OCR [{region_label}]: '{extracted}'")
            return extracted
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ""

    def extract_text_from_array(
        self,
        img: np.ndarray,
        region_label: Optional[str] = None,
        preprocess: bool = True,
    ) -> str:
        """
        Extract text from numpy array image (no disk I/O).
        Useful for in-memory frame analysis.
        """
        if region_label and region_label in self.regions:
            r = self.regions[region_label]
            img = img[r.y:r.y + r.height, r.x:r.x + r.width]

        if preprocess:
            img = self._preprocess(img)

        try:
            raw = pytesseract.image_to_string(img, lang=self.lang, config=self.config)
            return raw.strip().lower()
        except Exception as e:
            logger.error(f"OCR array extraction error: {e}")
            return ""

    def extract_full_page(self, image_path: str) -> str:
        """Extract text from the entire image (no region crop)"""
        img = cv2.imread(image_path)
        if img is None:
            return ""
        processed = self._preprocess(img)
        try:
            return pytesseract.image_to_string(
                processed, lang=self.lang, config=self.config
            ).strip().lower()
        except Exception as e:
            logger.error(f"OCR full page error: {e}")
            return ""

    def add_region(self, label: str, x: int, y: int, width: int, height: int):
        """Dynamically add an OCR region"""
        self.regions[label] = OcrRegion(x=x, y=y, width=width, height=height)

    def verify_text(
        self,
        image_path: str,
        region_label: str,
        expected_text: str,
    ) -> bool:
        """
        Convenience method: extract text and compare.
        Replaces the pattern: $extract_txt -eq $Exp_text
        """
        extracted = self.extract_text(image_path, region_label)
        match = expected_text.lower() in extracted
        logger.debug(
            f"OCR verify: expected='{expected_text}' extracted='{extracted}' match={match}"
        )
        return match
