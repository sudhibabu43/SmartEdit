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
from slm.scene_detector import SceneDetectionEngine

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
        self.scene_engine = SceneDetectionEngine()
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
                if app and hasattr(app, "window") and hasattr(app.window, "selected_clips") and app.window.selected_clips:
                    selected_ids = set(app.window.selected_clips)
                    timeline_clips = [c for c in timeline_clips if str(c.id) in selected_ids]
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

        
        
        
        shaky_regions_found = []
        if command.has_action(ActionType.DETECT_SHAKY) or command.has_action(ActionType.DELETE_SHAKY):
            thresh_pct = self.shaky_service.get_threshold(command.parameters.get("shaky", {}).get("threshold") or command.parameters.get("delete_shaky", {}).get("threshold"))
            
            
            shaky_regions_found = self.shaky_service.analyze_timeline_shaky_regions(threshold=thresh_pct, clips=timeline_clips)

            if shaky_regions_found:
                affected_clips_count = len(set(r.get("clip_id") for r in shaky_regions_found if r.get("clip_id")))
                names = list(dict.fromkeys(r.get("clip_name", "Clip") for r in shaky_regions_found))
                names_str = ", ".join(f'"{n}"' for n in names[:3])
                if len(names) > 3:
                    names_str += f" and {len(names) - 3} more"

                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SHAKY,
                    description=f"Detected <b>{len(shaky_regions_found)} shaky region(s)</b> across {affected_clips_count} clip(s) ({names_str})",
                    icon="✓",
                    details={"regions": shaky_regions_found, "clips": shaky_regions_found}
                ))

                if command.has_action(ActionType.DELETE_SHAKY):
                    close_gaps = command.parameters.get("delete_shaky", {}).get("close_gaps", False)
                    gap_note = "closing gaps" if close_gaps else "preserving timeline coordinates (e.g. 0–5s and 8–20s)"
                    plan_items.append(PlanItem(
                        action=ActionType.DELETE_SHAKY,
                        description=f"Split clips at detected boundaries and remove <b>{len(shaky_regions_found)}</b> shaky segment(s) from timeline ({gap_note}); source video files untouched",
                        icon="✂",
                        details={"regions": shaky_regions_found, "clip_ids": [r.get("clip_id") for r in shaky_regions_found], "close_gaps": close_gaps}
                    ))
                    operations.append({
                        "type": ActionType.DELETE_SHAKY,
                        "regions": shaky_regions_found,
                        "clips": shaky_regions_found,
                        "clip_ids": [r.get("clip_id") for r in shaky_regions_found],
                        "close_gaps": close_gaps
                    })
                elif command.has_action(ActionType.LABEL_SHAKY) or command.has_action(ActionType.DETECT_SHAKY):
                    plan_items.append(PlanItem(
                        action=ActionType.LABEL_SHAKY,
                        description=f"Highlight <b>{len(shaky_regions_found)}</b> shaky segment(s) on the timeline",
                        icon="📍"
                    ))
                    operations.append({
                        "type": ActionType.LABEL_SHAKY,
                        "regions": shaky_regions_found,
                        "clips": shaky_regions_found
                    })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SHAKY,
                    description="Analyzed clips for camera motion: <b>No shaky footage detected.</b>",
                    icon="ℹ️"
                ))

        
        
        
        if command.has_action(ActionType.REMOVE_SILENCE):
            if not timeline_clips:
                plan_items.append(PlanItem(
                    action=ActionType.REMOVE_SILENCE,
                    description="No clips selected. Please select a clip on the timeline first.",
                    icon="ℹ️"
                ))
            else:
                plan_items.append(PlanItem(
                    action=ActionType.REMOVE_SILENCE,
                    description=f"Open the interactive Silence Remover tool for {len(timeline_clips)} selected clip(s) to review and apply cuts.",
                    icon="✓",
                ))
                operations.append({
                    "type": ActionType.REMOVE_SILENCE,
                    "clip_ids": [c.id for c in timeline_clips]
                })

        
        
        
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

        # -----------------------------------------------------------
        # SCENE DETECTION & CUTTING
        # -----------------------------------------------------------
        if command.has_action(ActionType.DETECT_SCENES) or command.has_action(ActionType.CUT_SCENES) or command.has_action(ActionType.REMOVE_SCENE) or command.has_action(ActionType.MARK_SCENES):
            total_scenes_detected = 0
            scene_ops = []
            
            for clip in timeline_clips:
                path = clip.data.get("reader", {}).get("path") or ""
                if not path and clip.data.get("file_id"):
                    f = File.get(id=clip.data.get("file_id"))
                    if f:
                        path = f.absolute_path()
                        
                if path and os.path.isfile(path):
                    try:
                        # Extract max duration based on clip end to save time
                        max_dur = float(clip.data.get("end", 0)) if clip.data.get("end") else 0.0
                        self.scene_engine.threshold = 15.0  # Lower threshold for more sensitive detection
                        res = self.scene_engine.detect_scenes(path, max_duration_sec=max_dur)
                        scenes = res.get("scenes", [])
                        boundaries = res.get("boundaries", [])
                        
                        if scenes:
                            total_scenes_detected += len(scenes)
                            scene_ops.append({
                                "clip_id": clip.id,
                                "path": path,
                                "scenes": scenes,
                                "boundaries": boundaries,
                                "clip_data": clip.data
                            })
                    except Exception as ex:
                        logger.error(f"Scene detection failed for {path}: {ex}", exc_info=1)

            if total_scenes_detected > 0:
                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SCENES,
                    description=f"Detected <b>{total_scenes_detected} visual scene(s)</b> across {len(scene_ops)} clip(s)",
                    icon="🔍"
                ))
                
                # If they explicitly want to cut scenes or remove a specific one
                if command.has_action(ActionType.CUT_SCENES):
                    total_cuts = sum(len(op["boundaries"]) for op in scene_ops)
                    plan_items.append(PlanItem(
                        action=ActionType.CUT_SCENES,
                        description=f"Slice timeline at <b>{total_cuts} scene boundary points</b> (non-destructive)",
                        icon="✂"
                    ))
                    operations.append({
                        "type": ActionType.CUT_SCENES,
                        "scene_ops": scene_ops
                    })
                    
                if command.has_action(ActionType.MARK_SCENES):
                    total_marks = sum(len(op["boundaries"]) for op in scene_ops)
                    plan_items.append(PlanItem(
                        action=ActionType.MARK_SCENES,
                        description=f"Add <b>{total_marks} markers</b> at detected edit points",
                        icon="📍"
                    ))
                    operations.append({
                        "type": ActionType.MARK_SCENES,
                        "scene_ops": scene_ops
                    })
                    
                if command.has_action(ActionType.REMOVE_SCENE):
                    target_scene = command.parameters.get("remove_scene", {}).get("target")
                    plan_items.append(PlanItem(
                        action=ActionType.REMOVE_SCENE,
                        description=f"Split and remove <b>Scene {target_scene}</b>",
                        icon="🗑️"
                    ))
                    operations.append({
                        "type": ActionType.REMOVE_SCENE,
                        "scene_ops": scene_ops,
                        "target_scene": target_scene
                    })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.DETECT_SCENES,
                    description="Analyzed video for visual scenes: <b>No distinct scene changes detected.</b>",
                    icon="ℹ️"
                ))

        # ───────────────────────────────────────────
        # GENERIC TIMELINE ACTIONS
        # ───────────────────────────────────────────
        if command.has_action(ActionType.DELETE_CLIPS):
            params = command.parameters.get("delete_clips", {})
            target = params.get("target", "ALL")
            count = params.get("count", 1)
            
            target_clips = []
            if target == "SELECTED":
                target_clips = timeline_clips
            else:
                all_clips = []
                try:
                    all_clips = Clip.filter()
                    all_clips.sort(key=lambda c: (c.data.get("position", 0.0), c.data.get("layer", 0)))
                except Exception:
                    pass
                if target == "LAST":
                    target_clips = all_clips[-count:] if count > 0 else all_clips
                elif target == "FIRST":
                    target_clips = all_clips[:count] if count > 0 else all_clips
                elif target == "ALL":
                    target_clips = all_clips

            if target_clips:
                clip_ids = [c.id for c in target_clips]
                plan_items.append(PlanItem(
                    action=ActionType.DELETE_CLIPS,
                    description=f"Delete <b>{len(clip_ids)} clip(s)</b> from the timeline",
                    icon="🗑️"
                ))
                operations.append({
                    "type": ActionType.DELETE_CLIPS,
                    "clip_ids": clip_ids
                })
            else:
                plan_items.append(PlanItem(
                    action=ActionType.DELETE_CLIPS,
                    description="No clips found matching the criteria to delete.",
                    icon="ℹ️"
                ))

        if command.has_action(ActionType.SELECT_CLIPS):
            params = command.parameters.get("select_clips", {})
            target = params.get("target", "ALL")
            count = params.get("count", 1)
            
            target_clips = []
            all_clips = []
            try:
                all_clips = Clip.filter()
                all_clips.sort(key=lambda c: (c.data.get("position", 0.0), c.data.get("layer", 0)))
            except Exception:
                pass
                
            if target == "LAST":
                target_clips = all_clips[-count:] if count > 0 else all_clips
            elif target == "FIRST":
                target_clips = all_clips[:count] if count > 0 else all_clips
            elif target == "RANGE":
                start_idx = max(0, params.get("start", 1) - 1)
                end_idx = min(len(all_clips), params.get("end", 1))
                target_clips = all_clips[start_idx:end_idx]
            elif target == "ALL":
                target_clips = all_clips
                
            if target_clips:
                clip_ids = [c.id for c in target_clips]
                plan_items.append(PlanItem(
                    action=ActionType.SELECT_CLIPS,
                    description=f"Select <b>{len(clip_ids)} clip(s)</b> on the timeline",
                    icon="🖱️"
                ))
                operations.append({
                    "type": ActionType.SELECT_CLIPS,
                    "clip_ids": clip_ids
                })

        if command.has_action(ActionType.SPLIT_CLIP):
            plan_items.append(PlanItem(
                action=ActionType.SPLIT_CLIP,
                description="Split selected clip(s) at the current playhead",
                icon="✂"
            ))
            operations.append({
                "type": ActionType.SPLIT_CLIP
            })

        if command.has_action(ActionType.MOVE_CLIPS):
            params = command.parameters.get("move_clips", {})
            target = params.get("target", "SELECTED")
            position = params.get("position", "BEGINNING")
            
            plan_items.append(PlanItem(
                action=ActionType.MOVE_CLIPS,
                description=f"Move {target.lower()} clip(s) to the {position.lower()}",
                icon="↔️"
            ))
            operations.append({
                "type": ActionType.MOVE_CLIPS,
                "target": target,
                "position": position,
                "clip_ids": [c.id for c in timeline_clips] if target == "SELECTED" else []
            })

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

        
        transaction_id = str(uuid.uuid4())
        self.last_transaction_id = transaction_id
        app.updates.transaction_id = transaction_id

        applied_details = []

        try:
            for op in target_plan.operations:
                op_type = op.get("type")

                
                if op_type == ActionType.DELETE_SHAKY:
                    shaky_items = op.get("regions") or op.get("clips", [])
                    if shaky_items:
                        close_gaps = op.get("close_gaps", False)
                        res = self.shaky_service.trim_shaky_footage(shaky_items, close_gaps=close_gaps)
                        applied_details.append(f"Split and removed {res.get('removed_count', len(shaky_items))} shaky segment(s); preserved stable portions on timeline without modifying source files")
                    else:
                        for cid in op.get("clip_ids", []):
                            clip = Clip.get(id=cid)
                            if clip:
                                clip.delete()
                        applied_details.append(f"Removed {len(op.get('clip_ids', []))} shaky clip(s)")

                
                elif op_type == ActionType.DELETE_CLIPS:
                    clip_ids = op.get("clip_ids", [])
                    count = 0
                    for cid in clip_ids:
                        clip = Clip.get(id=cid)
                        if clip:
                            clip.delete()
                            count += 1
                    applied_details.append(f"Deleted {count} clip(s)")
                    
                elif op_type == ActionType.SELECT_CLIPS:
                    clip_ids = op.get("clip_ids", [])
                    if window and hasattr(window, "timeline"):
                        window.timeline.ClearAllSelections()
                        for cid in clip_ids:
                            window.timeline.addSelection(cid, "clip")
                    applied_details.append(f"Selected {len(clip_ids)} clip(s)")
                    
                elif op_type == ActionType.SPLIT_CLIP:
                    if window and hasattr(window, "timeline"):
                        # Uses the existing timeline UI method for splitting at playhead
                        clip_ids = [c for c in window.selected_clips]
                        if not clip_ids:
                            # Split all clips intersecting playhead if nothing selected
                            from classes.timeline import Timeline
                            t = Timeline()
                            intersecting = t.clips(app.window.timeline.get_playhead_position())
                            clip_ids = [c.id for c in intersecting]
                        if clip_ids:
                            window.timeline.Split_Audio_Triggered(None, clip_ids)
                    applied_details.append("Split clip(s) at playhead")
                    
                elif op_type == ActionType.MOVE_CLIPS:
                    target = op.get("target")
                    position = op.get("position")
                    clip_ids = op.get("clip_ids", [])
                    
                    if target == "SELECTED" and window:
                        clip_ids = [c for c in window.selected_clips]
                        
                    if clip_ids:
                        clips = [Clip.get(id=cid) for cid in clip_ids]
                        clips = [c for c in clips if c]
                        if clips:
                            all_clips = Clip.filter()
                            all_clips.sort(key=lambda c: (c.data.get("position", 0.0), c.data.get("layer", 0)))
                            if position == "BEGINNING":
                                # Move to position 0 and shift others
                                current_pos = 0.0
                                for c in clips:
                                    dur = float(c.data.get("end", 0.0)) - float(c.data.get("start", 0.0))
                                    c.data["position"] = current_pos
                                    c.save()
                                    current_pos += dur
                            elif position == "END":
                                # Move to end of last clip
                                max_pos = 0.0
                                if all_clips:
                                    last_c = all_clips[-1]
                                    max_pos = float(last_c.data.get("position", 0.0)) + (float(last_c.data.get("end", 0.0)) - float(last_c.data.get("start", 0.0)))
                                for c in clips:
                                    dur = float(c.data.get("end", 0.0)) - float(c.data.get("start", 0.0))
                                    c.data["position"] = max_pos
                                    c.save()
                                    max_pos += dur
                    applied_details.append(f"Moved {len(clip_ids)} clip(s) to the {position.lower()}")

                elif op_type == ActionType.ARRANGE_CLIPS:
                    source = op.get("source")
                    if source == "timeline":
                        all_clips = Clip.filter()
                        
                        clips = [
                            c for c in all_clips
                            if not ((c.data or {}).get("ui") or {}).get("ai_label")
                            and not str((c.data or {}).get("title", "")).startswith("SHAKY FOOTAGE")
                        ]
                        
                        clips.sort(key=lambda c: (c.data.get("position", 0.0), c.data.get("layer", 0)))
                        
                        current_pos = 0.0
                        target_layer = 1000000  

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
                            if not ((f.data or {}).get("ui") or {}).get("ai_label")
                            and "ai_labels" not in str((f.data or {}).get("path", ""))
                        ]
                        current_pos = 0.0
                        target_layer = 1000000
                        for f in files:
                            if window and hasattr(window, "timeline"):
                                from qt_api import QPointF  # FIX BUG 1: Use qt_api abstraction, not PyQt5
                                window.timeline.addClip(
                                    file_id=f.id,
                                    position=QPointF(current_pos, 0.0),
                                    track=target_layer,
                                    call_manual_move=False
                                )
                                current_pos += float(f.data.get("duration", 5.0) or 5.0)

                        applied_details.append(f"Placed {len(files)} file(s) onto timeline")

                
                elif op_type == ActionType.REMOVE_SILENCE:
                    clip_ids = op.get("clip_ids", [])
                    if clip_ids:
                        from windows.silence_remover_dialog import SilenceRemoverDialog
                        from classes.models import Clip, File
                        clip = Clip.get(id=clip_ids[0])
                        path = clip.data.get("reader", {}).get("path") or ""
                        if not path and clip.data.get("file_id"):
                            f = File.get(id=clip.data.get("file_id"))
                            if f:
                                path = f.absolute_path()
                        
                        dlg = SilenceRemoverDialog(window, initial_media_path=path, clip_ids=clip_ids)
                        dlg.exec_()
                    applied_details.append("Opened interactive Silence Remover tool for user review")

                elif op_type == ActionType.CUT_SCENES:
                    scene_ops = op.get("scene_ops", [])
                    total_splits = 0
                    for s_op in scene_ops:
                        clip_id = s_op.get("clip_id")
                        boundaries = sorted(s_op.get("boundaries", []))
                        if not clip_id or not boundaries:
                            continue
                            
                        clip = Clip.get(id=clip_id)
                        if not clip:
                            continue
                            
                        # Slice clip at each boundary non-destructively
                        c_start = float(clip.data.get("start", 0.0))
                        c_end = float(clip.data.get("end", 0.0))
                        c_pos = float(clip.data.get("position", 0.0))
                        
                        current_clip = clip
                        
                        for b in boundaries:
                            # Verify boundary falls within clip bounds
                            if b > c_start and b < c_end:
                                # Update current clip end
                                current_clip.data["end"] = b
                                current_clip.save()
                                
                                # Duplicate for the next segment
                                new_clip_data = current_clip.data.copy()
                                new_clip_data["id"] = str(uuid.uuid4())
                                new_clip_data["start"] = b
                                new_clip_data["end"] = c_end
                                new_clip_data["position"] = c_pos + (b - c_start)
                                
                                new_clip = Clip()
                                new_clip.data = new_clip_data
                                new_clip.save()
                                
                                current_clip = new_clip
                                total_splits += 1
                                c_start = b
                                
                    applied_details.append(f"Sliced clips at {total_splits} scene boundaries")

                elif op_type == ActionType.REMOVE_SCENE:
                    scene_ops = op.get("scene_ops", [])
                    target_scene = op.get("target_scene")
                    try:
                        target_id = int(target_scene)
                    except (ValueError, TypeError):
                        target_id = -1
                        
                    for s_op in scene_ops:
                        clip = Clip.get(id=s_op.get("clip_id"))
                        if not clip: continue
                        
                        scenes = s_op.get("scenes", [])
                        for scene in scenes:
                            if scene.get("scene_id") == target_id:
                                s = max(scene.get("start_time", 0.0), float(clip.data.get("start", 0.0)))
                                e = min(scene.get("end_time", 0.0), float(clip.data.get("end", 0.0)))
                                
                                if s < e:
                                    c_end = float(clip.data.get("end", 0.0))
                                    c_pos = float(clip.data.get("position", 0.0))
                                    c_start = float(clip.data.get("start", 0.0))
                                    
                                    clip.data["end"] = s
                                    clip.save()
                                    
                                    if e < c_end:
                                        new_clip_data = clip.data.copy()
                                        new_clip_data["id"] = str(uuid.uuid4())
                                        new_clip_data["start"] = e
                                        new_clip_data["end"] = c_end
                                        new_clip_data["position"] = c_pos + (e - c_start)
                                        
                                        new_clip = Clip()
                                        new_clip.data = new_clip_data
                                        new_clip.save()
                                        
                                    applied_details.append(f"Removed Scene {target_id}")
                                break
                                
                elif op_type == ActionType.LABEL_SHAKY:
                    regions = op.get("regions", [])
                    total_marks = 0
                    for r in regions:
                        clip_id = r.get("clip_id")
                        c_pos = float(r.get("clip_position", 0.0))
                        c_start = float(r.get("clip_start", 0.0))
                        s_time = float(r.get("start_time", 0.0))
                        e_time = float(r.get("end_time", 0.0))
                        
                        if clip_id:
                            clip = Clip.get(id=clip_id)
                            if clip:
                                c_pos = float(clip.data.get("position", 0.0))
                                c_start = float(clip.data.get("start", 0.0))
                                
                        # Create marker at start of shaky region
                        timeline_time = c_pos + (s_time - c_start)
                        marker = Marker()
                        marker.data = {
                            "id": str(uuid.uuid4()),
                            "position": timeline_time,
                            "icon": "marker",
                            "color": "#FF0000",
                            "title": f"SHAKY ({r.get('shaky_percentage', 0.0):.1f}%)"
                        }
                        marker.save()
                        total_marks += 1
                        
                        # Create marker at end of shaky region
                        timeline_time_end = c_pos + (e_time - c_start)
                        marker_end = Marker()
                        marker_end.data = {
                            "id": str(uuid.uuid4()),
                            "position": timeline_time_end,
                            "icon": "marker",
                            "color": "#FF0000",
                            "title": "END SHAKY"
                        }
                        marker_end.save()
                        total_marks += 1
                        
                    applied_details.append(f"Added {total_marks} markers to highlight shaky regions")
                                
                elif op_type == ActionType.MARK_SCENES:
                    scene_ops = op.get("scene_ops", [])
                    total_marks = 0
                    for s_op in scene_ops:
                        clip_id = s_op.get("clip_id")
                        boundaries = sorted(s_op.get("boundaries", []))
                        if not clip_id or not boundaries:
                            continue
                            
                        clip = Clip.get(id=clip_id)
                        if not clip:
                            continue
                            
                        c_start = float(clip.data.get("start", 0.0))
                        c_pos = float(clip.data.get("position", 0.0))
                        
                        for b in boundaries:
                            timeline_time = c_pos + (b - c_start)
                            # Create marker
                            marker = Marker()
                            marker.data = {
                                "position": timeline_time,
                                "icon": "blue.png",
                                "vector": "blue",
                            }
                            marker.save()
                            total_marks += 1
                                
                    applied_details.append(f"Added {total_marks} scene markers to timeline")

        finally:
            
            app.updates.transaction_id = None

        
        if window:
            if hasattr(window, "refreshFrameSignal"):
                window.refreshFrameSignal.emit()
            if hasattr(window, "timeline") and hasattr(window.timeline, "update"):
                window.timeline.update()

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
