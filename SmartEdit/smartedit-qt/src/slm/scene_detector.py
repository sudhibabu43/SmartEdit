"""
@file
@brief Scene Detection module using OpenCV content-based frame differencing.
@author SmartEdit Team
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV (cv2) is not available. Scene detection will not function.")


class SceneDetectionEngine:
    """
    Analyzes video content to detect scene boundaries using fast frame differencing.
    """

    def __init__(self, threshold: float = 30.0, min_scene_len_sec: float = 1.0):
        self.threshold = threshold
        self.min_scene_len_sec = min_scene_len_sec

    def detect_scenes(self, video_path: str, max_duration_sec: float = 0.0) -> Dict[str, Any]:
        """
        Detects scene boundaries in the video file.

        Args:
            video_path: Path to the video file.
            max_duration_sec: Optional duration limit to prevent hanging on huge files.

        Returns:
            Dict containing "boundaries" (list of floats) and "scenes" (metadata list).
        """
        if not OPENCV_AVAILABLE:
            logger.error("Scene detection failed: OpenCV is not installed.")
            return {"boundaries": [], "scenes": []}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Scene detection failed: Cannot open video {video_path}")
            return {"boundaries": [], "scenes": []}

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # We will sample at a lower framerate to speed up processing
        sample_fps = 5.0 
        frame_step = max(1, int(fps / sample_fps))

        boundaries = []
        scenes = []

        prev_frame = None
        frame_idx = 0
        last_boundary_time = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if max_duration_sec > 0 and (frame_idx / fps) > max_duration_sec:
                break

            if frame_idx % frame_step != 0:
                frame_idx += 1
                continue

            # Convert to grayscale and downscale for fast differencing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (256, 144))

            if prev_frame is not None:
                # Calculate mean absolute difference between current and previous frame
                diff = cv2.absdiff(gray, prev_frame)
                mean_diff = np.mean(diff)

                if mean_diff > self.threshold:
                    time_sec = frame_idx / fps
                    # Ensure minimum scene duration is met before declaring a new scene
                    if (time_sec - last_boundary_time) >= self.min_scene_len_sec:
                        boundaries.append(time_sec)
                        scenes.append({
                            "scene_id": len(scenes) + 1,
                            "start_time": last_boundary_time,
                            "end_time": time_sec,
                            "duration": time_sec - last_boundary_time,
                            "confidence": min(float(mean_diff) / 50.0, 1.0)
                        })
                        last_boundary_time = time_sec

            prev_frame = gray
            frame_idx += 1

        cap.release()

        # Add the final scene segment
        total_time_analyzed = frame_idx / fps
        if total_time_analyzed - last_boundary_time > 0.1:
            scenes.append({
                "scene_id": len(scenes) + 1,
                "start_time": last_boundary_time,
                "end_time": total_time_analyzed,
                "duration": total_time_analyzed - last_boundary_time,
                "confidence": 1.0
            })

        return {
            "boundaries": boundaries,
            "scenes": scenes,
            "total_analyzed_sec": total_time_analyzed
        }
