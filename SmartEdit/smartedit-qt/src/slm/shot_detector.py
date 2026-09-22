"""
@file
@brief Service layer for mapping ShotAnalyzer results (A-Roll, B-Roll, Pan) to timeline clips.
@author SmartEdit Team
"""

import os
import uuid
from typing import List, Dict, Any, Optional

from slm.shot_analyzer import ShotAnalyzer

class ShotTypeService:
    def __init__(self, analyzer: Optional[ShotAnalyzer] = None):
        self.analyzer = analyzer or ShotAnalyzer()

    def detect_timeline_aroll(self, clips: List[Any]) -> List[Dict[str, Any]]:
        """Finds A-Roll clips on the timeline."""
        results = []
        for clip in clips:
            c_data = clip.data if isinstance(clip.data, dict) else {}
            path = self._get_clip_path(clip)
            if not path:
                continue

            analysis = self.analyzer.analyze_role(path)
            if analysis.get("is_aroll"):
                c_start = float(c_data.get("start", 0.0))
                c_end = float(c_data.get("end", 0.0))
                pos = float(c_data.get("position", 0.0))
                dur = float(c_data.get("duration", 0.0))
                
                results.append({
                    "clip_id": clip.id,
                    "clip_name": c_data.get("title", f"Clip {clip.id}"),
                    "timeline_start": pos,
                    "timeline_end": pos + dur,
                    "timeline_duration": dur,
                    "media_start": c_start,
                    "media_end": c_end,
                    "confidence": analysis.get("confidence", 0.0),
                    "reason": analysis.get("reason", "")
                })
        return results

    def detect_timeline_broll(self, clips: List[Any]) -> List[Dict[str, Any]]:
        """Finds B-Roll clips on the timeline."""
        results = []
        for clip in clips:
            c_data = clip.data if isinstance(clip.data, dict) else {}
            path = self._get_clip_path(clip)
            if not path:
                continue

            analysis = self.analyzer.analyze_role(path)
            if analysis.get("is_broll"):
                c_start = float(c_data.get("start", 0.0))
                c_end = float(c_data.get("end", 0.0))
                pos = float(c_data.get("position", 0.0))
                dur = float(c_data.get("duration", 0.0))
                
                results.append({
                    "clip_id": clip.id,
                    "clip_name": c_data.get("title", f"Clip {clip.id}"),
                    "timeline_start": pos,
                    "timeline_end": pos + dur,
                    "timeline_duration": dur,
                    "media_start": c_start,
                    "media_end": c_end,
                    "confidence": analysis.get("confidence", 0.0),
                    "reason": analysis.get("reason", "")
                })
        return results

    def detect_timeline_pan_shots(self, clips: List[Any]) -> List[Dict[str, Any]]:
        """Finds Pan shots within clips on the timeline."""
        results = []
        for clip in clips:
            c_data = clip.data if isinstance(clip.data, dict) else {}
            path = self._get_clip_path(clip)
            if not path:
                continue

            clip_start = float(c_data.get("start", 0.0))
            clip_end = float(c_data.get("end", 0.0))
            clip_pos = float(c_data.get("position", 0.0))

            analysis = self.analyzer.analyze_pan_shots(path)
            segments = analysis.get("pan_segments", [])
            
            effective_end = clip_end if (clip_end > 0.0) else (clip_start + analysis.get("duration_sec", 60.0))

            for seg in segments:
                src_start = float(seg.get("start", 0.0))
                src_end = float(seg.get("end", 0.0))

                sub_start = max(src_start, clip_start)
                sub_end = min(src_end, effective_end)

                if sub_end - sub_start >= 0.25:
                    tl_start = round(clip_pos + (sub_start - clip_start), 3)
                    tl_end = round(clip_pos + (sub_end - clip_start), 3)
                    tl_dur = round(tl_end - tl_start, 3)

                    results.append({
                        "clip_id": clip.id,
                        "clip_name": c_data.get("title", f"Clip {clip.id}"),
                        "media_start": round(sub_start, 3),
                        "media_end": round(sub_end, 3),
                        "media_duration": round(sub_end - sub_start, 3),
                        "timeline_start": tl_start,
                        "timeline_end": tl_end,
                        "timeline_duration": tl_dur,
                        "direction": seg.get("direction", ""),
                        "confidence": seg.get("confidence", 0.0)
                    })
        return results

    def _get_clip_path(self, clip: Any) -> str:
        c_data = clip.data if isinstance(clip.data, dict) else {}
        path = c_data.get("reader", {}).get("path") or ""
        if not path and c_data.get("file_id"):
            from classes.query import File
            try:
                f = File.get(id=c_data.get("file_id"))
                if f:
                    path = f.absolute_path()
            except Exception:
                pass
        return path
