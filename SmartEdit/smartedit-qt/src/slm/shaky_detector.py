"""
@file
@brief Shaky Footage Detection and Labeling service for SmartEdit timeline.
@author SmartEdit Team
"""

import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional

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
    and non-destructively places visible warning label clips and markers.
    """

    def __init__(self, video_analyzer: Optional[VideoAnalyzer] = None):
        self.video_analyzer = video_analyzer or VideoAnalyzer()
        self.last_transaction_id: Optional[str] = None
        self.last_created_clip_ids: List[str] = []
        self.last_created_marker_ids: List[str] = []
        self.last_created_layer: Optional[int] = None

    def get_threshold(self, threshold: Optional[float] = None) -> float:
        """Returns the active shake threshold in percentage (0–100%). Default: 50%."""
        return self.video_analyzer.get_effective_threshold(threshold)

    def analyze_timeline_clips(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Analyzes all video clips placed on the timeline.
        Does NOT modify, move, cut, or delete any existing clips.

        Returns:
            List of analysis dicts for all eligible timeline video clips.
        """
        thresh_pct = self.get_threshold(threshold)
        results: List[Dict[str, Any]] = []

        try:
            timeline_clips = Clip.filter()
        except Exception as ex:
            logger.warning(f"Failed to query timeline clips: {ex}")
            timeline_clips = []

        for clip in timeline_clips:
            clip_data = clip.data if isinstance(clip.data, dict) else {}

            # Ignore AI label clips themselves if re-running
            if clip_data.get("ui", {}).get("ai_label") or str(clip_data.get("title", "")).startswith("SHAKY FOOTAGE"):
                continue

            # Check if media has video
            reader = clip_data.get("reader") or {}
            has_video = reader.get("has_video")
            if has_video is False:
                continue

            # Resolve file path
            path = reader.get("path") or ""
            file_id = clip_data.get("file_id") or reader.get("id")
            if (not path or not os.path.isfile(path)) and file_id:
                try:
                    f = File.get(id=file_id)
                    if f:
                        path = f.absolute_path()
                except Exception:
                    pass

            # Duration and position
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

            # Run optical flow shake analysis
            if path and os.path.isfile(path):
                analysis = self.video_analyzer.analyze_shaky_footage(path, threshold=thresh_pct)
            else:
                # Fallback for placeholder clips in tests
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

        # Collect occupied layers (ignore existing AI label clips)
        occupied_layers = set()
        for c in all_clips:
            c_data = c.data if isinstance(c.data, dict) else {}
            if not c_data.get("ui", {}).get("ai_label") and not str(c_data.get("title", "")).startswith("SHAKY FOOTAGE"):
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

        # Look for existing unused track strictly above all occupied tracks
        candidates_above = [
            n for n in existing_track_numbers
            if n > max_occupied and n not in occupied_layers
        ]

        if candidates_above:
            # Use the topmost unused track
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
            # Top layer is occupied (or no unused tracks above clips exist).
            # Automatically create the next unused layer above the highest existing track.
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

    def generate_warning_image(self, shake_percentage: float, classification: str) -> str:
        """
        Generates a visible warning-style PNG indicator asset for the label clip.
        Uses high-contrast 1920x1080 transparent ARGB layout with amber/red badge.
        Returns the absolute path to the generated PNG.
        """
        pct_int = int(round(shake_percentage))
        out_dir = os.path.join(info.USER_PATH, "ai_labels")
        os.makedirs(out_dir, exist_ok=True)
        png_filename = f"shaky_warning_{pct_int}.png"
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

                # 1. Main container card at top center
                card = QRectF(410, 50, 1100, 120)
                p.setBrush(QColor(21, 27, 38, 240))
                p.setPen(QPen(QColor(231, 76, 60), 4))
                p.drawRoundedRect(card, 16, 16)

                # 2. Caution Triangle Icon
                triangle = QPainterPath()
                triangle.moveTo(460, 134)
                triangle.lineTo(495, 72)
                triangle.lineTo(530, 134)
                triangle.closeSubpath()
                p.setBrush(QColor(243, 156, 18))
                p.setPen(QPen(QColor(255, 255, 255), 2))
                p.drawPath(triangle)

                # Exclamation inside triangle
                p.setPen(QPen(QColor(21, 27, 38), 5))
                p.drawLine(QPointF(495, 90), QPointF(495, 114))
                p.setBrush(QColor(21, 27, 38))
                p.drawEllipse(QPointF(495, 124), 3.5, 3.5)

                # 3. Main Title
                font_title = QFont("Segoe UI", 28, QFont.Bold)
                p.setFont(font_title)
                p.setPen(QColor(255, 255, 255))
                p.drawText(QRectF(555, 65, 750, 45), Qt.AlignLeft | Qt.AlignVCenter, f"SHAKY FOOTAGE – {pct_int}%")

                # 4. Subtitle
                font_sub = QFont("Segoe UI", 14, QFont.DemiBold)
                p.setFont(font_sub)
                p.setPen(QColor(255, 118, 117))
                p.drawText(QRectF(555, 112, 750, 32), Qt.AlignLeft | Qt.AlignVCenter, f"Classification: {classification} (Camera Shake Exceeds Threshold)")

                # 5. Score Pill Badge on Right
                pill = QRectF(1340, 80, 140, 56)
                grad = QLinearGradient(pill.topLeft(), pill.bottomRight())
                grad.setColorAt(0.0, QColor(231, 76, 60))
                grad.setColorAt(1.0, QColor(192, 57, 43))
                p.setBrush(grad)
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(pill, 28, 28)

                font_badge = QFont("Segoe UI", 24, QFont.Bold)
                p.setFont(font_badge)
                p.setPen(QColor(255, 255, 255))
                p.drawText(pill, Qt.AlignCenter, f"{pct_int}%")

                p.end()
                img.save(png_path, "PNG")
                rendered = True
        except Exception as ex:
            logger.warning(f"QImage rendering for warning PNG failed: {ex}")

        if not rendered and not os.path.exists(png_path):
            # Fallback valid 64x64 PNG if Qt GUI is absent
            import struct, zlib
            raw_data = b"".join(b"\x00" + b"\xe7\x4c\x3c\xff" * 64 for _ in range(64))
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

    def generate_warning_svg(self, shake_percentage: float, classification: str) -> str:
        """
        Generates a visible warning-style SVG visual indicator asset for the label clip.
        Displays 'SHAKY FOOTAGE – [percentage]%' with an amber/red warning badge.
        """
        pct_int = int(round(shake_percentage))
        out_dir = os.path.join(info.USER_PATH, "ai_labels")
        os.makedirs(out_dir, exist_ok=True)
        svg_filename = f"shaky_warning_{pct_int}.svg"
        svg_path = os.path.join(out_dir, svg_filename)

        # SVG markup with high-contrast warning design
        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="warnGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#e74c3c" />
      <stop offset="100%" stop-color="#c0392b" />
    </linearGradient>
    <filter id="badgeShadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
  </defs>
  <!-- Warning Banner Overlay at Top Center -->
  <g transform="translate(410, 50)" filter="url(#badgeShadow)">
    <rect x="0" y="0" width="1100" height="110" rx="16" ry="16" fill="#151b26" fill-opacity="0.92" stroke="#e74c3c" stroke-width="3.5"/>
    
    <!-- Warning Icon Triangle -->
    <path d="M 60 82 L 95 24 L 130 82 Z" fill="#f39c12" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>
    <line x1="95" y1="42" x2="95" y2="65" stroke="#151b26" stroke-width="5" stroke-linecap="round"/>
    <circle cx="95" cy="74" r="3.5" fill="#151b26"/>
    
    <!-- Text Labels -->
    <text x="160" y="54" fill="#ffffff" font-family="'Segoe UI', Roboto, sans-serif" font-size="32" font-weight="900" letter-spacing="2">SHAKY FOOTAGE – {pct_int}%</text>
    <text x="160" y="86" fill="#ff7675" font-family="'Segoe UI', Roboto, sans-serif" font-size="19" font-weight="600">Classification: {classification} (Camera Shake Exceeds Threshold)</text>
    
    <!-- Score Pill Badge -->
    <rect x="910" y="28" width="150" height="54" rx="27" ry="27" fill="url(#warnGrad)"/>
    <text x="985" y="64" fill="#ffffff" font-family="'Segoe UI', Roboto, sans-serif" font-size="24" font-weight="900" text-anchor="middle">{pct_int}%</text>
  </g>
