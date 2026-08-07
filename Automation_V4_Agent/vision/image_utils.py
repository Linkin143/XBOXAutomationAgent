"""
Image Utilities — Automation V4 Agent
=======================================
Shared image utility functions.
Replaces: Hcl.eDAT.BaseImageUtilities.dll + various image helpers
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def build_captured_path(folder: str, name: str) -> str:
    """
    Build path for captured image.
    Replaces: Captured_ImgPath(-img_name $CapturedImage)
    """
    return str(Path(folder) / f"{name}.bmp")


def build_icon_path(folder: str, name: str) -> str:
    """
    Build path for icon/reference image.
    Replaces: Icon_ImgPath(-img_name $IconImage)
    """
    return str(Path(folder) / f"{name}.bmp")


def load_image(path: str) -> Optional[np.ndarray]:
    """Load image file, return None if not found"""
    img = cv2.imread(path)
    if img is None:
        logger.warning(f"Image not found: {path}")
    return img


def save_image(img: np.ndarray, path: str) -> bool:
    """Save numpy array image to path"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return cv2.imwrite(path, img)


def resize_to_base(img: np.ndarray,
                   base_w: int = 1920, base_h: int = 1080) -> np.ndarray:
    """Resize to standard base resolution for consistent matching"""
    h, w = img.shape[:2]
    if w != base_w or h != base_h:
        img = cv2.resize(img, (base_w, base_h))
    return img


def crop_region(img: np.ndarray, x: int, y: int,
                width: int, height: int) -> np.ndarray:
    """Crop a region from image"""
    return img[y:y + height, x:x + width]


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR to grayscale"""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def draw_match_rectangle(
    img: np.ndarray,
    location: tuple,
    template_shape: tuple,
    color: tuple = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """Draw a rectangle around a pattern match location"""
    x, y = location
    h, w = template_shape[:2]
    result = img.copy()
    cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
    return result


# ─────────────────────────────────────────────
# Dynamic Keyboard Navigation
# Replaces: DynamicKeyBoard() in ConsoleNavigation.ps1
# ─────────────────────────────────────────────

KEYBOARD_LAYOUT = [
    ["", "", "", "", "<", ">", "[", "]", "{", "}"],
    ["=", "+", "\\", ";", ":", '"', "*", "/", "", ""],
    ["!", "@", "#", "$", "%", "&", "(", ")", "-", "_"],
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", "'"],
    ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "?"],
]


def get_key_navigation(
    character: str,
    current_col: int = 5,
    current_row: int = 1,
) -> dict:
    """
    Calculate navigation moves to reach a character on the Xbox keyboard.
    Replaces: DynamicKeyBoard() in ConsoleNavigation.ps1

    Returns:
        {
          "row": target row,
          "col": target col,
          "row_moves": (positive=down, negative=up),
          "col_moves": (positive=right, negative=left),
          "needs_lt_shift": bool (for special chars rows 0-2)
        }
    """
    char = character.upper() if character.isalpha() else character

    for row_idx, row in enumerate(KEYBOARD_LAYOUT):
        if char in row:
            col_idx = row.index(char)
            return {
                "row": row_idx,
                "col": col_idx,
                "row_moves": row_idx - current_row,
                "col_moves": col_idx - current_col,
                "needs_lt_shift": row_idx <= 2,
                "found": True,
            }

    logger.warning(f"Character '{character}' not found in keyboard layout")
    return {"found": False}


def type_string_navigation(text: str) -> list[dict]:
    """
    Generate all navigation steps for typing a string.
    Replaces: DynamicKeyBoard() full logic.

    Returns: list of actions per character
    """
    actions = []
    current_col = 5
    current_row = 1

    for char in text:
        if char == " ":
            actions.append({"type": "space"})
            continue

        nav = get_key_navigation(char, current_col, current_row)
        if not nav.get("found"):
            continue

        action = {
            "type": "char",
            "character": char,
            "row_moves": nav["row_moves"],
            "col_moves": nav["col_moves"],
            "needs_lt_shift": nav["needs_lt_shift"],
        }
        actions.append(action)
        current_row = nav["row"]
        current_col = nav["col"]

    return actions
