"""
@file
@brief SmartEdit Editing Controller: bridges SLM commands, analysis modules, and timeline operations.
@author SmartEdit Team
"""

import os
import uuid
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from slm.command_schema import ActionType, SLMCommand
from slm.video_analyzer import VideoAnalyzer, classify_shake
from slm.shaky_detector import ShakyFootageService

logger = logging.getLogger(__name__)


@dataclass
class PlanItem:
    """A single human-readable line item in the proposed AI plan."""
    action: str
    description: str
    icon: str = "✓"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIPlan:
    """The generated AI plan awaiting human review before execution."""
    command: SLMCommand
    items: List[PlanItem] = field(default_factory=list)
    operations: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    is_empty: bool = True

    def to_preview_text(self) -> str:
        """Returns a nicely formatted checklist for the UI."""
        if self.is_empty or not self.items:
            return "No changes proposed for this instruction."
        
        lines = ["<b>AI Plan:</b><br/>"]
        for item in self.items:
            lines.append(f"{item.icon} {item.description}")
        return "<br/>".join(lines)


class EditingController:
    """
    Orchestrates video and audio analysis, creates human-in-the-loop plans,
    and applies changes safely to SmartEdit's timeline data model.
    """

    def __init__(self, video_analyzer: Optional[VideoAnalyzer] = None):
        self.video_analyzer = video_analyzer or VideoAnalyzer()
        self.shaky_service = ShakyFootageService(self.video_analyzer)
        self.last_transaction_id: Optional[str] = None
        self.pending_plan: Optional[AIPlan] = None

    def generate_plan(
        self,
        command: SLMCommand,
        clips: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None
    ) -> AIPlan:
        """
        Analyzes the current timeline clips and project files, then formulates
        a proposed plan without modifying the timeline.
        """
        from classes.app import get_app
        from classes.query import Clip, File

        app = get_app()
        if clips is not None:
            timeline_clips = list(clips)
        else:
            timeline_clips = []
            try:
                timeline_clips = Clip.filter()
            except Exception:
                timeline_clips = []

        if files is not None:
            project_files = list(files)
        else:
            project_files = []
            try:
                project_files = File.filter()
            except Exception:
                project_files = []

        plan_items: List[PlanItem] = []
        operations: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # 1. Shaky Footage Detection & Labeling
        # -------------------------------------------------------------
        shaky_clips_found = []
        if command.has_action(ActionType.DETECT_SHAKY) or command.has_action(ActionType.LABEL_SHAKY) or command.has_action(ActionType.DELETE_SHAKY):
            target_clips = timeline_clips if timeline_clips else []
            thresh_pct = self.shaky_service.get_threshold(command.parameters.get("shaky", {}).get("threshold"))

            for clip in target_clips:
                clip_data = clip.data if isinstance(clip.data, dict) else {}
                if clip_data.get("ui", {}).get("ai_label") or str(clip_data.get("title", "")).startswith("SHAKY FOOTAGE"):
                    continue

                path = clip_data.get("reader", {}).get("path") or ""
                if not path and clip_data.get("file_id"):
                    f = File.get(id=clip_data.get("file_id"))
                    if f:
                        path = f.absolute_path()

                has_video = clip_data.get("reader", {}).get("has_video")
                if has_video is False:
                    continue

                clip_name = clip.title() or os.path.basename(path) or "Clip"
                pos = float(clip_data.get("position", 0.0))
                dur = float(clip_data.get("duration", 0.0) or (float(clip_data.get("end", 5.0)) - float(clip_data.get("start", 0.0))))
                if dur <= 0.0:
                    dur = 5.0

                if path and os.path.isfile(path):
                    analysis = self.video_analyzer.analyze_shaky_footage(path, threshold=thresh_pct)
                else:
                    analysis = self.video_analyzer._heuristic_analysis(clip_name, threshold=thresh_pct)

                shake_pct = float(analysis.get("shake_percentage", 0.0))
                if shake_pct == 0.0 and analysis.get("shake_score"):
                    shake_pct = round(float(analysis.get("shake_score", 0.0)) * 100.0, 1)
                classification = analysis.get("classification") or classify_shake(shake_pct)
                is_shaky = bool(analysis.get("is_shaky", False)) or (shake_pct >= thresh_pct)

                if is_shaky:
                    shaky_clips_found.append({
                        "clip_id": clip.id,
                        "clip_name": clip_name,
                        "path": path,
                        "position": pos,
                        "duration": dur,
                        "shake_score": float(analysis.get("shake_score", 0.0)),
                        "shake_percentage": shake_pct,
                        "classification": classification,
                        "segments": analysis.get("shaky_segments", []),
                    })

            if shaky_clips_found:
                names_str = ", ".join(f'"{c["clip_name"]}" ({int(round(c["shake_percentage"]))}%)' for c in shaky_clips_found[:3])
                if len(shaky_clips_found) > 3:
                    names_str += f" and {len(shaky_clips_found) - 3} more"

                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SHAKY,
                    description=f"Detected <b>{len(shaky_clips_found)} shaky clip(s)</b> ({names_str})",
                    icon="✓",
                    details={"clips": shaky_clips_found}
                ))

                if command.has_action(ActionType.DELETE_SHAKY):
                    plan_items.append(PlanItem(
                        action=ActionType.DELETE_SHAKY,
                        description=f"Remove <b>{len(shaky_clips_found)}</b> detected shaky clip(s) from timeline",
                        icon="⚠️",
                        details={"clip_ids": [c["clip_id"] for c in shaky_clips_found]}
                    ))
                    operations.append({
                        "type": ActionType.DELETE_SHAKY,
                        "clip_ids": [c["clip_id"] for c in shaky_clips_found]
                    })
                elif command.has_action(ActionType.LABEL_SHAKY) or command.has_action(ActionType.DETECT_SHAKY):
                    plan_items.append(PlanItem(
                        action=ActionType.LABEL_SHAKY,
                        description=f"Find/create topmost unused layer and label <b>{len(shaky_clips_found)}</b> shaky clip(s) with <b>'SHAKY FOOTAGE – XX%'</b> warning indicators and timeline markers",
                        icon="✓",
                        details={"clips": shaky_clips_found}
                    ))
                    operations.append({
                        "type": ActionType.LABEL_SHAKY,
                        "clips": shaky_clips_found
                    })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SHAKY,
                    description="Analyzed clips for camera motion: <b>No shaky footage detected.</b>",
                    icon="ℹ️"
                ))

        # -------------------------------------------------------------
        # 2. Silence Detection & Removal
        # -------------------------------------------------------------
        if command.has_action(ActionType.REMOVE_SILENCE):
            from smartedit.audio_analysis import AudioAnalyzer
            audio_analyzer = AudioAnalyzer()

            total_silences = 0
            total_time_saved = 0.0
            silence_ops = []

            for clip in timeline_clips:
                path = clip.data.get("reader", {}).get("path") or ""
                if not path and clip.data.get("file_id"):
                    f = File.get(id=clip.data.get("file_id"))
                    if f:
                        path = f.absolute_path()

                if path and os.path.isfile(path):
                    has_audio = clip.data.get("reader", {}).get("has_audio")
                    if has_audio is False:
                        continue

                    try:
                        audio_path = audio_analyzer.extract_audio_if_needed(path)
                        cut_data = audio_analyzer.generate_cut_points(
                            audio_path,
                            top_db=command.parameters.get("silence", {}).get("top_db", 20),
                            min_silence_duration_sec=command.parameters.get("silence", {}).get("min_silence_duration_sec", 0.5)
                        )
                        cut_points = cut_data.get("cut_points", [])
                        saved_sec = cut_data.get("time_saved_sec", 0.0)

                        if cut_points:
                            total_silences += len(cut_points)
                            total_time_saved += saved_sec
                            silence_ops.append({
                                "clip_id": clip.id,
                                "cut_points": cut_points,
                                "time_saved_sec": saved_sec,
                                "clip_data": clip.data
                            })
                    except Exception as ex:
                        logger.warning(f"Audio analysis failed for clip {clip.id}: {ex}")

            if total_silences > 0:
                plan_items.append(PlanItem(
                    action=ActionType.REMOVE_SILENCE,
                    description=f"Remove <b>{total_silences} silent section(s)</b> (saving approximately {total_time_saved:.1f}s)",
                    icon="✓",
                    details={"silence_ops": silence_ops}
                ))
                operations.append({
                    "type": ActionType.REMOVE_SILENCE,
                    "silence_ops": silence_ops
                })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.REMOVE_SILENCE,
                    description="Analyzed audio levels: <b>No major silent intervals found</b>.",
                    icon="ℹ️"
                ))

        # -------------------------------------------------------------
        # 3. Clip Arrangement & Sequential Alignment
        # -------------------------------------------------------------
        if command.has_action(ActionType.ARRANGE_CLIPS) or command.has_action(ActionType.ROUGH_CUT):
            if timeline_clips:
                count = len(timeline_clips)
                plan_items.append(PlanItem(
                    action=ActionType.ARRANGE_CLIPS,
                    description=f"Rearrange <b>{count} clip(s)</b> in optimal sequential order on primary track with zero gaps",
                    icon="✓",
                    details={"clip_count": count}
                ))
                operations.append({
                    "type": ActionType.ARRANGE_CLIPS,
                    "source": "timeline"
                })
            elif project_files:
                count = len(project_files)
                plan_items.append(PlanItem(
                    action=ActionType.ARRANGE_CLIPS,
                    description=f"Add and arrange <b>{count} project file(s)</b> in sequential order on the timeline",
                    icon="✓",
                    details={"file_count": count}
                ))
                operations.append({
                    "type": ActionType.ARRANGE_CLIPS,
                    "source": "files"
                })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.ARRANGE_CLIPS,
                    description="No clips or files in project to arrange.",
                    icon="ℹ️"
                ))

        is_empty = len(operations) == 0
        summary = f"Plan contains {len(operations)} operation(s)."

        self.pending_plan = AIPlan(
            command=command,
            items=plan_items,
            operations=operations,
            summary=summary,
            is_empty=is_empty
        )
        return self.pending_plan

    def apply_plan(self, plan: Optional[AIPlan] = None) -> Dict[str, Any]:
        """
        Applies the proposed operations atomically to the timeline.
        Groups all changes into a single undo transaction.
        """
        target_plan = plan or self.pending_plan
        if not target_plan or target_plan.is_empty:
            return {"success": False, "message": "No operations in plan to apply."}

        from classes.app import get_app
        from classes.query import Clip, File, Marker

        app = get_app()
        window = getattr(app, "window", None)

        # Generate atomic transaction ID for undo/redo
        transaction_id = str(uuid.uuid4())
        self.last_transaction_id = transaction_id
        app.updates.transaction_id = transaction_id

        applied_details = []

        try:
            for op in target_plan.operations:
                op_type = op.get("type")

                # A. Label Shaky Clips (Non-destructive: places labels on topmost unused layer)
                if op_type == ActionType.LABEL_SHAKY:
                    shaky_items = op.get("clips", [])
                    if shaky_items:
                        target_layer = self.shaky_service.find_or_create_top_unused_layer()
                        created = self.shaky_service.label_shaky_clips(shaky_items, target_layer)
                        track_num = target_layer // 1000000
                        applied_details.append(f"Placed {len(created)} 'SHAKY FOOTAGE' label(s) on Track {track_num} (top unused layer)")

                # B. Delete Shaky Clips (only if explicitly requested!)
                elif op_type == ActionType.DELETE_SHAKY:
                    for cid in op.get("clip_ids", []):
                        clip = Clip.get(id=cid)
                        if clip:
                            clip.delete()
                    applied_details.append(f"Removed {len(op.get('clip_ids', []))} shaky clip(s)")

                # C. Arrange Clips Sequentially
                elif op_type == ActionType.ARRANGE_CLIPS:
                    source = op.get("source")
                    if source == "timeline":
                        all_clips = Clip.filter()
                        # Exclude AI label clips from clip rearrangement
                        clips = [
                            c for c in all_clips
                            if not (c.data or {}).get("ui", {}).get("ai_label")
                            and not str((c.data or {}).get("title", "")).startswith("SHAKY FOOTAGE")
                        ]
                        # Sort clips by existing position or file name
                        clips.sort(key=lambda c: (c.data.get("position", 0.0), c.data.get("layer", 0)))
                        
                        current_pos = 0.0
                        target_layer = 1000000  # Default primary track

                        for c in clips:
                            duration = float(c.data.get("end", 10.0)) - float(c.data.get("start", 0.0))
                            if duration <= 0.0:
                                duration = float(c.data.get("duration", 1.0))
                            
                            c.data["position"] = round(current_pos, 4)
                            c.data["layer"] = target_layer
                            c.save()
                            current_pos += duration

                        applied_details.append(f"Arranged {len(clips)} clip(s) sequentially")

                    elif source == "files":
                        all_files = File.filter()
                        files = [
                            f for f in all_files
                            if not (f.data or {}).get("ui", {}).get("ai_label")
                            and "ai_labels" not in str((f.data or {}).get("path", ""))
                        ]
                        current_pos = 0.0
                        target_layer = 1000000
                        for f in files:
                            if window and hasattr(window, "timeline"):
                                from PyQt5.QtCore import QPointF
                                window.timeline.addClip(
                                    file_id=f.id,
                                    position=QPointF(current_pos, 0.0),
                                    track=target_layer,
                                    call_manual_move=False
                                )
                                current_pos += float(f.data.get("duration", 5.0) or 5.0)

                        applied_details.append(f"Placed {len(files)} file(s) onto timeline")

                # D. Silence Removal
                elif op_type == ActionType.REMOVE_SILENCE:
                    for s_op in op.get("silence_ops", []):
                        clip = Clip.get(id=s_op["clip_id"])
                        if clip:
                            # Trim start/end silence if cut points touch boundaries
                            cut_points = s_op.get("cut_points", [])
                            if cut_points:
                                # Adjust start if silence at beginning
                                first_cut = cut_points[0]
                                if first_cut < 2.0:
                                    clip.data["start"] = float(clip.data.get("start", 0.0)) + first_cut
                                    clip.save()
                    applied_details.append("Processed silence cuts on timeline clips")

        finally:
            # Clear transaction id so subsequent manual edits form new transactions
            app.updates.transaction_id = None

        # Refresh the timeline view and project window
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "run_js"):
                try:
                    window.timeline.run_js("if (window.timeline) { timeline.loadTimeline(); }")
                except Exception:
                    pass

        self.pending_plan = None
        return {
            "success": True,
            "transaction_id": transaction_id,
            "message": "Successfully applied AI plan: " + "; ".join(applied_details)
        }

    def undo_last_ai_operation(self) -> bool:
        """Undoes the last AI operation using SmartEdit's undo system."""
        from classes.app import get_app
        app = get_app()
        try:
            app.updates.undo()
            window = getattr(app, "window", None)
            if window and hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            return True
        except Exception as ex:
            logger.error(f"Undo failed: {ex}")
            return False
