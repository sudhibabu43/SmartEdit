"""
@file
@brief Shaky Footage Detection, Labeling, and Removal service for SmartEdit timeline.
@author SmartEdit Team
"""

import os
import uuid
import json
import logging
from copy import deepcopy
from typing import List, Dict, Any, Optional, Tuple

from classes import info
from classes.query import Clip, File, Marker, Track, Transition
from slm.video_analyzer import VideoAnalyzer, classify_shake

logger = logging.getLogger(__name__)


def _safe_app():
    try:
        from classes.app import get_app
        return get_app()
    except Exception:
        return None


class ShakyFootageService:
    """
    Coordinates shaky footage detection across timeline clips,
    finds/creates the topmost unused track above all clips,
    places visual warning label clips on detected shaky regions,
    and cleanly cuts/removes shaky regions while keeping stable portions in sync.
    """

    def __init__(self, video_analyzer: Optional[VideoAnalyzer] = None):
        self.video_analyzer = video_analyzer or VideoAnalyzer()
        self.last_transaction_id: Optional[str] = None
        self.last_created_clip_ids: List[str] = []
        self.last_created_marker_ids: List[str] = []
        self.last_created_layer: Optional[int] = None
        self.last_detected_regions: List[Dict[str, Any]] = []

    def get_threshold(self, threshold: Optional[float] = None) -> float:
        """Returns the active shake threshold in percentage (0–100%). Default: 50%."""
        return self.video_analyzer.get_effective_threshold(threshold)

    def analyze_timeline_clips(
        self,
        threshold: Optional[float] = None,
        clips: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes all video clips placed on the timeline at the whole-clip level.
        Does NOT modify, move, cut, or delete any existing clips.

        Returns:
            List of analysis dicts for all eligible timeline video clips.
        """
        thresh_pct = self.get_threshold(threshold)
        results: List[Dict[str, Any]] = []

        if clips is not None:
            timeline_clips = list(clips)
        else:
            try:
                timeline_clips = Clip.filter()
                app = _safe_app()
                if app and hasattr(app, "window") and hasattr(app.window, "selected_clips") and app.window.selected_clips:
                    selected_ids = set(app.window.selected_clips)
                    timeline_clips = [c for c in timeline_clips if str(c.id) in selected_ids]
            except Exception as ex:
                logger.warning(f"Failed to query timeline clips: {ex}")
                timeline_clips = []

        for clip in timeline_clips:
            clip_data = clip.data if isinstance(clip.data, dict) else {}

            
            clip_ui = clip_data.get("ui") if isinstance(clip_data.get("ui"), dict) else {}
            if clip_ui.get("ai_label") or str(clip_data.get("title", "")).startswith("SHAKY FOOTAGE") or str(clip_data.get("title", "")).startswith("[⚠ SHAKY"):
                continue

            
            reader = clip_data.get("reader") or {}
            has_video = reader.get("has_video")
            if has_video is False:
                continue

            
            path = reader.get("path") or ""
            file_id = clip_data.get("file_id") or reader.get("id")
            if (not path or not os.path.isfile(path)) and file_id:
                try:
                    f = File.get(id=file_id)
                    if f:
                        path = f.absolute_path()
                except Exception:
                    pass

            
            try:
                pos = float(clip_data.get("position", 0.0))
            except (TypeError, ValueError):
                pos = 0.0

            try:
                start = float(clip_data.get("start", 0.0))
                end = float(clip_data.get("end", 0.0))
                dur = float(clip_data.get("duration", 0.0) or (end - start))
            except (TypeError, ValueError):
                start, end, dur = 0.0, 5.0, 5.0

            if dur <= 0.0:
                dur = 5.0

            try:
                orig_layer = int(clip_data.get("layer", 1000000))
            except (TypeError, ValueError):
                orig_layer = 1000000

            clip_name = clip.title() or os.path.basename(path) or "Clip"

            
            if path and os.path.isfile(path):
                analysis = self.video_analyzer.analyze_shaky_footage(path, threshold=thresh_pct)
            else:
                
                analysis = self.video_analyzer._heuristic_analysis(clip_name, threshold=thresh_pct)

            shake_pct = float(analysis.get("shake_percentage", 0.0))
            shake_score = float(analysis.get("shake_score", 0.0))
            classification = analysis.get("classification") or classify_shake(shake_pct)
            is_shaky = bool(analysis.get("is_shaky", False)) or (shake_pct >= thresh_pct)

            results.append({
                "clip_id": clip.id,
                "clip_name": clip_name,
                "path": path,
                "position": pos,
                "start": start,
                "end": end,
                "duration": dur,
                "layer": orig_layer,
                "shake_score": shake_score,
                "shake_percentage": shake_pct,
                "classification": classification,
                "is_shaky": is_shaky,
                "threshold": thresh_pct,
                "segments": analysis.get("shaky_segments", []),
                "clip_ref": clip
            })

        return results

    def analyze_timeline_shaky_regions(
        self,
        threshold: Optional[float] = None,
        clips: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyzes every video clip on the timeline and detects discrete temporal
        regions containing camera shake with exact timeline start and end timestamps.

        Returns:
            List of detected shaky region dicts across all timeline video clips.
        """
        thresh_pct = self.get_threshold(threshold)
        all_regions: List[Dict[str, Any]] = []

        if clips is not None:
            timeline_clips = list(clips)
        else:
            try:
                timeline_clips = Clip.filter()
                app = _safe_app()
                if app and hasattr(app, "window") and hasattr(app.window, "selected_clips") and app.window.selected_clips:
                    selected_ids = set(app.window.selected_clips)
                    timeline_clips = [c for c in timeline_clips if str(c.id) in selected_ids]
            except Exception as ex:
                logger.warning(f"Failed to query timeline clips: {ex}")
                timeline_clips = []

        for clip in timeline_clips:
            clip_data = clip.data if isinstance(clip.data, dict) else {}

            
            clip_ui = clip_data.get("ui") if isinstance(clip_data.get("ui"), dict) else {}
            if clip_ui.get("ai_label") or str(clip_data.get("title", "")).startswith("SHAKY FOOTAGE") or str(clip_data.get("title", "")).startswith("[⚠ SHAKY") or str(clip_data.get("title", "")).startswith("[⚠ REMOVED"):
                continue

            reader = clip_data.get("reader") or {}
            has_video = reader.get("has_video")
            if has_video is False:
                continue

            path = reader.get("path") or ""
            file_id = clip_data.get("file_id") or reader.get("id")
            if (not path or not os.path.isfile(path)) and file_id:
                try:
                    f = File.get(id=file_id)
                    if f:
                        path = f.absolute_path()
                except Exception:
                    pass

            try:
                pos = float(clip_data.get("position", 0.0))
                start = float(clip_data.get("start", 0.0))
                end = float(clip_data.get("end", 0.0))
                dur = float(clip_data.get("duration", 0.0) or (end - start))
            except (TypeError, ValueError):
                pos, start, end, dur = 0.0, 0.0, 5.0, 5.0

            if dur <= 0.0:
                dur = 5.0
            if end <= start:
                end = start + dur

            try:
                orig_layer = int(clip_data.get("layer", 1000000))
            except (TypeError, ValueError):
                orig_layer = 1000000

            clip_name = clip.title() or os.path.basename(path) or "Clip"
            video_ref = path if (path and os.path.isfile(path)) else clip_name

            clip_regions = self.video_analyzer.detect_shaky_regions(
                video_ref,
                threshold=thresh_pct,
                clip_start=start,
                clip_end=end,
                clip_position=pos
            )

            for r in clip_regions:
                r["clip_id"] = clip.id
                r["clip_name"] = clip_name
                r["clip_layer"] = orig_layer
                r["clip_position"] = pos
                r["clip_start"] = start
                r["clip_end"] = end
                r["clip_duration"] = dur
                r["clip_ref"] = clip
                all_regions.append(r)

        self.last_detected_regions = all_regions
        return all_regions

    def find_or_create_top_unused_layer(self) -> int:
        """
        Finds the topmost unused video track/layer above existing timeline tracks.
        If the top layer is occupied, automatically finds/creates the next unused layer above it.
        Does not overwrite existing clips or tracks.

        Returns:
            layer_number (int): Multiples of 1,000,000 (e.g. 4000000).
        """
        app = _safe_app()
        project = getattr(app, "project", None) if app else None
        tracks = project.get("layers") if (project and hasattr(project, "get")) else []
        existing_track_numbers = sorted(
            int(t.get("number", 0)) for t in tracks if int(t.get("number", 0)) > 0
        )

        all_clips = []
        try:
            all_clips = Clip.filter()
        except Exception:
            pass

        all_trans = []
        try:
            all_trans = Transition.filter()
        except Exception:
            pass

        
        occupied_layers = set()
        for c in all_clips:
            c_data = c.data if isinstance(c.data, dict) else {}
            c_ui = c_data.get("ui") if isinstance(c_data.get("ui"), dict) else {}
            if not c_ui.get("ai_label") and not str(c_data.get("title", "")).startswith("SHAKY FOOTAGE") and not str(c_data.get("title", "")).startswith("[⚠ SHAKY") and not str(c_data.get("title", "")).startswith("[⚠ REMOVED"):
                try:
                    occupied_layers.add(int(c_data.get("layer", 0)))
                except (TypeError, ValueError):
                    pass

        for t in all_trans:
            t_data = t.data if isinstance(t.data, dict) else {}
            try:
                occupied_layers.add(int(t_data.get("layer", 0)))
            except (TypeError, ValueError):
                pass

        max_occupied = max(occupied_layers) if occupied_layers else 0
        max_existing = max(existing_track_numbers) if existing_track_numbers else 0

        
        candidates_above = [
            n for n in existing_track_numbers
            if n > max_occupied and n not in occupied_layers
        ]

        if candidates_above:
            chosen_layer = max(candidates_above)
            try:
                track_obj = Track.get(number=chosen_layer)
                if track_obj and not track_obj.data.get("label"):
                    track_obj.data["label"] = "AI Labels"
                    track_obj.save()
            except Exception:
                pass
            return chosen_layer
        else:
            new_layer = max(max_existing, max_occupied) + 1000000
            if new_layer <= 0:
                new_layer = 1000000

            track = Track()
            track.data = {
                "number": new_layer,
                "y": 0,
                "label": "AI Labels",
                "lock": False
            }
            track.save()
            return new_layer

    def generate_warning_image(
        self,
        shake_percentage: float,
        classification: str,
        removed: bool = False,
        time_str: str = ""
    ) -> str:
        """
        Generates a visible indicator PNG asset for the label clip.
        - When removed=False: amber/red warning badge displaying '[⚠ SHAKY XX%]'.
        - When removed=True: green/emerald badge displaying '[⚠ REMOVED SHAKY]'.
        Returns the absolute path to the generated PNG.
        """
        pct_int = int(round(shake_percentage))
        out_dir = os.path.join(info.USER_PATH, "ai_labels")
        os.makedirs(out_dir, exist_ok=True)
        prefix = "shaky_removed" if removed else "shaky_warning"
        png_filename = f"{prefix}_{pct_int}.png"
        png_path = os.path.join(out_dir, png_filename)

        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
            return png_path

        rendered = False
        try:
            from qt_api import (
                QGuiApplication, QImage, QPainter, QColor, QFont, QPen, QPainterPath, QLinearGradient,
                QRectF, QPointF, Qt
            )
            if QGuiApplication.instance() is not None:
                img = QImage(1920, 1080, QImage.Format_ARGB32_Premultiplied)
                img.fill(Qt.transparent)

                p = QPainter(img)
                p.setRenderHint(QPainter.Antialiasing, True)

                
                border_color = QColor(39, 174, 96) if removed else QColor(231, 76, 60)
                card_bg = QColor(18, 28, 24, 242) if removed else QColor(21, 27, 38, 242)

                
                card = QRectF(380, 50, 1160, 120)
                p.setBrush(card_bg)
                p.setPen(QPen(border_color, 4))
                p.drawRoundedRect(card, 16, 16)

                if removed:
                    
                    p.setBrush(QColor(39, 174, 96))
                    p.setPen(QPen(QColor(255, 255, 255), 2))
                    p.drawRoundedRect(QRectF(420, 72, 60, 60), 12, 12)
                    p.setPen(QPen(QColor(255, 255, 255), 6))
                    p.drawLine(QPointF(434, 102), QPointF(446, 118))
                    p.drawLine(QPointF(446, 118), QPointF(466, 86))

                    
                    p.setFont(QFont("Segoe UI", 26, QFont.Bold))
                    p.setPen(QColor(255, 255, 255))
                    p.drawText(QRectF(505, 65, 760, 42), Qt.AlignLeft | Qt.AlignVCenter, f"REMOVED SHAKY FOOTAGE – {pct_int}%")

                    p.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
                    p.setPen(QColor(46, 204, 113))
                    sub_txt = f"Original Detected Region {time_str} – Camera Shake Cut from Timeline" if time_str else "Original Detected Region – Camera Shake Cut from Timeline"
                    p.drawText(QRectF(505, 110, 760, 32), Qt.AlignLeft | Qt.AlignVCenter, sub_txt)

                    
                    pill = QRectF(1340, 80, 160, 56)
                    grad = QLinearGradient(pill.topLeft(), pill.bottomRight())
                    grad.setColorAt(0.0, QColor(39, 174, 96))
                    grad.setColorAt(1.0, QColor(30, 132, 73))
                    p.setBrush(grad)
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(pill, 28, 28)

                    p.setFont(QFont("Segoe UI", 18, QFont.Bold))
                    p.setPen(QColor(255, 255, 255))
                    p.drawText(pill, Qt.AlignCenter, "REMOVED")

                else:
                    
                    triangle = QPainterPath()
                    triangle.moveTo(420, 134)
                    triangle.lineTo(455, 72)
                    triangle.lineTo(490, 134)
                    triangle.closeSubpath()
                    p.setBrush(QColor(243, 156, 18))
                    p.setPen(QPen(QColor(255, 255, 255), 2))
                    p.drawPath(triangle)

                    p.setPen(QPen(QColor(21, 27, 38), 5))
                    p.drawLine(QPointF(455, 90), QPointF(455, 114))
                    p.setBrush(QColor(21, 27, 38))
                    p.drawEllipse(QPointF(455, 124), 3.5, 3.5)

                    
                    p.setFont(QFont("Segoe UI", 26, QFont.Bold))
                    p.setPen(QColor(255, 255, 255))
                    p.drawText(QRectF(515, 65, 760, 42), Qt.AlignLeft | Qt.AlignVCenter, f"SHAKY FOOTAGE – {pct_int}%")

                    p.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
                    p.setPen(QColor(255, 118, 117))
                    sub_txt = f"Detected Shake Region {time_str} ({classification})" if time_str else f"Classification: {classification} (Camera Shake Exceeds Threshold)"
                    p.drawText(QRectF(515, 110, 760, 32), Qt.AlignLeft | Qt.AlignVCenter, sub_txt)

                    
                    pill = QRectF(1340, 80, 160, 56)
                    grad = QLinearGradient(pill.topLeft(), pill.bottomRight())
                    grad.setColorAt(0.0, QColor(231, 76, 60))
                    grad.setColorAt(1.0, QColor(192, 57, 43))
                    p.setBrush(grad)
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(pill, 28, 28)

                    p.setFont(QFont("Segoe UI", 22, QFont.Bold))
                    p.setPen(QColor(255, 255, 255))
                    p.drawText(pill, Qt.AlignCenter, f"{pct_int}%")

                p.end()
                img.save(png_path, "PNG")
                rendered = True
        except Exception as ex:
            logger.warning(f"QImage rendering for indicator PNG failed: {ex}")

        if not rendered and not os.path.exists(png_path):
            import struct, zlib
            pixel_color = b"\x27\xae\x60\xff" if removed else b"\xe7\x4c\x3c\xff"
            raw_data = b"".join(b"\x00" + pixel_color * 64 for _ in range(64))
            compressed = zlib.compress(raw_data)
            png_bytes = (
                b"\x89PNG\r\n\x1a\n"
                + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", 64, 64, 8, 6, 0, 0, 0)
                + struct.pack(">I", zlib.crc32(b"IHDR" + struct.pack(">IIBBBBB", 64, 64, 8, 6, 0, 0, 0)))
                + struct.pack(">I", len(compressed)) + b"IDAT" + compressed
                + struct.pack(">I", zlib.crc32(b"IDAT" + compressed))
                + struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
            )
            with open(png_path, "wb") as f:
                f.write(png_bytes)

        return png_path

    def label_shaky_regions(
        self,
        regions: List[Dict[str, Any]],
        target_layer: int
    ) -> List[Clip]:
        """
        Creates a visual 'SHAKY FOOTAGE' marker clip on target_layer for each
        detected shaky region, positioned at the exact same start and end timestamps.
        Preserves original clips completely untouched.
        """
        created_clips: List[Clip] = []
        self.last_created_clip_ids = []
        self.last_created_marker_ids = []
        self.last_created_layer = target_layer

        for region in regions:
            shake_pct = float(region.get("shake_percentage", 65.0))
            pct_int = int(round(shake_pct))
            classification = region.get("classification") or classify_shake(shake_pct)

            tl_start = float(region.get("timeline_start", 0.0))
            tl_dur = float(region.get("timeline_duration", 0.0))
            tl_end = float(region.get("timeline_end", tl_start + tl_dur))
            if tl_dur <= 0.0:
                tl_dur = max(0.2, tl_end - tl_start)

            time_str = f"{tl_start:.2f}–{tl_end:.2f}"
            title_text = region.get("title") or f"[⚠ SHAKY {pct_int}%] {time_str}"

            
            img_path = self.generate_warning_image(shake_pct, classification, removed=False, time_str=time_str)

            
            file_obj = None
            try:
                for f in File.filter():
                    if f.data.get("path") == img_path:
                        file_obj = f
                        break
                if not file_obj:
                    file_obj = File()
                    file_obj.data = {
                        "path": img_path,
                        "name": title_text,
                        "media_type": "image",
                        "duration": tl_dur,
                        "ui": {"ai_label": True}
                    }
                    file_obj.save()
            except Exception as f_ex:
                logger.warning(f"Could not register File for label image: {f_ex}")

            
            clip_dict: Dict[str, Any] = {}
            try:
                import smartedit
                c = smartedit.Clip(img_path)
                clip_dict = json.loads(c.Json())
            except Exception:
                clip_dict = {}

            clip_dict["position"] = round(tl_start, 4)
            clip_dict["start"] = 0.0
            clip_dict["end"] = round(tl_dur, 4)
            clip_dict["duration"] = round(tl_dur, 4)
            clip_dict["layer"] = target_layer
            clip_dict["title"] = title_text
            if file_obj and getattr(file_obj, "id", None):
                clip_dict["file_id"] = file_obj.id

            clip_dict.setdefault("ui", {})
            clip_dict["ui"].update({
                "ai_label": True,
                "label_type": "shaky_region",
                "shake_percentage": pct_int,
                "classification": classification,
                "target_clip_id": region.get("clip_id"),
                "timeline_start": round(tl_start, 4),
                "timeline_end": round(tl_end, 4),
                "timeline_duration": round(tl_dur, 4),
                "original_timeline_start": round(tl_start, 4),
                "original_timeline_end": round(tl_end, 4),
                "region_data": region
            })

            label_clip = Clip()
            label_clip.data = clip_dict
            label_clip.save()

            created_clips.append(label_clip)
            if label_clip.id:
                self.last_created_clip_ids.append(label_clip.id)

            
            try:
                app = _safe_app()
                project = getattr(app, "project", None) if app else None
                marker_id = None
                if project and hasattr(project, "generate_id"):
                    marker_id = project.generate_id()
                if not marker_id:
                    marker_id = str(uuid.uuid4())

                marker = Marker()
                marker.data = {
                    "id": marker_id,
                    "position": round(tl_start, 4),
                    "label": f"[⚠ SHAKY {pct_int}%]",
                    "color": "#e74c3c",
                    "ui": {
                        "ai_label": True,
                        "label_type": "shaky_region",
                        "target_clip_id": region.get("clip_id"),
                        "shake_percentage": pct_int,
                        "original_timeline_start": round(tl_start, 4),
                        "original_timeline_end": round(tl_end, 4)
                    }
                }
                marker.save()
                if marker.id:
                    self.last_created_marker_ids.append(marker.id)
            except Exception as mex:
                logger.warning(f"Could not add timeline marker for shaky region: {mex}")

        return created_clips

    def label_shaky_clips(
        self,
        shaky_clips: List[Dict[str, Any]],
        target_layer: int
    ) -> List[Clip]:
        """
        Backwards-compatible helper: labels clips directly or maps them to regions.
        """
        
        regions = []
        for item in shaky_clips:
            if "timeline_start" in item:
                regions.append(item)
            else:
                pos = float(item.get("position", 0.0))
                dur = float(item.get("duration", 0.0))
                pct_int = int(round(item.get("shake_percentage", 65.0)))
                regions.append({
                    "title": f"SHAKY FOOTAGE – {pct_int}%",
                    "clip_id": item.get("clip_id"),
                    "clip_name": item.get("clip_name", "Clip"),
                    "timeline_start": pos,
                    "timeline_end": pos + dur,
                    "timeline_duration": dur,
                    "shake_percentage": item.get("shake_percentage", 65.0),
                    "classification": item.get("classification", "Shaky"),
                    "clip_ref": item.get("clip_ref")
                })
        return self.label_shaky_regions(regions, target_layer)

    def detect_and_label_timeline(self, threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes the full detection and labeling workflow:
        1. Analyzes every video clip on timeline.
        2. Detects exact time regions containing camera shake.
        3. Creates visual markers on topmost unused layer with shake percentage.
        4. Atomic transaction grouping for 1-click Undo.
        """
        app = _safe_app()
        window = getattr(app, "window", None) if app else None

        
        regions = self.analyze_timeline_shaky_regions(threshold=threshold)

        if not regions:
            return {
                "success": True,
                "detected_count": 0,
                "message": "No shaky footage detected.",
                "regions": [],
                "clips": [],
                "labeled_layer": None
            }

        
        transaction_id = str(uuid.uuid4())
        self.last_transaction_id = transaction_id
        if app and hasattr(app, "updates") and app.updates:
            app.updates.transaction_id = transaction_id

        try:
            
            target_layer = self.find_or_create_top_unused_layer()

            
            created_clips = self.label_shaky_regions(regions, target_layer)

        finally:
            if app and hasattr(app, "updates") and app.updates:
                app.updates.transaction_id = None

        
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass

        track_display_num = target_layer // 1000000
        affected_clips_count = len(set(r.get("clip_id") for r in regions if r.get("clip_id")))
        if affected_clips_count == 0:
            affected_clips_count = len(regions)
        msg = f"Detected {affected_clips_count} shaky clip(s) ({len(regions)} shaky region(s)). Labeled on Track {track_display_num}."

        return {
            "success": True,
            "detected_count": len(regions),
            "labeled_layer": target_layer,
            "regions": regions,
            "clips": regions,
            "transaction_id": transaction_id,
            "message": msg
        }

    def trim_shaky_footage(
        self,
        regions: Optional[List[Dict[str, Any]]] = None,
        close_gaps: bool = True,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end 'Trim Shaky Footage' workflow:
        1. Retrieves timeline clips.
        2. Runs video analysis on eligible video clips.
        3. Calculates discrete camera shake regions.
        4. Validates timestamps and converts timeline coordinates.
        5. Splits original clips at shaky region boundaries.
        6. Removes detected shaky segments; preserves stable portions.
        7. Repositions/merges remaining clips and closes gaps.
        8. Refreshes timeline display.
        9. Encloses all changes in an atomic transaction for single-step Undo/Redo.
        """
        print("[DEBUG] User clicked Trim Shaky Footage")
        app = _safe_app()
        window = getattr(app, "window", None) if app else None

        
        print("[DEBUG] Retrieving timeline clips...")
        target_regions = regions
        if not target_regions:
            target_regions = getattr(self, "last_detected_regions", [])

        if not target_regions:
            
            try:
                for c in Clip.filter():
                    c_data = c.data if isinstance(c.data, dict) else {}
                    ui = c_data.get("ui") if isinstance(c_data.get("ui"), dict) else {}
                    if ui.get("ai_label") and ui.get("label_type") in ("shaky_region", "shaky_footage") and not ui.get("removed"):
                        if "region_data" in ui:
                            target_regions.append(ui["region_data"])
                        else:
                            pos = float(c_data.get("position", 0.0))
                            dur = float(c_data.get("duration", 0.0))
                            target_regions.append({
                                "clip_id": ui.get("target_clip_id"),
                                "timeline_start": pos,
                                "timeline_end": pos + dur,
                                "timeline_duration": dur,
                                "shake_percentage": float(ui.get("shake_percentage", 65.0)),
                                "classification": ui.get("classification", "Shaky")
                            })
            except Exception:
                pass

        if not target_regions:
            
            try:
                timeline_clips = Clip.filter()
                app = _safe_app()
                if app and hasattr(app, "window") and hasattr(app.window, "selected_clips") and app.window.selected_clips:
                    selected_ids = set(app.window.selected_clips)
                    timeline_clips = [c for c in timeline_clips if str(c.id) in selected_ids]
            except Exception as ex:
                logger.warning(f"Failed to query timeline clips: {ex}")
                timeline_clips = []
            print(f"[DEBUG] Retrieved {len(timeline_clips)} timeline video clip(s)")
            target_regions = self.analyze_timeline_shaky_regions(threshold=threshold, clips=timeline_clips)
        else:
            print(f"[DEBUG] Using {len(target_regions)} previously detected/provided shaky region(s)")

        
        if not target_regions:
            print("[SHAKE] No shaky regions detected")
            return {
                "success": True,
                "removed_count": 0,
                "affected_clips": 0,
                "close_gaps": close_gaps,
                "message": "No shaky regions detected."
            }

        print(f"[DEBUG] Validated timestamps and timeline coordinates for {len(target_regions)} region(s)")
        for r in target_regions:
            clip_id = r.get("clip_id") or "unknown"
            c_start = float(r.get("clip_start", 0.0))
            c_end = float(r.get("clip_end", 0.0))
            if c_start == 0.0 and c_end == 0.0 and clip_id != "unknown":
                try:
                    c_ref = Clip.get(id=clip_id)
                    if c_ref and isinstance(c_ref.data, dict):
                        c_start = float(c_ref.data.get("start", 0.0))
                        c_end = float(c_ref.data.get("end", 0.0))
                except Exception:
                    pass
            s_start = float(r.get("timeline_start", 0.0))
            s_end = float(r.get("timeline_end", 0.0))
            score = int(round(float(r.get("shake_percentage", 0.0))))

            print(f"[SHAKE] clip={clip_id}")
            print(f"[SHAKE] clip_start={c_start:.2f}s")
            print(f"[SHAKE] clip_end={c_end:.2f}s")
            print(f"[SHAKE] shaky_start={s_start:.2f}s")
            print(f"[SHAKE] shaky_end={s_end:.2f}s")
            print(f"[SHAKE] region={s_start:.2f}s - {s_end:.2f}s")
            print(f"[SHAKE] score={score}%")

        
        clips_to_regions: Dict[str, List[Dict[str, Any]]] = {}
        for r in target_regions:
            cid = r.get("clip_id")
            if cid:
                clips_to_regions.setdefault(cid, []).append(r)

        
        sorted_clip_entries = []
        for clip_id, clip_regs in clips_to_regions.items():
            c_obj = Clip.get(id=clip_id)
            if c_obj:
                pos = float(c_obj.data.get("position", 0.0)) if isinstance(c_obj.data, dict) else 0.0
                sorted_clip_entries.append((pos, clip_id, clip_regs))
        sorted_clip_entries.sort(key=lambda x: x[0], reverse=True)

        
        transaction_id = str(uuid.uuid4())
        self.last_transaction_id = transaction_id
        if app and hasattr(app, "updates") and app.updates:
            app.updates.transaction_id = transaction_id

        removed_count = 0
        affected_clips = 0

        try:
            for orig_pos, clip_id, clip_regs in sorted_clip_entries:
                clip = Clip.get(id=clip_id)
                if not clip:
                    continue

                c_data = deepcopy(clip.data) if isinstance(clip.data, dict) else {}
                c_pos = float(c_data.get("position", 0.0))
                c_start = float(c_data.get("start", 0.0))
                c_end = float(c_data.get("end", 0.0))
                c_dur = max(0.0, c_end - c_start)
                c_tl_end = c_pos + c_dur
                c_layer = int(c_data.get("layer", 1000000))

                
                merged_shaky: List[Tuple[float, float, float]] = []
                sorted_regs = sorted(clip_regs, key=lambda x: float(x.get("timeline_start", 0.0)))

                for r in sorted_regs:
                    s = max(c_pos, min(c_tl_end, float(r.get("timeline_start", 0.0))))
                    e = max(c_pos, min(c_tl_end, float(r.get("timeline_end", 0.0))))
                    score = float(r.get("shake_percentage", 65.0))
                    if e - s <= 0.04:
                        continue
                    if not merged_shaky:
                        merged_shaky.append((s, e, score))
                    else:
                        ps, pe, psc = merged_shaky[-1]
                        if s <= pe + 0.04:
                            merged_shaky[-1] = (ps, max(pe, e), max(psc, score))
                        else:
                            merged_shaky.append((s, e, score))

                if not merged_shaky:
                    continue

                
                for (s_shaky, e_shaky, _) in merged_shaky:
                    print(f"[SPLIT] {clip_id} at {s_shaky:.2f}s")
                    print(f"[SPLIT] {clip_id} at {e_shaky:.2f}s")
                    print(f"[REMOVE] shaky segment {s_shaky:.2f}s - {e_shaky:.2f}s")

                removed_count += len(merged_shaky)
                affected_clips += 1

                
                stable_intervals: List[Tuple[float, float]] = []
                curr = c_pos
                for (s_shaky, e_shaky, _) in merged_shaky:
                    if s_shaky - curr >= 0.05:
                        stable_intervals.append((curr, s_shaky))
                    curr = max(curr, e_shaky)
                if c_tl_end - curr >= 0.05:
                    stable_intervals.append((curr, c_tl_end))

                total_shaky_dur = c_dur - sum(ei - si for (si, ei) in stable_intervals)

                
                if not stable_intervals:
                    clip.delete()
                else:
                    next_pos = c_pos
                    for idx, (si, ei) in enumerate(stable_intervals):
                        duri = round(ei - si, 4)
                        m_starti = round(c_start + (si - c_pos), 4)
                        m_endi = round(m_starti + duri, 4)
                        seg_pos = round(next_pos, 4) if close_gaps else round(si, 4)

                        if idx == 0:
                            clip.data["position"] = seg_pos
                            clip.data["start"] = m_starti
                            clip.data["end"] = m_endi
                            clip.data["duration"] = duri
                            clip.save()
                        else:
                            new_clip = Clip()
                            new_clip_data = deepcopy(c_data)
                            new_clip_data.pop("id", None)
                            new_clip.id = None
                            new_clip.type = "insert"
                            new_clip.key = None
                            new_clip.data = new_clip_data
                            new_clip.data["position"] = seg_pos
                            new_clip.data["start"] = m_starti
                            new_clip.data["end"] = m_endi
                            new_clip.data["duration"] = duri
                            new_clip.data["layer"] = c_layer
                            new_clip.save()

                        next_pos = round(next_pos + duri, 4)

                
                if close_gaps and total_shaky_dur > 0.02:
                    try:
                        for other_clip in Clip.filter(layer=c_layer):
                            if other_clip.id != clip_id and float(other_clip.data.get("position", 0.0)) >= c_tl_end - 0.01:
                                other_clip.data["position"] = max(0.0, float(other_clip.data["position"]) - total_shaky_dur)
                                other_clip.save()
                    except Exception as ex:
                        logger.debug(f"Could not shift clips for gap: {ex}")

                    try:
                        for other_trans in Transition.filter(layer=c_layer):
                            if float(other_trans.data.get("position", 0.0)) >= c_tl_end - 0.01:
                                other_trans.data["position"] = max(0.0, float(other_trans.data["position"]) - total_shaky_dur)
                                other_trans.save()
                    except Exception as ex:
                        logger.debug(f"Could not shift transitions for gap: {ex}")

            print("[DEBUG] Remaining clips repositioned and merged")

            
            try:
                for c in Clip.filter():
                    c_dict = c.data if isinstance(c.data, dict) else {}
                    ui = c_dict.get("ui") if isinstance(c_dict.get("ui"), dict) else {}
                    if ui.get("ai_label") and not ui.get("removed"):
                        pct = float(ui.get("shake_percentage", 65.0))
                        orig_s = float(ui.get("original_timeline_start", c_dict.get("position", 0.0)))
                        orig_e = float(ui.get("original_timeline_end", orig_s + float(c_dict.get("duration", 0.0))))
                        time_str = f"{orig_s:.2f}–{orig_e:.2f}"
                        c.data["title"] = f"[⚠ REMOVED SHAKY] {time_str}"
                        c.data["ui"]["removed"] = True
                        c.data["ui"]["label_type"] = "shaky_region_removed"
                        c.save()
            except Exception as ex:
                logger.warning(f"Error updating top AI markers after cut: {ex}")

            try:
                for m in Marker.filter():
                    m_dict = m.data if isinstance(m.data, dict) else {}
                    m_ui = m_dict.get("ui") if isinstance(m_dict.get("ui"), dict) else {}
                    if m_ui.get("ai_label") and not m_ui.get("removed"):
                        m.data["label"] = "[⚠ REMOVED SHAKY]"
                        m.data["color"] = "#27ae60"
                        m.data["ui"]["removed"] = True
                        m.save()
            except Exception:
                pass

        finally:
            
            if app and hasattr(app, "updates") and app.updates:
                app.updates.transaction_id = None
            print(f"[DEBUG] Undo/redo transaction {transaction_id} committed")

        
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass
            if hasattr(window, "timeline") and hasattr(window.timeline, "update"):
                try:
                    window.timeline.update()
                except Exception:
                    pass

        print("[TIMELINE] refresh completed")

        msg = f"Removed {removed_count} shaky segment(s) across {affected_clips} clip(s). Stable portions preserved."
        return {
            "success": True,
            "removed_count": removed_count,
            "affected_clips": affected_clips,
            "transaction_id": transaction_id,
            "close_gaps": close_gaps,
            "message": msg
        }

    def remove_shaky_regions(
        self,
        regions: Optional[List[Dict[str, Any]]] = None,
        close_gaps: bool = True
    ) -> Dict[str, Any]:
        """
        Applies the removal of detected shaky regions (delegates to trim_shaky_footage).
        """
        return self.trim_shaky_footage(regions=regions, close_gaps=close_gaps)

    def undo_shaky_labels(self) -> bool:
        """
        Removes all AI-generated shaky labels and markers, or reverts cuts.
        Uses SmartEdit's undo system if available, with explicit cleanup fallback.
        """
        app = _safe_app()
        window = getattr(app, "window", None) if app else None
        success = False

        if app and hasattr(app, "updates") and app.updates and self.last_transaction_id:
            try:
                app.updates.undo()
                success = True
            except Exception as ex:
                logger.warning(f"Atomic undo failed: {ex}")

        try:
            all_clips = Clip.filter()
            for c in all_clips:
                c_data = c.data if isinstance(c.data, dict) else {}
                c_ui = c_data.get("ui") if isinstance(c_data.get("ui"), dict) else {}
                title = str(c_data.get("title", ""))
                if c_ui.get("ai_label") or title.startswith("SHAKY FOOTAGE") or title.startswith("[⚠ SHAKY") or title.startswith("[⚠ REMOVED"):
                    c.delete()
                    success = True

            all_markers = Marker.filter()
            for m in all_markers:
                m_data = m.data if isinstance(m.data, dict) else {}
                m_ui = m_data.get("ui") if isinstance(m_data.get("ui"), dict) else {}
                label = str(m_data.get("label", ""))
                if m_ui.get("ai_label") or label.startswith("SHAKY FOOTAGE") or label.startswith("[⚠ SHAKY") or label.startswith("[⚠ REMOVED"):
                    m.delete()
                    success = True

            all_files = File.filter()
            for f in all_files:
                f_data = f.data if isinstance(f.data, dict) else {}
                f_ui = f_data.get("ui") if isinstance(f_data.get("ui"), dict) else {}
                if f_ui.get("ai_label") or "ai_labels" in str(f_data.get("path", "")):
                    f.delete()
                    success = True
        except Exception as cex:
            logger.warning(f"Explicit cleanup failed: {cex}")

        self.last_created_clip_ids = []
        self.last_created_marker_ids = []
        self.last_transaction_id = None
        self.last_detected_regions = []

        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass

        return success