</svg>"""

        try:
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
        except Exception as ex:
            logger.error(f"Error writing warning SVG ({svg_path}): {ex}")

        return svg_path

    def label_shaky_clips(
        self,
        shaky_clips: List[Dict[str, Any]],
        target_layer: int
    ) -> List[Clip]:
        """
        Places a corresponding warning label clip and marker on target_layer
        aligned with the exact time range (position and duration) of each shaky clip.
        Preserves the original clips intact.
        """
        app = _safe_app()
        created_clips: List[Clip] = []
        self.last_created_clip_ids = []
        self.last_created_marker_ids = []
        self.last_created_layer = target_layer

        for item in shaky_clips:
            shake_pct = item["shake_percentage"]
            pct_int = int(round(shake_pct))
            classification = item["classification"]
            title_text = f"SHAKY FOOTAGE – {pct_int}%"

            # 1. Generate warning badge visual indicator PNG (fully supported by libsmartedit QtImageReader)
            img_path = self.generate_warning_image(shake_pct, classification)

            pos = float(item["position"])
            dur = float(item["duration"])

            # 2. Register/retrieve File entry for project consistency
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
                        "duration": dur,
                        "ui": {"ai_label": True}
                    }
                    file_obj.save()
            except Exception as f_ex:
                logger.warning(f"Could not register File for label image: {f_ex}")

            # 3. Build Clip data structure using smartedit.Clip(img_path)
            clip_dict: Dict[str, Any] = {}
            try:
                import smartedit
                c = smartedit.Clip(img_path)
                clip_dict = json.loads(c.Json())
            except Exception:
                clip_dict = {}

            clip_dict["position"] = pos
            clip_dict["start"] = 0.0
            clip_dict["end"] = dur
            clip_dict["duration"] = dur
            clip_dict["layer"] = target_layer
            clip_dict["title"] = title_text
            if file_obj and getattr(file_obj, "id", None):
                clip_dict["file_id"] = file_obj.id

            clip_dict.setdefault("ui", {})
            clip_dict["ui"].update({
                "ai_label": True,
                "label_type": "shaky_footage",
                "shake_percentage": pct_int,
                "classification": classification,
                "target_clip_id": item["clip_id"]
            })

            # Save clip to project store
            label_clip = Clip()
            label_clip.data = clip_dict
            label_clip.save()

            created_clips.append(label_clip)
            if label_clip.id:
                self.last_created_clip_ids.append(label_clip.id)

            # 3. Add timeline Marker at clip start timestamp
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
                    "position": pos,
                    "label": title_text,
                    "color": "#e74c3c",
                    "ui": {
                        "ai_label": True,
                        "label_type": "shaky_footage",
                        "target_clip_id": item["clip_id"]
                    }
                }
                marker.save()
                if marker.id:
                    self.last_created_marker_ids.append(marker.id)
            except Exception as mex:
                logger.warning(f"Could not add timeline marker for shaky clip: {mex}")

        return created_clips

    def detect_and_label_timeline(self, threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes the full shaky footage detection and labeling workflow.
        - Analyzes all video clips on timeline
        - Calculates 0-100% shake score
        - If none detected: returns 'No shaky footage detected.'
        - If detected: finds topmost unused layer, adds 'SHAKY FOOTAGE – XX%' label clips and markers
        - Groups all operations into an atomic transaction for 1-click Undo.
        """
        app = _safe_app()
        window = getattr(app, "window", None) if app else None

        # 1. Analyze clips
        analysis_results = self.analyze_timeline_clips(threshold=threshold)
        shaky_clips = [c for c in analysis_results if c["is_shaky"]]

        if not shaky_clips:
            return {
                "success": True,
                "detected_count": 0,
                "message": "No shaky footage detected.",
                "clips": [],
                "labeled_layer": None
            }

        # 2. Begin atomic transaction for single-step Undo
        transaction_id = str(uuid.uuid4())
        self.last_transaction_id = transaction_id
        if app and hasattr(app, "updates") and app.updates:
            app.updates.transaction_id = transaction_id

        try:
            # 3. Find topmost unused layer above all existing tracks/clips
            target_layer = self.find_or_create_top_unused_layer()

            # 4. Place labels aligned to shaky clips
            created_clips = self.label_shaky_clips(shaky_clips, target_layer)

        finally:
            if app and hasattr(app, "updates") and app.updates:
                app.updates.transaction_id = None

        # 5. Refresh timeline UI
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass

        track_display_num = target_layer // 1000000
        msg = f"Detected {len(shaky_clips)} shaky clip(s). Labeled on Track {track_display_num}."

        return {
            "success": True,
            "detected_count": len(shaky_clips),
            "labeled_layer": target_layer,
            "clips": shaky_clips,
            "transaction_id": transaction_id,
            "message": msg
        }

    def undo_shaky_labels(self) -> bool:
        """
        Removes all AI-generated shaky labels and markers.
        Uses SmartEdit's undo system if available, with explicit cleanup fallback.
        """
        app = _safe_app()
        window = getattr(app, "window", None) if app else None
        success = False

        # Attempt atomic undo first
        if app and hasattr(app, "updates") and app.updates and self.last_transaction_id:
            try:
                app.updates.undo()
                success = True
            except Exception as ex:
                logger.warning(f"Atomic undo failed: {ex}")

        # Fallback explicit cleanup if needed
        try:
            all_clips = Clip.filter()
            for c in all_clips:
                c_data = c.data if isinstance(c.data, dict) else {}
                if c_data.get("ui", {}).get("ai_label") or str(c_data.get("title", "")).startswith("SHAKY FOOTAGE"):
                    c.delete()
                    success = True

            all_markers = Marker.filter()
            for m in all_markers:
                m_data = m.data if isinstance(m.data, dict) else {}
                if m_data.get("ui", {}).get("ai_label") or str(m_data.get("label", "")).startswith("SHAKY FOOTAGE"):
                    m.delete()
                    success = True

            all_files = File.filter()
            for f in all_files:
                f_data = f.data if isinstance(f.data, dict) else {}
                if f_data.get("ui", {}).get("ai_label") or "ai_labels" in str(f_data.get("path", "")):
                    f.delete()
                    success = True
        except Exception as cex:
            logger.warning(f"Explicit cleanup failed: {cex}")

        self.last_created_clip_ids = []
        self.last_created_marker_ids = []
        self.last_transaction_id = None

        # Refresh timeline UI
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass

        return success
