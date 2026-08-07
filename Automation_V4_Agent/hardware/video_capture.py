"""
Video Capture — Automation V4 Agent
=====================================
Pure Python replacement for:
  - Hcl.eDAT.ImageCapture.dll
  - Hcl.eDAT.Video.dll / Hcl.eDAT.VFCapture.dll
  - AForge.Video.DirectShow.dll
  - eDAT_Image_Camera_Script.ps1

Captures from AVerMedia U3 via DirectShow backend in OpenCV.
"""

import cv2
import numpy as np
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class VideoCapture:
    """
    Captures frames from AVerMedia U3 Video Capture device.
    Replaces: Hcl.eDAT.ImageCapture.dll + Image_Capture() in eDAT scripts.

    Physical path:
      Xbox HDMI → AVerMedia U3 Capture Card → PC (DirectShow)
    """

    def __init__(
        self,
        device_index: int = 0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        use_dshow: bool = True,
    ):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None

        # Use DirectShow backend on Windows (equivalent to AForge DirectShow)
        self._backend = cv2.CAP_DSHOW if use_dshow else cv2.CAP_ANY

    def open(self) -> bool:
        """
        Open capture device. Replaces: Initialize() in Hcl.eDAT.ImageCapture
        """
        try:
            self._cap = cv2.VideoCapture(self.device_index, self._backend)
            if not self._cap.isOpened():
                logger.error(f"Cannot open capture device index {self.device_index}")
                return False

            # Set resolution and FPS
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)

            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Capture opened: device={self.device_index}, "
                        f"resolution={actual_w}x{actual_h}")
            return True
        except Exception as e:
            logger.error(f"Video capture open failed: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the device.
        Replaces: Image_Capture(-ImagePath ...) in eDAT_Image_Camera_Script.ps1
        Returns: BGR image as numpy array, or None on failure
        """
        if not self._cap or not self._cap.isOpened():
            logger.warning("Capture device not open, attempting to open...")
            if not self.open():
                return None

        # Discard a few frames to get a fresh one (avoid buffered stale frames)
        for _ in range(3):
            self._cap.grab()

        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.error("Failed to capture frame")
            return None

        logger.debug(f"Frame captured: {frame.shape}")
        return frame

    def capture_and_save(self, save_path: str) -> Optional[str]:
        """
        Capture frame and save to disk as BMP (matching V3 .bmp format).
        Replaces: Image_Capture(-ImagePath $Global:CapturedImgPath)

        Returns: path to saved image, or None on failure
        """
        frame = self.capture_frame()
        if frame is None:
            return None

        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Save as BMP to match V3 format
        cv2.imwrite(save_path, frame)
        logger.info(f"Frame saved: {save_path}")
        return save_path

    def capture_to_memory(self) -> Optional[np.ndarray]:
        """Capture frame without saving to disk"""
        return self.capture_frame()

    def record_video(self, output_path: str, duration_seconds: int,
                     codec: str = "mp4v") -> bool:
        """
        Record video for given duration.
        Replaces: RecordVideo_ffmpeg() in CommonFunctions.ps1
        """
        frame = self.capture_frame()
        if frame is None:
            return False

        fourcc = cv2.VideoWriter_fourcc(*codec)
        h, w = frame.shape[:2]
        writer = cv2.VideoWriter(output_path, fourcc, self.fps, (w, h))

        start = time.time()
        logger.info(f"Recording video: {output_path} for {duration_seconds}s")

        try:
            while time.time() - start < duration_seconds:
                f = self.capture_frame()
                if f is not None:
                    writer.write(f)
        finally:
            writer.release()
            logger.info(f"Video saved: {output_path}")

        return True

    def close(self):
        """Release capture device"""
        if self._cap:
            self._cap.release()
            self._cap = None
            logger.info("Capture device released")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def enumerate_devices(max_index: int = 10) -> list[dict]:
        """
        Find all available video capture devices.
        Useful to identify AVerMedia U3 device index.
        """
        devices = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                devices.append({"index": i, "width": w, "height": h})
                cap.release()
        return devices


class FrameExtractor:
    """
    Extracts frames from recorded video for latency analysis.
    Replaces: Generate_Frames() + ComputeFrame_LinearSearch_OCR()
              in CommonFunctions.ps1
    """

    def __init__(self, video_path: str, output_folder: str):
        self.video_path = video_path
        self.output_folder = output_folder
        Path(output_folder).mkdir(parents=True, exist_ok=True)

    def extract_all_frames(self, prefix: str = "frame") -> list[str]:
        """
        Extract all frames from video as BMP files.
        Replaces: Generate_Frames()
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {self.video_path}")
            return []

        frame_paths = []
        i = 1
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            path = os.path.join(self.output_folder, f"{prefix}{i}.bmp")
            cv2.imwrite(path, frame)
            frame_paths.append(path)
            i += 1

        cap.release()
        logger.info(f"Extracted {len(frame_paths)} frames to {self.output_folder}")
        return frame_paths

    def get_fps(self) -> float:
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return fps
