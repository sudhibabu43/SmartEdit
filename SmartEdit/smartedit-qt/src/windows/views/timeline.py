"""
 @file
 @brief This file loads the interactive timeline
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author Noah Figg <eggmunkee@hotmail.com>
 @author Olivier Girard <eolinwen@gmail.com>

 @section LICENSE

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with SmartEdit Library.  If not, see <http://www.gnu.org/licenses/>.
 """

import json
from copy import deepcopy
import logging
import os
import time
import uuid
from functools import partial
from operator import itemgetter

import smartedit
from qt_api import pyqtSlot, Qt, QCoreApplication, QTimer, pyqtSignal, QPointF
from qt_api import modifiers_has
from qt_api import QCursor, QKeySequence, QIcon
from qt_api import QDialog

from classes import info, updates
from classes.app import get_app
from classes.film_grain_presets import (
    FILM_GRAIN_CLASS_NAME,
    FILM_GRAIN_PRESET_16MM_CLASSIC,
    FILM_GRAIN_PRESET_35MM_CLASSIC,
    FILM_GRAIN_PRESET_35MM_FINE,
    FILM_GRAIN_PRESET_35MM_GRITTY,
    FILM_GRAIN_PRESET_HIGH_ISO,
    FILM_GRAIN_PRESET_NONE,
    FILM_GRAIN_PRESET_SUPER_8,
    apply_film_grain_preset,
    is_film_grain_effect,
)

LOOK_EFFECT_UI_MENU = "look"
MOTION_EFFECT_UI_MENU = "motion"

LOOK_RESET_EFFECT_CLASSES = {
    FILM_GRAIN_CLASS_NAME,
}

LOOK_EFFECT_PRESETS = {
    "AnalogTape": {
        "none": {},
        "subtle": {
            "bleed": 0.25,
            "noise": 0.18,
            "softness": 0.15,
            "static_bands": 0.05,
            "stripe": 0.06,
            "tracking": 0.20,
        },
        "vhs": {
            "bleed": 0.55,
            "noise": 0.35,
            "softness": 0.35,
            "static_bands": 0.18,
            "stripe": 0.20,
            "tracking": 0.45,
        },
        "heavy": {
            "bleed": 0.85,
            "noise": 0.60,
            "softness": 0.55,
            "static_bands": 0.35,
            "stripe": 0.40,
            "tracking": 0.75,
        },
    },
    "Blur": {
        "none": {},
        "soft_focus": {"horizontal_radius": 3.0, "vertical_radius": 3.0, "sigma": 1.5, "iterations": 2.0},
        "medium": {"horizontal_radius": 8.0, "vertical_radius": 8.0, "sigma": 4.0, "iterations": 3.0},
        "heavy": {"horizontal_radius": 20.0, "vertical_radius": 20.0, "sigma": 8.0, "iterations": 4.0},
    },
    "Glow": {
        "none": {},
        "soft_white": {"mode": 0, "opacity": 0.35, "blur_radius": 18.0, "spread": 0.15, "color": "#ffffffff"},
        "warm": {"mode": 0, "opacity": 0.45, "blur_radius": 24.0, "spread": 0.20, "color": "#ffd28cff"},
        "neon": {"mode": 0, "opacity": 0.65, "blur_radius": 16.0, "spread": 0.35, "color": "#35d7ffff"},
        "inner": {"mode": 1, "opacity": 0.45, "blur_radius": 12.0, "spread": 0.25, "color": "#ffffffff"},
    },
    "Shadow": {
        "none": {},
        "subtle": {"opacity": 0.30, "blur_radius": 12.0, "spread": 0.05, "distance": 8.0, "angle": 135.0, "color": "#000000ff"},
        "soft": {"opacity": 0.45, "blur_radius": 28.0, "spread": 0.10, "distance": 14.0, "angle": 135.0, "color": "#000000ff"},
        "strong": {"opacity": 0.70, "blur_radius": 18.0, "spread": 0.25, "distance": 16.0, "angle": 135.0, "color": "#000000ff"},
        "long": {"opacity": 0.45, "blur_radius": 24.0, "spread": 0.12, "distance": 44.0, "angle": 135.0, "color": "#000000ff"},
    },
    "Sharpen": {
        "none": {},
        "subtle": {"amount": 4.0, "radius": 1.5, "threshold": 0.0},
        "medium": {"amount": 9.0, "radius": 2.5, "threshold": 0.0},
        "strong": {"amount": 16.0, "radius": 3.5, "threshold": 0.0},
    },
}

from classes.camera_motion import (
    KEN_BURNS_AUTO,
    KEN_BURNS_BOTTOM_TO_TOP,
    KEN_BURNS_LEFT_TO_RIGHT,
    KEN_BURNS_RIGHT_TO_LEFT,
    KEN_BURNS_TOP_TO_BOTTOM,
    PAN_AUTO,
    PAN_DOWN,
    PAN_LEFT,
    PAN_LEFT_TO_RIGHT,
    PAN_RIGHT,
    PAN_RIGHT_TO_LEFT,
    PAN_TOP_TO_BOTTOM,
    PAN_BOTTOM_TO_TOP,
    PAN_UP,
    camera_pan_keyframes,
    ken_burns_keyframes,
    push_pull_keyframes,
    source_dimensions_from_reader,
)
from classes.effect_init import effect_options
from classes.logger import log
from classes.query import File, Clip, Transition, Track, Effect
from classes.clipboard import ClipboardManager
from classes.thumbnail import GetThumbPath
from classes.waveform import (
    ABSOLUTE_WAVEFORM_FORMAT,
    WAVEFORM_FORMAT_KEY,
    WAVEFORM_RATE_KEY,
    WAVEFORM_RMS_KEY,
    get_audio_data,
)
from classes.path_utils import absolute_media_path
from .timeline_backend.enums import (
    MenuFade, MenuRotate, MenuLayout, MenuAlign, MenuAnimate, MenuVolume,
    MenuTime, MenuCopy, MenuSlice, MenuSplitAudio
)
from .timeline_backend.qwidget import TimelineWidget
from .timeline_backend.colors import effect_color_hex
from .menu import StyledContextMenu
from classes.clip_utils import (
    clamp_timing_to_media,
    apply_file_caption_to_clip,
    is_single_image_media,
)
from .retime import retime_clip
from .repeat import apply_repeat, reset_repeat, RepeatDialog


JS_SCOPE_SELECTOR = "$('body').scope()"
MICROPHONE_ICON = "tool-microphone.svg"
ViewClass = TimelineWidget

log.info("Timeline backend: QWidget (%s)", getattr(ViewClass, "__name__", "unknown"))



from classes.animation_presets import PRESETS as _ANIMATION_PRESETS, KEYFRAME_EASING as _KEYFRAME_EASING


_JSON_ANIM = {
    MenuAnimate.BACK_IN_DOWN:    "backInDown",
    MenuAnimate.BACK_IN_LEFT:    "backInLeft",
    MenuAnimate.BACK_IN_RIGHT:   "backInRight",
    MenuAnimate.BACK_IN_UP:      "backInUp",
    MenuAnimate.BOUNCE_IN:       "bounceIn",
    MenuAnimate.BOUNCE_IN_DOWN:  "bounceInDown",
    MenuAnimate.BOUNCE_IN_LEFT:  "bounceInLeft",
    MenuAnimate.BOUNCE_IN_RIGHT: "bounceInRight",
    MenuAnimate.BOUNCE_IN_UP:    "bounceInUp",
    MenuAnimate.BACK_OUT_DOWN:   "backOutDown",
    MenuAnimate.BACK_OUT_LEFT:   "backOutLeft",
    MenuAnimate.BACK_OUT_RIGHT:  "backOutRight",
    MenuAnimate.BACK_OUT_UP:     "backOutUp",
    MenuAnimate.BOUNCE_OUT:      "bounceOut",
    MenuAnimate.BOUNCE_OUT_DOWN: "bounceOutDown",
    MenuAnimate.BOUNCE_OUT_LEFT: "bounceOutLeft",
    MenuAnimate.BOUNCE_OUT_RIGHT:"bounceOutRight",
    MenuAnimate.BOUNCE_OUT_UP:   "bounceOutUp",
    MenuAnimate.BOUNCE:          "bounce",
    MenuAnimate.FLASH:           "flash",
    MenuAnimate.PULSE:           "pulse",
    MenuAnimate.RUBBER_BAND:     "rubberBand",
    MenuAnimate.SHAKE_X:         "shakeX",
    MenuAnimate.SHAKE_Y:         "shakeY",
    MenuAnimate.SWING:           "swing",
    MenuAnimate.TADA:            "tada",
    MenuAnimate.WOBBLE:          "wobble",
    MenuAnimate.JELLO:           "jello",
    MenuAnimate.HEART_BEAT:      "heartBeat",
}

_EMPHASIS_ACTIONS = frozenset({
    MenuAnimate.BOUNCE, MenuAnimate.FLASH, MenuAnimate.PULSE,
    MenuAnimate.RUBBER_BAND, MenuAnimate.SHAKE_X, MenuAnimate.SHAKE_Y,
    MenuAnimate.SWING, MenuAnimate.TADA,
    MenuAnimate.WOBBLE, MenuAnimate.JELLO, MenuAnimate.HEART_BEAT,
})

_IN_ACTIONS = frozenset({
    MenuAnimate.BACK_IN_DOWN, MenuAnimate.BACK_IN_LEFT,
    MenuAnimate.BACK_IN_RIGHT, MenuAnimate.BACK_IN_UP,
    MenuAnimate.BOUNCE_IN, MenuAnimate.BOUNCE_IN_DOWN,
    MenuAnimate.BOUNCE_IN_LEFT, MenuAnimate.BOUNCE_IN_RIGHT,
    MenuAnimate.BOUNCE_IN_UP,
})


def _event_posf(event):
    if hasattr(event, "posF"):
        return event.posF()
    return event.position()


class TimelineView(updates.UpdateInterface, ViewClass):
    """Timeline integration widget backed by the QWidget timeline."""

    
    html_path = os.path.join(info.PATH, 'timeline', 'index.html')

    
    clipAudioDataReady = pyqtSignal(str, object, str)
    fileAudioDataReady = pyqtSignal(str, object, str)

    def _microphone_icon(self):
        return QIcon(os.path.join(info.PATH, "themes/cosmic/images", MICROPHONE_ICON))

    def _show_recording_dock_deferred(self, start_time=None, track_number=None):
        """Open recording after context-menu event handling has unwound."""
        QTimer.singleShot(
            50,
            lambda: self.window.show_audio_recording_dock(
                start_time=start_time,
                track_number=track_number,
            )
        )

    def _recording_track_for_clip(self, clip):
        """Prefer the nearest lower unlocked track with room for a voiceover."""
        try:
            clip_data = clip.data if isinstance(clip.data, dict) else {}
            source_track = int(clip_data.get("layer", 1) or 1)
            start = float(clip_data.get("position", 0.0) or 0.0)
            duration = max(
                0.0,
                float(clip_data.get("end", 0.0) or 0.0) - float(clip_data.get("start", 0.0) or 0.0),
            )
        except (TypeError, ValueError):
            return 1

        end = start + max(duration, 0.001)
        try:
            tracks = sorted(
                Track.filter(),
                key=lambda t: int(t.data.get("number", 0) or 0),
                reverse=True,
            )
        except Exception:
            tracks = []

        candidate_numbers = [
            int(track.data.get("number", 0) or 0)
            for track in tracks
            if int(track.data.get("number", 0) or 0) < source_track
            and not track.data.get("lock", False)
        ]
        if not candidate_numbers:
            return source_track

        occupied = {}
        for existing in Clip.filter():
            data = existing.data if isinstance(existing.data, dict) else {}
            try:
                layer = int(data.get("layer", 0) or 0)
                left = float(data.get("position", 0.0) or 0.0)
                right = left + max(0.0, float(data.get("end", 0.0) or 0.0) - float(data.get("start", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue
            occupied.setdefault(layer, []).append((left, right))

        for track_number in candidate_numbers:
            has_overlap = any(left < end and right > start for left, right in occupied.get(track_number, []))
            if not has_overlap:
                return track_number
        return source_track

    def _record_from_clip(self, clip):
        """Seek to a clip's first frame and open Recording on a free lower track."""
        clip_data = clip.data if isinstance(clip.data, dict) else {}
        try:
            position = max(0.0, float(clip_data.get("position", 0.0) or 0.0))
        except (TypeError, ValueError):
            position = 0.0
        try:
            fps = get_app().project.get("fps")
            fps_value = float(fps["num"]) / float(fps["den"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            fps_value = 30.0
        frame_number = max(1, int(round(position * fps_value)) + 1)
        self.PlayheadMoved(frame_number, True)
        self._show_recording_dock_deferred(
            start_time=position,
            track_number=self._recording_track_for_clip(clip),
        )

    def connect_playback(self):
        """Connect playback signals to the QWidget timeline."""
        TimelineWidget.connect_playback(self)

    @pyqtSlot()
    def page_ready(self):
        """Document.Ready event has fired, and is initialized"""
        self.document_is_ready = True

    @pyqtSlot(result=str)
    def get_uuid(self):
        """Get a unique id (used for generating a transaction id for the undo/redo system)"""
        return str(uuid.uuid4())

    @pyqtSlot(result=str)
    def get_thumb_address(self):
        """Return the thumbnail HTTP server address"""
        thumb_server_details = self.window.http_server_thread.server_address
        while not thumb_server_details:
            log.info('No HTTP thumbnail server found yet... keep waiting...')
            time.sleep(0.25)
            thumb_server_details = self.window.http_server_thread.server_address

        thumb_address = "http://%s:%s/thumbnails/" % (thumb_server_details[0], thumb_server_details[1])
        return thumb_address

    @pyqtSlot(str, str, str)
    def StartKeyframeDrag(self, object_type, object_id, transaction_id):
        """Begin a keyframe drag operation"""
        self.keyframe_transaction_id = transaction_id
        get_app().updates.transaction_id = transaction_id
        get_app().updates.ignore_history = True
        
        self.window.IgnoreUpdates.emit(True, False)
        self.show_wait_spinner = False
        obj = None
        if object_type == "clip":
            obj = Clip.get(id=object_id)
        elif object_type == "transition":
            obj = Transition.get(id=object_id)
        if obj:
            self.keyframe_drag_original[object_id] = json.loads(json.dumps(obj.data))

    @pyqtSlot(str, str)
    def FinalizeKeyframeDrag(self, object_type, object_id):
        """Finalize a keyframe drag operation and record history"""
        obj = None
        if object_type == "clip":
            obj = Clip.get(id=object_id)
        elif object_type == "transition":
            obj = Transition.get(id=object_id)
        self.show_wait_spinner = True
        original = self.keyframe_drag_original.pop(object_id, None)
        if obj:
            get_app().updates.transaction_id = self.keyframe_transaction_id
            get_app().updates.ignore_history = True
            obj.save()
            if original:
                get_app().updates.apply_last_action_to_history(original)
                if (
                    object_type == "clip"
                    and self._clip_volume_curve_changed(original, getattr(obj, "data", None))
                    and self._clip_has_visible_waveform(obj)
                ):
                    self.Show_Waveform_Triggered(
                        [obj.id],
                        transaction_id=self.keyframe_transaction_id,
                    )
        get_app().updates.transaction_id = None
        get_app().updates.ignore_history = False
        self.keyframe_transaction_id = None
        
        self.window.IgnoreUpdates.emit(False, False)

    def _collect_clip_ids_from_value(self, value, clip_ids):
        """Recursively collect clip ids from an update payload without walking audio samples"""
        if isinstance(value, dict):
            clip_id = value.get("id")
            if clip_id:
                clip_ids.add(str(clip_id))
            for key, sub_value in value.items():
                if key == "audio_data":
                    continue
                self._collect_clip_ids_from_value(sub_value, clip_ids)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    self._collect_clip_ids_from_value(item, clip_ids)

    def _payload_contains_waveform(self, value):
        """Check if an update payload already contains waveform samples"""
        if isinstance(value, dict):
            audio_data = value.get("audio_data")
            if isinstance(audio_data, list) and len(audio_data) > 0:
                return True
            ui_value = value.get("ui")
            if ui_value and self._payload_contains_waveform(ui_value):
                return True
            for key, sub_value in value.items():
                if key in ("audio_data", "ui"):
                    continue
                if self._payload_contains_waveform(sub_value):
                    return True
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)) and self._payload_contains_waveform(item):
                    return True
        return False

    def _clip_has_visible_waveform(self, clip):
        """Return True when a clip currently has waveform samples displayed."""
        if not clip or not isinstance(getattr(clip, "data", None), dict):
            return False
        audio_data = clip.data.get("ui", {}).get("audio_data")
        return isinstance(audio_data, list) and len(audio_data) > 0

    def _clip_volume_curve_changed(self, original_data, current_data):
        """Return True when a clip's volume keyframe payload changed."""
        if not isinstance(original_data, dict) or not isinstance(current_data, dict):
            return False
        return original_data.get("volume") != current_data.get("volume")

    def _assign_new_effect_ids(self, clip_data):
        """Assign new unique IDs to each effect on the provided clip data."""
        if not isinstance(clip_data, dict):
            return

        effects = clip_data.get("effects")
        if not isinstance(effects, list):
            return

        for effect in effects:
            if isinstance(effect, dict):
                effect["id"] = get_app().project.generate_id()

    def _select_inserted_paste_items(self, inserted_items):
        """Replace the current selection with newly inserted pasted items."""
        if not inserted_items:
            return

        if ViewClass == TimelineWidget:
            TimelineWidget.clear_all_selections(self)
            for index, (item_id, item_type) in enumerate(inserted_items):
                self._select_timeline_item(item_id, item_type, clear_existing=(index == 0))
            return

        self.ClearAllSelections()
        for index, (item_id, item_type) in enumerate(inserted_items):
            self.AddSelectionJS(item_id, item_type, clear_existing=(index == 0))

    def _handle_paste_callback(self, clip_ids, tran_ids, callback_data):
        """Handle clipboard data insertion after resolving timeline coordinates."""
        position = callback_data.get("position", 0.0)
        layer_id = callback_data.get("track", 0)
        inserted_new_items = False
        inserted_items = []

        tid = self.get_uuid()
        get_app().updates.transaction_id = tid

        try:
            copied_object = ClipboardManager.from_mime(get_app().clipboard().mimeData())
            if not copied_object:
                return

            if isinstance(copied_object, Clip):
                clip_ids = [cid for cid in clip_ids if cid != copied_object.id]
            if isinstance(copied_object, Transition):
                tran_ids = [tran_id for tran_id in tran_ids if tran_id != copied_object.id]

            def adjust_positions_and_layers(objects, target_position, target_layer):
                if not objects:
                    return

                left_most_position = min(obj.data.get("position", 0.0) for obj in objects)
                top_most_layer = max(obj.data.get("layer", 0) for obj in objects)
                position_diff = target_position - left_most_position
                layer_diff = target_layer - top_most_layer if target_layer != -1 else 0
                layer_map = {}
                if target_layer != -1:
                    source_layers = sorted(
                        {
                            int(obj.data.get("layer", 0))
                            for obj in objects
                            if obj.data.get("layer") is not None
                        },
                        reverse=True,
                    )
                    target_layers = TimelineView._track_stack_from(self, target_layer, len(source_layers))
                    layer_map = dict(zip(source_layers, target_layers))

                for obj in objects:
                    obj.type = "insert"
                    obj.data.pop("id", None)
                    obj.id = None
                    self._assign_new_effect_ids(obj.data)
                    obj.data["position"] = obj.data.get("position", 0.0) + position_diff
                    old_layer = obj.data.get("layer", 0)
                    try:
                        old_layer_key = int(old_layer)
                    except (TypeError, ValueError):
                        old_layer_key = old_layer
                    obj.data["layer"] = layer_map.get(old_layer_key, obj.data.get("layer", 0) + layer_diff)
                    TimelineView._ensure_layers_exist(self, [obj.data.get("layer")])
                    obj.save()
                    item_id = getattr(obj, "id", None) or obj.data.get("id")
                    item_type = None
                    if isinstance(obj, Clip):
                        item_type = "clip"
                    elif isinstance(obj, Transition):
                        item_type = "transition"
                    if item_id and item_type:
                        inserted_items.append((str(item_id), item_type))

            def apply_clipboard_data(target_obj, clipboard_data, excluded_keys=None):
                excluded_keys = excluded_keys or []
                for key, value in clipboard_data.items():
                    if key in excluded_keys:
                        continue
                    if key == "effects" and isinstance(value, list):
                        existing_effects = target_obj.data.setdefault("effects", [])
                        effect_map = {
                            effect.get("class_name"): effect
                            for effect in existing_effects
                            if isinstance(effect, dict) and effect.get("class_name")
                        }

                        for effect in value:
                            if not isinstance(effect, dict):
                                continue
                            effect_copy = deepcopy(effect)
                            self._assign_new_effect_ids({"effects": [effect_copy]})
                            effect_type = effect_copy.get("class_name")
                            if effect_type in effect_map:
                                effect_map[effect_type].update(effect_copy)
                            else:
                                existing_effects.append(effect_copy)
                        target_obj.data["effects"] = existing_effects
                    else:
                        target_obj.data[key] = value
                target_obj.save()

            if len(clip_ids + tran_ids) == 0 and (
                isinstance(copied_object, Clip) or isinstance(copied_object, Transition)
            ):
                copied_object = [copied_object]

            if isinstance(copied_object, list):
                adjust_positions_and_layers(copied_object, position, layer_id)
                inserted_new_items = True

            for clip_id in clip_ids:
                clip = Clip.get(id=clip_id)
                if not clip:
                    continue
                if isinstance(copied_object, Clip):
                    apply_clipboard_data(
                        clip,
                        copied_object.data,
                        excluded_keys=["id", "position", "layer", "start", "end"],
                    )
                elif isinstance(copied_object, Effect):
                    effect_copy = deepcopy(copied_object.data)
                    self._assign_new_effect_ids({"effects": [effect_copy]})
                    apply_clipboard_data(clip, {"effects": [effect_copy]}, excluded_keys=["id"])

            for tran_id in tran_ids:
                tran = Transition.get(id=tran_id)
                if tran and isinstance(copied_object, Transition):
                    apply_clipboard_data(
                        tran,
                        copied_object.data,
                        excluded_keys=["id", "position", "layer", "start", "end"],
                    )

            if inserted_new_items:
                self._extend_timeline_to_fit_items()
                self._select_inserted_paste_items(inserted_items)
        finally:
            get_app().updates.transaction_id = None

    def _ensure_layers_exist(self, layers):
        window = getattr(get_app(), "window", None)
        ensure = getattr(window, "ensure_tracks_for_layers", None)
        if callable(ensure):
            ensure(list(layers or []))

    def _track_stack_from(self, layer_number, count):
        window = getattr(get_app(), "window", None)
        stack = getattr(window, "track_stack_from", None)
        if callable(stack):
            return stack(layer_number, count)

        try:
            layer_number = int(layer_number)
        except (TypeError, ValueError):
            layer_number = 0
        return [max(1, layer_number - index) for index in range(max(0, int(count or 0)))]

    def _qwidget_paste_coordinates(self, local_pos, clip_ids, tran_ids):
        """Resolve paste coordinates for the QWidget timeline backend."""
        if ViewClass != TimelineWidget:
            return 0.0, 0

        seconds = 0.0
        if hasattr(self, "_seconds_from_x"):
            seconds = max(0.0, float(self._seconds_from_x(local_pos.x())))

        local_posf = QPointF(local_pos)
        track_number = None
        if hasattr(self, "geometry"):
            self.geometry.ensure()
            track_iter = getattr(self.geometry, "iter_tracks", None)
            if callable(track_iter):
                track_entries = track_iter()
            else:
                track_entries = getattr(self.geometry, "track_rects", [])

            for track_rect, track, _name_rect in track_entries:
                if track_rect.contains(local_posf):
                    track_number = track.data.get("number")
                    break

        if track_number is None and clip_ids:
            clip = Clip.get(id=clip_ids[0])
            if clip:
                track_number = clip.data.get("layer")

        if track_number is None and tran_ids:
            tran = Transition.get(id=tran_ids[0])
            if tran:
                track_number = tran.data.get("layer")

        if track_number is None:
            selected_tracks = getattr(self.window, "selected_tracks", [])
            if selected_tracks:
                track = Track.get(id=selected_tracks[0])
                if track:
                    track_number = track.data.get("number")

        if track_number is None:
            track_number = 0

        return seconds, track_number

    def _apply_effect_colors(self, value):
        """Ensure effect dictionaries define a color attribute."""
        if isinstance(value, dict):
            effects = value.get("effects")
            if isinstance(effects, list):
                for effect in effects:
                    if not isinstance(effect, dict):
                        continue
                    ui_data = effect.get("ui")
                    if not isinstance(ui_data, dict):
                        ui_data = {}
                        effect["ui"] = ui_data
                    ui_data.setdefault("icon_color", effect_color_hex(effect))
                    self._apply_effect_colors(effect)
            for key, sub_value in value.items():
                if key in ("effects", "ui", "audio_data"):
                    continue
                if isinstance(sub_value, (dict, list)):
                    self._apply_effect_colors(sub_value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    self._apply_effect_colors(item)

    def _should_refresh_waveforms(self, action):
        """Determine if a project update requires redrawing clip waveforms."""
        if not action:
            return False
        if action.type == "load":
            return True
        if not action.key or action.key[0] != "clips":
            return False

        if self._payload_contains_waveform(action.values):
            return True

        clip_ids = set()
        for part in action.key:
            if isinstance(part, dict) and part.get("id"):
                clip_ids.add(str(part["id"]))

        if not clip_ids:
            self._collect_clip_ids_from_value(action.values, clip_ids)

        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip:
                continue
            audio_data = clip.data.get("ui", {}).get("audio_data")
            if isinstance(audio_data, list) and len(audio_data) > 0:
                return True
        return False

    
    def changed(self, action):
        if action is None:
            if ViewClass == TimelineWidget:
                TimelineWidget.changed(self, None)
            return

        if ViewClass == TimelineWidget and self._pending_trim_refresh:
            pending = self._pending_trim_refresh
            item_id = pending.get("id")
            if item_id and action and action.key and action.key[0] in ["clips", "transitions"]:
                if self._action_contains_item_id(action, item_id):
                    self._apply_pending_trim_refresh()

        try:
            
            action = action.copy()
            action.old_values = {}
        except:
            log.error("Error duplicating UpdateAction", exc_info=1)
            return

        
        if action and len(action.key) >= 1 and action.key[0] not in ["clips", "effects", "duration", "layers", "markers"]:
            log.debug(f"Skipping unneeded timeline update for '{action.key[0]}'")
            return

        redraw_waveforms = self._should_refresh_waveforms(action)

        if ViewClass == TimelineWidget:
            
            TimelineWidget.changed(self, action)
            if action and action.type == "load":
                initial_scale = float(get_app().project.get("scale") or 15.0)
                TimelineWidget.setZoomFactor(self, initial_scale, emit=False)
            return

        
        if action.type == "load":
            
            self.run_js(JS_SCOPE_SELECTOR + ".setThumbAddress('" + self.get_thumb_address() + "');")

            _ = get_app()._tr
            
            self.run_js(JS_SCOPE_SELECTOR + ".setTrackLabel('" + _("Track %s") + "');")

            
            self.run_js(JS_SCOPE_SELECTOR + ".loadJson(" + action.json() + ");")

        elif action.key[0] != "files":
            
            self.run_js(JS_SCOPE_SELECTOR + ".applyJsonDiff([" + action.json() + "]);")

        
        if action.type == "load":
            
            initial_scale = float(get_app().project.get("scale") or 15.0)
            self.window.sliderZoomWidget.setZoomFactor(initial_scale)

        if redraw_waveforms:
            self.redraw_audio_timer.start()

    def _extend_timeline_to_fit_items(self):
        """Extend project duration to cover all clips/transitions."""
        
        update_duration = getattr(self, "_update_project_duration", None)
        if callable(update_duration):
            try:
                update_duration()
                return
            except Exception:
                log.warning("Failed to update project duration via widget helper", exc_info=1)

        furthest = 0.0
        for clip in Clip.filter():
            data = clip.data if isinstance(clip.data, dict) else {}
            position = float(data.get("position", 0.0) or 0.0)
            start = float(data.get("start", 0.0) or 0.0)
            end = float(data.get("end", start) or start)
            duration = max(0.0, end - start)
            furthest = max(furthest, position + duration)
        for tran in Transition.filter():
            data = tran.data if isinstance(tran.data, dict) else {}
            position = float(data.get("position", 0.0) or 0.0)
            start = float(data.get("start", 0.0) or 0.0)
            end = float(data.get("end", start) or start)
            duration = max(0.0, end - start)
            furthest = max(furthest, position + duration)

        min_length = 300.0
        padding = 10.0
        desired = max(min_length, furthest + padding)
        current = float(get_app().project.get("duration") or 0.0)
        if desired > current + 1e-3:
            self.resizeTimeline(desired)

    def delete_invalid_timeline_item(self, item):
        """Delete an invalid timeline item (clip or transitions) if the basic
           data does not make sense - i.e. negative duration"""
        
        if item.data["position"] < 0.0:
            item.data["position"] = 0.0
        if item.data["start"] < 0.0:
            item.data["start"] = 0.0
        if item.data["end"] < item.data["start"]:
            item.data["end"] = item.data["start"]
        if item.data["end"] - item.data["start"] <= 0.0:
            log.warning("Negative or zero duration is not possible, so deleting item instead: item_id: %s" % item.id)
            get_app().window.clearSelections()
            item.delete()
            return True
        return False

    @pyqtSlot(str, bool, bool, bool, str)
    def update_clip_data(
        self, clip_json, only_basic_props=True, ignore_reader=False,
        ignore_refresh=False, transaction_id=None
    ):
        """ Javascript callable function to update the project data when a clip changes.
        Create an updateAction and send it to the update manager.
        Transaction ID is for undo/redo grouping (if any) """

        
        try:
            if not isinstance(clip_json, dict):
                clip_data = json.loads(clip_json)
            else:
                clip_data = clip_json
        except Exception:
            
            log.warning('Failed to parse clip JSON data', exc_info=1)
            return
        auto_transition = bool(clip_data.pop("_auto_transition", False))

        self._apply_effect_colors(clip_data)

        
        existing_clip = Clip.get(id=clip_data.get("id"))
        if not existing_clip:
            
            log.debug("Create new clip object from clip_data: %s" % clip_data)
            existing_clip = Clip()

        
        clamp_timing_to_media(clip_data, existing_clip)

        
        existing_clip.data = clip_data

        
        if only_basic_props:
            existing_clip.data = {}
            existing_clip.data["id"] = clip_data["id"]
            existing_clip.data["layer"] = clip_data["layer"]
            existing_clip.data["position"] = clip_data["position"]
            existing_clip.data["start"] = clip_data["start"]
            existing_clip.data["end"] = clip_data["end"]
            existing_clip.data["duration"] = clip_data.get("duration")

        
        if self.delete_invalid_timeline_item(existing_clip):
            return

        
        
        if ignore_reader and "reader" in existing_clip.data:
            existing_clip.data.pop("reader")

        
        if transaction_id:
            get_app().updates.transaction_id = transaction_id

        
        existing_clip.save()

        if transaction_id:
            get_app().updates.transaction_id = None

        if auto_transition:
            missing_transition = self._find_missing_transition_details(existing_clip.data)
            if missing_transition is not None:
                self.add_missing_transition(json.dumps(missing_transition))

        
        self.window.IgnoreUpdates.emit(ignore_refresh, self.show_wait_spinner)

    
    @pyqtSlot(str)
    def add_missing_transition(self, transition_json):
        if not get_app().get_settings().get("automatic_transitions"):
            log.debug("Skipping auto transition (disabled in settings)")
            return

        transition_details = json.loads(transition_json)

        transition_path = os.path.join(info.PATH, "transitions", "common", "fade.svg")
        reader_data = self._load_transition_reader_data(transition_path)
        if not reader_data:
            log.warning("Unable to load default transition image: %s", transition_path)
            return

        
        transitions_data = {
            "id": get_app().project.generate_id(),
            "layer": transition_details["layer"],
            "title": "Transition",
            "type": "Mask",
            "position": transition_details["position"],
            "start": transition_details["start"],
            "end": transition_details["end"],
            "reader": reader_data,
            "fade_audio_hint": True,
            "replace_image": False
        }
        self._set_transition_mask_defaults(transitions_data)

        
        self.update_transition_data(transitions_data, only_basic_props=False)

    def _find_missing_transition_details(self, clip_data):
        """Return auto-transition details for one overlap on the clip's layer, or None."""
        if not isinstance(clip_data, dict):
            return None

        try:
            clip_layer = int(clip_data.get("layer", 0))
            original_left = float(clip_data.get("position", 0.0))
            original_duration = float(clip_data.get("end", 0.0)) - float(clip_data.get("start", 0.0))
        except (TypeError, ValueError):
            return None
        if original_duration <= 0.0:
            return None

        original_right = original_left + original_duration
        original_id = clip_data.get("id")
        transition_size = None

        def _clip_pos(clip_obj):
            try:
                return float(((clip_obj.data or {}).get("position", 0.0)))
            except (TypeError, ValueError):
                return 0.0

        same_layer_clips = sorted(Clip.filter(layer=clip_layer), key=_clip_pos)
        for clip in same_layer_clips:
            data = clip.data if isinstance(clip.data, dict) else {}
            if data.get("id") == original_id:
                continue
            try:
                clip_left = float(data.get("position", 0.0))
                clip_right = clip_left + (float(data.get("end", 0.0)) - float(data.get("start", 0.0)))
            except (TypeError, ValueError):
                continue

            if original_left < clip_right and original_left > clip_left:
                transition_size = {
                    "position": original_left,
                    "layer": clip_layer,
                    "start": 0.0,
                    "end": (clip_right - original_left),
                }
            elif original_right > clip_left and original_right < clip_right:
                transition_size = {
                    "position": clip_left,
                    "layer": clip_layer,
                    "start": 0.0,
                    "end": (original_right - clip_left),
                }

            if transition_size is not None and transition_size["end"] >= 0.5:
                break
            if transition_size is not None and transition_size["end"] < 0.5:
                transition_size = None

        if transition_size is None:
            return None

        new_left = transition_size["position"]
        new_right = transition_size["position"] + (transition_size["end"] - transition_size["start"])
        tolerance = 0.01
        for tran in Transition.filter(layer=clip_layer):
            tran_data = tran.data if isinstance(tran.data, dict) else {}
            try:
                tran_left = float(tran_data.get("position", 0.0))
                tran_right = tran_left + (float(tran_data.get("end", 0.0)) - float(tran_data.get("start", 0.0)))
            except (TypeError, ValueError):
                continue
            if abs(tran_left - new_left) < tolerance or abs(tran_right - new_right) < tolerance:
                return None

        return transition_size

    def _scale_keyframes(self, keyframe, factor):
        """Scale the X values of keyframe points"""
        for point in keyframe.get("Points", []):
            if "co" in point and "X" in point["co"] and point["co"]["X"] != 1:
                point["co"]["X"] = round((point["co"]["X"] - 1) * factor) + 1

    def _anchor_transition_endpoint_keyframes(self, transition_data, total_frames):
        """Keep static transition endpoint keyframes anchored to the clip edges."""
        if total_frames <= 0 or not isinstance(transition_data, dict):
            return
        last_frame = int(total_frames) + 1
        for prop in ("brightness", "contrast"):
            keyframe = transition_data.get(prop)
            points = keyframe.get("Points") if isinstance(keyframe, dict) else None
            if not isinstance(points, list) or len(points) < 2:
                continue
            first = points[0].get("co") if isinstance(points[0], dict) else None
            last = points[-1].get("co") if isinstance(points[-1], dict) else None
            if isinstance(first, dict):
                first["X"] = 1
            if isinstance(last, dict):
                last["X"] = last_frame

    def _transition_mask_reader(self, transition_data, fallback_data=None):
        """Return reader metadata for a transition payload."""
        if isinstance(transition_data, dict):
            for key in ("mask_reader", "reader"):
                reader = transition_data.get(key)
                if isinstance(reader, dict):
                    return reader
        if isinstance(fallback_data, dict):
            for key in ("mask_reader", "reader"):
                reader = fallback_data.get(key)
                if isinstance(reader, dict):
                    return reader
        return {}

    def _transition_uses_static_mask(self, transition_data, fallback_data=None):
        """Return True when a transition uses a static single-image mask."""
        reader = self._transition_mask_reader(transition_data, fallback_data)
        if "has_single_image" in reader:
            return bool(reader.get("has_single_image"))
        return bool(is_single_image_media(reader))

    def _transition_reader_changed(self, transition_data, fallback_data=None):
        """Return True when the transition reader source changed."""
        new_reader = self._transition_mask_reader(transition_data, fallback_data)
        old_reader = self._transition_mask_reader(fallback_data, None)

        if not isinstance(fallback_data, dict):
            return False
        if not new_reader and not old_reader:
            return False

        for key in ("id", "path", "type", "has_single_image", "video_length", "duration"):
            if new_reader.get(key) != old_reader.get(key):
                return True
        return new_reader != old_reader

    def _build_transition_default_keyframes(self, duration, start_value, end_value, contrast_value):
        """Build default brightness/contrast keyframes for a transition."""
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        duration = max(0.0, float(duration or 0.0))

        brightness = smartedit.Keyframe()
        brightness.AddPoint(1, float(start_value), smartedit.BEZIER)
        if float(start_value) != float(end_value):
            brightness.AddPoint(round(duration * fps_float) + 1, float(end_value), smartedit.BEZIER)
        contrast = smartedit.Keyframe(float(contrast_value))
        return json.loads(brightness.Json()), json.loads(contrast.Json())

    def _set_transition_mask_defaults(self, transition_data, fallback_data=None):
        """Normalize timing/keyframes for static vs animated transition masks."""
        if not isinstance(transition_data, dict):
            return transition_data

        start = float(transition_data.get("start", 0.0) or 0.0)
        end = float(transition_data.get("end", start) or start)
        if end < start:
            end = start
        duration = max(0.0, end - start)

        if self._transition_uses_static_mask(transition_data, fallback_data):
            transition_data["start"] = 0.0
            transition_data["end"] = duration
            brightness, contrast = self._build_transition_default_keyframes(duration, 1.0, -1.0, 3.0)
            mode = "static"
        else:
            transition_data["start"] = start
            transition_data["end"] = end
            brightness, contrast = self._build_transition_default_keyframes(duration, 0.0, 0.0, 0.0)
            mode = "animated"

        transition_data["duration"] = max(
            0.0,
            float(transition_data.get("end", 0.0) or 0.0) - float(transition_data.get("start", 0.0) or 0.0),
        )
        transition_data["brightness"] = brightness
        transition_data["contrast"] = contrast
        return transition_data

    def _reverse_keyframes(self, keyframe, total_frames):
        """Reverse keyframe positions, swapping handles"""
        points = keyframe.get("Points", [])
        x_values = [
            point["co"]["X"]
            for point in points
            if isinstance(point.get("co"), dict) and "X" in point["co"]
        ]

        if not x_values:
            return

        min_x = min(x_values)
        max_x = max(x_values)

        
        
        
        
        pivot = min_x + max_x

        new_points = []
        for point in points:
            new_point = json.loads(json.dumps(point))
            if isinstance(new_point.get("co"), dict) and "X" in new_point["co"]:
                new_point["co"]["X"] = pivot - point["co"]["X"]
                hl = new_point.pop("handle_left", None)
                hr = new_point.pop("handle_right", None)
                if hr is not None:
                    new_point["handle_left"] = hr
                if hl is not None:
                    new_point["handle_right"] = hl
            new_points.append(new_point)

        keyframe["Points"] = sorted(
            new_points,
            key=lambda p: p.get("co", {}).get("X", 0)
        )

    def _infer_transition_drop_side(self, transition_data):
        """Return 'left' or 'right' based on which side of a clip the transition overlaps."""
        if not isinstance(transition_data, dict):
            return None

        try:
            layer = int(transition_data.get("layer", 0))
            position = float(transition_data.get("position", 0.0))
            start = float(transition_data.get("start", 0.0))
            end = float(transition_data.get("end", 0.0))
        except (TypeError, ValueError):
            return None

        duration = max(0.0, end - start)
        if duration <= 0.0:
            return None

        tran_left = position
        tran_right = position + duration
        tran_mid = (tran_left + tran_right) / 2.0
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        edge_tolerance = (0.5 / fps_float) if fps_float > 0 else 0.01

        edge_matches = set()
        overlap_candidates = []

        for clip in Clip.filter(layer=layer):
            clip_data = clip.data if isinstance(clip.data, dict) else {}
            try:
                clip_left = float(clip_data.get("position", 0.0))
                clip_start = float(clip_data.get("start", 0.0))
                clip_end = float(clip_data.get("end", 0.0))
            except (TypeError, ValueError):
                continue

            clip_duration = max(0.0, clip_end - clip_start)
            if clip_duration <= 0.0:
                continue

            clip_right = clip_left + clip_duration
            overlap = min(tran_right, clip_right) - max(tran_left, clip_left)
            if overlap <= 0.0:
                continue

            if abs(tran_left - clip_left) <= edge_tolerance:
                edge_matches.add("left")
            if abs(tran_right - clip_right) <= edge_tolerance:
                edge_matches.add("right")

            clip_mid = (clip_left + clip_right) / 2.0
            side = "left" if tran_mid <= clip_mid else "right"
            edge_dist = abs(tran_mid - (clip_left if side == "left" else clip_right))
            overlap_candidates.append(((-overlap, edge_dist), side))

        if len(edge_matches) == 1:
            return edge_matches.pop()
        if len(edge_matches) > 1:
            
            
            
            
            return "left"
        if not overlap_candidates:
            return None

        overlap_candidates.sort(key=lambda candidate: candidate[0])
        best_score, best_side = overlap_candidates[0]

        
        
        if len(overlap_candidates) > 1 and overlap_candidates[1][0] == best_score:
            tied_sides = {best_side, overlap_candidates[1][1]}
            if "left" in tied_sides:
                return "left"
            return best_side

        return best_side

    def _auto_orient_transition_keyframes(self, transition_data):
        """Apply fade-in orientation on left-edge drops (right edge keeps default orientation)."""
        if not self._transition_uses_static_mask(transition_data):
            return
        target_side = self._infer_transition_drop_side(transition_data)
        if target_side not in ("left", "right"):
            return

        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        try:
            duration = float(transition_data.get("end", 0.0)) - float(transition_data.get("start", 0.0))
        except (TypeError, ValueError):
            duration = 0.0
        total_frames = max(1, round(max(0.0, duration) * fps_float))

        
        current_side = None
        brightness = transition_data.get("brightness")
        if isinstance(brightness, dict):
            points = brightness.get("Points", [])
            keyed = []
            for point in points:
                co = point.get("co") if isinstance(point, dict) else None
                if not isinstance(co, dict):
                    continue
                x = co.get("X")
                y = co.get("Y")
                if x is None or y is None:
                    continue
                try:
                    keyed.append((float(x), float(y)))
                except (TypeError, ValueError):
                    continue
            if len(keyed) >= 2:
                keyed.sort(key=lambda k: k[0])
                first_y = keyed[0][1]
                last_y = keyed[-1][1]
                if first_y < last_y:
                    current_side = "right"
                elif first_y > last_y:
                    current_side = "left"

        
        
        if current_side is None:
            return

        if current_side == target_side:
            return

        for prop in ("brightness", "contrast"):
            keyframe = transition_data.get(prop)
            if isinstance(keyframe, dict):
                self._reverse_keyframes(keyframe, total_frames)

    
    @pyqtSlot(str, bool, bool, str)
    def update_transition_data(self, transition_json, only_basic_props=True, ignore_refresh=False, transaction_id=None):
        """Create an updateAction and send it to the update manager.
        Transaction ID is for undo/redo grouping (if any)"""

        
        if not isinstance(transition_json, dict):
            transition_data = json.loads(transition_json)
        else:
            transition_data = transition_json
        auto_direction = bool(transition_data.pop("_auto_direction", False))

        
        existing_item = Transition.get(id=transition_data["id"])
        old_data = json.loads(json.dumps(existing_item.data)) if existing_item else {}
        if not existing_item:
            
            existing_item = Transition()
        existing_item.data = transition_data

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])

        
        old_duration = old_data.get("end", 0.0) - old_data.get("start", 0.0)
        new_duration = existing_item.data.get("end", 0.0) - existing_item.data.get("start", 0.0)
        old_frames = round(old_duration * fps_float) if old_duration > 0 else 0
        new_frames = round(new_duration * fps_float) if new_duration > 0 else 0
        uses_static_mask = self._transition_uses_static_mask(existing_item.data, old_data)

        if old_data and only_basic_props:
            if "brightness" in old_data:
                existing_item.data["brightness"] = old_data["brightness"]
            if "contrast" in old_data:
                existing_item.data["contrast"] = old_data["contrast"]

            if uses_static_mask and old_frames and new_frames and old_frames != new_frames:
                scale = new_frames / old_frames
                for prop in ("brightness", "contrast"):
                    if prop in existing_item.data:
                        self._scale_keyframes(existing_item.data[prop], scale)
            if uses_static_mask and new_frames:
                self._anchor_transition_endpoint_keyframes(existing_item.data, new_frames)
        elif old_data and self._transition_reader_changed(existing_item.data, old_data):
            self._set_transition_mask_defaults(existing_item.data, old_data)

        if auto_direction and uses_static_mask:
            self._auto_orient_transition_keyframes(existing_item.data)

        
        if only_basic_props and not old_data:
            existing_item.data = {}
            existing_item.data["id"] = transition_data["id"]
            existing_item.data["layer"] = transition_data["layer"]
            existing_item.data["position"] = transition_data["position"]
            existing_item.data["start"] = transition_data["start"]
            existing_item.data["end"] = transition_data["end"]
            existing_item.data["brightness"] = transition_data.get("brightness", {})
            existing_item.data["contrast"] = transition_data.get("contrast", {})

        
        if self.delete_invalid_timeline_item(existing_item):
            return

        
        if transaction_id:
            get_app().updates.transaction_id = transaction_id

        
        existing_item.save()

        if transaction_id:
            get_app().updates.transaction_id = None

        
        self.window.IgnoreUpdates.emit(ignore_refresh, self.show_wait_spinner)

    
    def contextMenuEvent(self, event):
        event.ignore()

    
    @pyqtSlot(float)
    def ShowPlayheadMenu(self, position=None):
        log.debug('ShowPlayheadMenu: %s' % position)
        self._context_menu_paste_data = None

        
        _ = get_app()._tr

        
        intersecting_clips = Clip.filter(intersect=position)
        intersecting_trans = Transition.filter(intersect=position)

        menu = StyledContextMenu(parent=self)
        if intersecting_clips or intersecting_trans:
            
            clip_ids = [c.id for c in intersecting_clips]
            trans_ids = [t.id for t in intersecting_trans]

            
            Slice_Menu = StyledContextMenu(title=_("Slice All"), parent=self)
            Slice_Keep_Both = Slice_Menu.addAction(_("Keep Both Sides"))
            Slice_Keep_Both.setShortcuts(self.window.getShortcutByName("sliceAllKeepBothSides"))
            Slice_Keep_Both.triggered.connect(partial(
                self.Slice_Triggered, MenuSlice.KEEP_BOTH, clip_ids, trans_ids, position))
            Slice_Keep_Left = Slice_Menu.addAction(_("Keep Left Side"))
            Slice_Keep_Left.setShortcuts(self.window.getShortcutByName("sliceAllKeepLeftSide"))
            Slice_Keep_Left.triggered.connect(partial(
                self.Slice_Triggered, MenuSlice.KEEP_LEFT, clip_ids, trans_ids, position))
            Slice_Keep_Right = Slice_Menu.addAction(_("Keep Right Side"))
            Slice_Keep_Right.setShortcuts(self.window.getShortcutByName("sliceAllKeepRightSide"))
            Slice_Keep_Right.triggered.connect(partial(
                self.Slice_Triggered, MenuSlice.KEEP_RIGHT, clip_ids, trans_ids, position))
            menu.addMenu(Slice_Menu)

            
            Cache_Menu = StyledContextMenu(title=_("Cache"), parent=self)
            Cache_Menu.addAction(self.window.actionClearAllCache)
            menu.addMenu(Cache_Menu)

            
            self.context_menu_cursor_position = QCursor.pos()
            return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot(str)
    def ShowEffectMenu(self, effect_id=None):
        log.debug('ShowEffectMenu: %s' % effect_id)
        self._context_menu_paste_data = None

        
        _ = get_app()._tr

        menu = StyledContextMenu(parent=self)

        
        Copy_Menu = StyledContextMenu(title=_("Copy"), parent=self)
        Copy_Effect = Copy_Menu.addAction(_("Effect"))
        Copy_Effect.setShortcuts(self.window.getShortcutByName("copyAll"))
        Copy_Effect.triggered.connect(partial(self.Copy_Triggered, MenuCopy.EFFECT, [], [], [effect_id]))
        menu.addMenu(Copy_Menu)

        
        menu.addAction(self.window.actionProperties)

        
        menu.addSeparator()
        menu.addAction(self.window.actionRemoveEffect)

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot(float, int)
    def ShowTimelineMenu(self, position, layer_number):
        log.debug('ShowTimelineMenu: position: %s, layer: %s' % (position, layer_number))
        self._context_menu_paste_data = {
            "position": max(0.0, float(position)),
            "track": int(layer_number),
        }

        
        _ = get_app()._tr

        
        found_start = 0.0
        found_end = float('inf')
        found_gap = False

        
        copied_object = ClipboardManager.from_mime(get_app().clipboard().mimeData())

        
        has_clipboard = False
        if copied_object and isinstance(copied_object, Clip) and len(copied_object.data.keys()) > 20:
            has_clipboard = True
        elif copied_object and isinstance(copied_object, Transition) and len(copied_object.data.keys()) > 10:
            has_clipboard = True
        elif copied_object and isinstance(copied_object, list):
            has_clipboard = True

        
        clips_and_transitions = sorted(
            Clip.filter(layer=layer_number) + Transition.filter(layer=layer_number),
            key=lambda c: c.data.get("position", 0.0)
        )

        
        for clip in clips_and_transitions:
            left_edge = clip.data.get("position", 0.0)
            right_edge = left_edge + (clip.data.get("end", 0.0) - clip.data.get("start", 0.0))

            
            if left_edge > found_start and left_edge > position:
                found_end = left_edge
                found_gap = True
                break  

            
            found_start = max(found_start, right_edge)

        
        track = Track.get(number=layer_number)
        if not track:
            return
        locked = track.data.get("lock", False)
        if locked and (has_clipboard or found_gap):
            return

        
        menu = StyledContextMenu(parent=self)

        has_edit_actions = False

        if found_gap:
            
            menu.addAction(self.window.actionRemoveGap)
            try:
                
                self.window.actionRemoveGap.triggered.disconnect()
            except TypeError:
                pass  
            self.window.actionRemoveGap.triggered.connect(
                partial(self.RemoveGap_Triggered, found_start, found_end, int(layer_number))
            )
            has_edit_actions = True
        if has_clipboard:
            
            Paste_Clip = menu.addAction(_("Paste"))
            Paste_Clip.setShortcuts(self.window.getShortcutByName("pasteAll"))
            Paste_Clip.triggered.connect(
                partial(self.Paste_Triggered, MenuCopy.PASTE, [], [])
            )
            has_edit_actions = True

        if not has_edit_actions:
            return

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot()
    def ShowProperties(self):
        """Show the Properties dock (triggered by double-click on a clip/transition)."""
        self.window.actionProperties.trigger()

    @pyqtSlot(str)
    def ShowClipMenu(self, clip_id=None):
        log.debug('ShowClipMenu: %s' % clip_id)
        self._context_menu_paste_data = None

        
        _ = get_app()._tr

        
        clip = Clip.get(id=clip_id)
        if not clip:
            
            return

        
        clip_ids = self.window.selected_clips
        tran_ids = self.window.selected_transitions

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])

        
        _reader = clip.data.get("reader", {}) if clip else {}
        clip_has_visual = bool(_reader.get("has_video", True)) or bool(clip.data.get("waveform", False))
        clip_has_audio = bool(_reader.get("has_audio", True))

        
        playhead_position = float(self.window.preview_thread.current_frame - 1) / fps_float

        
        copied_object = ClipboardManager.from_mime(get_app().clipboard().mimeData())
        has_clipboard = False
        if copied_object and isinstance(copied_object, Clip):
            has_clipboard = True
        elif copied_object and isinstance(copied_object, Effect):
            has_clipboard = True

        
        menu = StyledContextMenu(parent=self)

        
        if len(tran_ids) + len(clip_ids) > 1:
            
            Copy_All = menu.addAction(_("Copy"))
            Copy_All.setShortcuts(self.window.getShortcutByName("copyAll"))
            Copy_All.triggered.connect(self.window.copyAll)
            
            Cut_All = menu.addAction(_("Cut"))
            Cut_All.setShortcuts(self.window.getShortcutByName("cutAll"))
            Cut_All.triggered.connect(self.window.cutAll)
        else:
            
            Copy_Menu = StyledContextMenu(title=_("Copy"), parent=self)
            Copy_Clip = Copy_Menu.addAction(_("Clip"))
            Copy_Clip.setShortcuts(self.window.getShortcutByName("copyAll"))
            Copy_Clip.triggered.connect(partial(self.Copy_Triggered, MenuCopy.CLIP, [clip_id], [], []))

            Keyframe_Menu = StyledContextMenu(title=_("Keyframes"), parent=self)
            Copy_Keyframes_All = Keyframe_Menu.addAction(_("All"))
            Copy_Keyframes_All.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_ALL, [clip_id], [], []))
            Keyframe_Menu.addSeparator()
            Copy_Keyframes_Alpha = Keyframe_Menu.addAction(_("Alpha"))
            Copy_Keyframes_Alpha.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_ALPHA, [clip_id], [], []))
            Copy_Keyframes_Scale = Keyframe_Menu.addAction(_("Scale"))
            Copy_Keyframes_Scale.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_SCALE, [clip_id], [], []))
            Copy_Keyframes_Shear = Keyframe_Menu.addAction(_("Shear"))
            Copy_Keyframes_Shear.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_SHEAR, [clip_id], [], []))
            Copy_Keyframes_Rotate = Keyframe_Menu.addAction(_("Rotation"))
            Copy_Keyframes_Rotate.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_ROTATE, [clip_id], [], []))
            Copy_Keyframes_Locate = Keyframe_Menu.addAction(_("Location"))
            Copy_Keyframes_Locate.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_LOCATION, [clip_id], [], []))
            Copy_Keyframes_Time = Keyframe_Menu.addAction(_("Time"))
            Copy_Keyframes_Time.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_TIME, [clip_id], [], []))
            Copy_Keyframes_Volume = Keyframe_Menu.addAction(_("Volume"))
            Copy_Keyframes_Volume.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_VOLUME, [clip_id], [], []))

            
            Copy_Effects = Copy_Menu.addAction(_("Effects"))
            Copy_Effects.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.ALL_EFFECTS, [clip_id], [], []))
            Copy_Menu.addMenu(Keyframe_Menu)
            menu.addMenu(Copy_Menu)

            
            Cut_All = menu.addAction(_("Cut"))
            Cut_All.setShortcuts(self.window.getShortcutByName("cutAll"))
            Cut_All.triggered.connect(self.window.cutAll)

        
        if has_clipboard:
            
            Paste_Clip = menu.addAction(_("Paste"))
            Paste_Clip.triggered.connect(partial(self.Paste_Triggered, MenuCopy.PASTE, clip_ids, []))

        menu.addSeparator()

        
        if len(clip_ids) > 1:
            Alignment_Menu = StyledContextMenu(title=_("Align"), parent=self)
            Align_Left = Alignment_Menu.addAction(_("Left"))
            Align_Left.triggered.connect(partial(self.Align_Triggered, MenuAlign.LEFT, clip_ids, tran_ids))
            Align_Right = Alignment_Menu.addAction(_("Right"))
            Align_Right.triggered.connect(partial(self.Align_Triggered, MenuAlign.RIGHT, clip_ids, tran_ids))

            
            menu.addMenu(Alignment_Menu)

        
        Fade_Menu = StyledContextMenu(title=_("Fade"), parent=self)
        Fade_None = Fade_Menu.addAction(_("No Fade"))
        Fade_None.triggered.connect(partial(self.Fade_Triggered, MenuFade.NONE, clip_ids))
        Fade_Menu.addSeparator()

        Fade_In_Menu = StyledContextMenu(title=_("Fade In"), parent=self)
        Fade_In_Fast = Fade_In_Menu.addAction(_("Fast"))
        Fade_In_Fast.triggered.connect(partial(self.Fade_Triggered, MenuFade.IN_FAST, clip_ids, "Start of Clip"))
        Fade_In_Slow = Fade_In_Menu.addAction(_("Slow"))
        Fade_In_Slow.triggered.connect(partial(self.Fade_Triggered, MenuFade.IN_SLOW, clip_ids, "Start of Clip"))
        Fade_Menu.addMenu(Fade_In_Menu)

        Fade_Out_Menu = StyledContextMenu(title=_("Fade Out"), parent=self)
        Fade_Out_Fast = Fade_Out_Menu.addAction(_("Fast"))
        Fade_Out_Fast.triggered.connect(partial(self.Fade_Triggered, MenuFade.OUT_FAST, clip_ids, "End of Clip"))
        Fade_Out_Slow = Fade_Out_Menu.addAction(_("Slow"))
        Fade_Out_Slow.triggered.connect(partial(self.Fade_Triggered, MenuFade.OUT_SLOW, clip_ids, "End of Clip"))
        Fade_Menu.addMenu(Fade_Out_Menu)

        Fade_In_Out_Menu = StyledContextMenu(title=_("Fade In and Out"), parent=self)
        Fade_In_Out_Fast = Fade_In_Out_Menu.addAction(_("Fast"))
        Fade_In_Out_Fast.triggered.connect(partial(self.Fade_Triggered, MenuFade.IN_OUT_FAST, clip_ids, "Entire Clip"))
        Fade_In_Out_Slow = Fade_In_Out_Menu.addAction(_("Slow"))
        Fade_In_Out_Slow.triggered.connect(partial(self.Fade_Triggered, MenuFade.IN_OUT_SLOW, clip_ids, "Entire Clip"))
        Fade_Menu.addMenu(Fade_In_Out_Menu)

        menu.addMenu(Fade_Menu)

        
        Animate_Menu = StyledContextMenu(title=_("Motion"), parent=self)
        Animate_None = Animate_Menu.addAction(_("No Motion"))
        Animate_None.triggered.connect(partial(self.Animate_Triggered, MenuAnimate.NONE, clip_ids))
        Animate_Menu.addSeparator()

        def _motion_act(menu_obj, label, action):
            act = menu_obj.addAction(label)
            act.triggered.connect(partial(self.Animate_Triggered, action, clip_ids))

        def _motion_sub(title, items):
            sub = StyledContextMenu(title=title, parent=self)
            for label, action in items:
                _motion_act(sub, label, action)
            return sub

        
        In_Menu = StyledContextMenu(title=_("In"), parent=self)
        In_Menu.addMenu(_motion_sub(_("Back In"), [
            (_("From Bottom"), MenuAnimate.BACK_IN_UP),
            (_("From Left"),   MenuAnimate.BACK_IN_LEFT),
            (_("From Right"),  MenuAnimate.BACK_IN_RIGHT),
            (_("From Top"),    MenuAnimate.BACK_IN_DOWN),
        ]))
        _motion_act(In_Menu, _("Blur In"),   MenuAnimate.BLUR_IN)
        In_Menu.addMenu(_motion_sub(_("Bounce In"), [
            (_("Center"),      MenuAnimate.BOUNCE_IN),
            (_("From Bottom"), MenuAnimate.BOUNCE_IN_UP),
            (_("From Left"),   MenuAnimate.BOUNCE_IN_LEFT),
            (_("From Right"),  MenuAnimate.BOUNCE_IN_RIGHT),
            (_("From Top"),    MenuAnimate.BOUNCE_IN_DOWN),
        ]))
        In_Menu.addMenu(_motion_sub(_("Focus Wipe In"), [
            (_("Circle Expand"),  MenuAnimate.FOCUS_WIPE_IN_CIRCLE_EXPAND),
            (_("Circle Shrink"),  MenuAnimate.FOCUS_WIPE_IN_CIRCLE_SHRINK),
            (_("From Bottom"),    MenuAnimate.FOCUS_WIPE_IN_BOTTOM),
            (_("From Left"),      MenuAnimate.FOCUS_WIPE_IN_LEFT),
            (_("From Right"),     MenuAnimate.FOCUS_WIPE_IN_RIGHT),
            (_("From Top"),       MenuAnimate.FOCUS_WIPE_IN_TOP),
        ]))
        _motion_act(In_Menu, _("Pop In"),    MenuAnimate.POP_IN)
        In_Menu.addMenu(_motion_sub(_("Slide In"), [
            (_("From Bottom"), MenuAnimate.SLIDE_IN_BOTTOM),
            (_("From Left"),   MenuAnimate.SLIDE_IN_LEFT),
            (_("From Right"),  MenuAnimate.SLIDE_IN_RIGHT),
            (_("From Top"),    MenuAnimate.SLIDE_IN_TOP),
        ]))
        _motion_act(In_Menu, _("Spiral In"), MenuAnimate.SPIRAL_IN)
        In_Menu.addMenu(_motion_sub(_("Wipe In"), [
            (_("Circle Expand"),  MenuAnimate.WIPE_IN_CIRCLE_EXPAND),
            (_("Circle Shrink"),  MenuAnimate.WIPE_IN_CIRCLE_SHRINK),
            (_("From Bottom"),    MenuAnimate.WIPE_IN_BOTTOM),
            (_("From Left"),      MenuAnimate.WIPE_IN_LEFT),
            (_("From Right"),     MenuAnimate.WIPE_IN_RIGHT),
            (_("From Top"),       MenuAnimate.WIPE_IN_TOP),
        ]))
        Animate_Menu.addMenu(In_Menu)

        
        Out_Menu = StyledContextMenu(title=_("Out"), parent=self)
        Out_Menu.addMenu(_motion_sub(_("Back Out"), [
            (_("To Bottom"), MenuAnimate.BACK_OUT_DOWN),
            (_("To Left"),   MenuAnimate.BACK_OUT_LEFT),
            (_("To Right"),  MenuAnimate.BACK_OUT_RIGHT),
            (_("To Top"),    MenuAnimate.BACK_OUT_UP),
        ]))
        _motion_act(Out_Menu, _("Blur Out"),  MenuAnimate.BLUR_OUT)
        Out_Menu.addMenu(_motion_sub(_("Bounce Out"), [
            (_("Center"),    MenuAnimate.BOUNCE_OUT),
            (_("To Bottom"), MenuAnimate.BOUNCE_OUT_DOWN),
            (_("To Left"),   MenuAnimate.BOUNCE_OUT_LEFT),
            (_("To Right"),  MenuAnimate.BOUNCE_OUT_RIGHT),
            (_("To Top"),    MenuAnimate.BOUNCE_OUT_UP),
        ]))
        Out_Menu.addMenu(_motion_sub(_("Focus Wipe Out"), [
            (_("Circle Expand"),  MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_EXPAND),
            (_("Circle Shrink"),  MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_SHRINK),
            (_("To Bottom"),      MenuAnimate.FOCUS_WIPE_OUT_BOTTOM),
            (_("To Left"),        MenuAnimate.FOCUS_WIPE_OUT_LEFT),
            (_("To Right"),       MenuAnimate.FOCUS_WIPE_OUT_RIGHT),
            (_("To Top"),         MenuAnimate.FOCUS_WIPE_OUT_TOP),
        ]))
        _motion_act(Out_Menu, _("Pop Out"),   MenuAnimate.POP_OUT)
        Out_Menu.addMenu(_motion_sub(_("Slide Out"), [
            (_("To Bottom"), MenuAnimate.SLIDE_OUT_BOTTOM),
            (_("To Left"),   MenuAnimate.SLIDE_OUT_LEFT),
            (_("To Right"),  MenuAnimate.SLIDE_OUT_RIGHT),
            (_("To Top"),    MenuAnimate.SLIDE_OUT_TOP),
        ]))
        _motion_act(Out_Menu, _("Spiral Out"), MenuAnimate.SPIRAL_OUT)
        Out_Menu.addMenu(_motion_sub(_("Wipe Out"), [
            (_("Circle Expand"),  MenuAnimate.WIPE_OUT_CIRCLE_EXPAND),
            (_("Circle Shrink"),  MenuAnimate.WIPE_OUT_CIRCLE_SHRINK),
            (_("To Bottom"),      MenuAnimate.WIPE_OUT_BOTTOM),
            (_("To Left"),        MenuAnimate.WIPE_OUT_LEFT),
            (_("To Right"),       MenuAnimate.WIPE_OUT_RIGHT),
            (_("To Top"),         MenuAnimate.WIPE_OUT_TOP),
        ]))
        Animate_Menu.addMenu(Out_Menu)

        
        Animate_Menu.addMenu(_motion_sub(_("Emphasis"), [
            (_("Bounce"),      MenuAnimate.BOUNCE),
            (_("Flash"),       MenuAnimate.FLASH),
            (_("Heartbeat"),   MenuAnimate.HEART_BEAT),
            (_("Jello"),       MenuAnimate.JELLO),
            (_("Pulse"),       MenuAnimate.PULSE),
            (_("Rubber Band"), MenuAnimate.RUBBER_BAND),
            (_("Shake X"),     MenuAnimate.SHAKE_X),
            (_("Shake Y"),     MenuAnimate.SHAKE_Y),
            (_("Swing"),       MenuAnimate.SWING),
            (_("Tada"),        MenuAnimate.TADA),
            (_("Wobble"),      MenuAnimate.WOBBLE),
        ]))

        
        Camera_Menu = StyledContextMenu(title=_("Camera"), parent=self)
        Camera_Menu.addMenu(_motion_sub(_("Zoom"), [
            (_("In"),  MenuAnimate.CAM_PUSH_IN),
            (_("Out"), MenuAnimate.CAM_PULL_OUT),
        ]))
        Camera_Menu.addMenu(_motion_sub(_("Pan"), [
            (_("Auto Direction"), MenuAnimate.CAM_PAN_AUTO),
            (_("Left to Right"),  MenuAnimate.CAM_PAN_RIGHT),
            (_("Right to Left"),  MenuAnimate.CAM_PAN_LEFT),
            (_("Top to Bottom"),  MenuAnimate.CAM_PAN_DOWN),
            (_("Bottom to Top"),  MenuAnimate.CAM_PAN_UP),
        ]))
        Zoom_Pan_Menu = StyledContextMenu(title=_("Zoom & Pan").replace("&", "&&"), parent=self)
        Zoom_Pan_Menu.addMenu(_motion_sub(_("In"), [
            (_("Auto Direction"),  MenuAnimate.KEN_BURNS_IN),
            (_("Left to Right"),   MenuAnimate.KEN_BURNS_IN_LEFT_TO_RIGHT),
            (_("Right to Left"),   MenuAnimate.KEN_BURNS_IN_RIGHT_TO_LEFT),
            (_("Top to Bottom"),   MenuAnimate.KEN_BURNS_IN_TOP_TO_BOTTOM),
            (_("Bottom to Top"),   MenuAnimate.KEN_BURNS_IN_BOTTOM_TO_TOP),
        ]))
        Zoom_Pan_Menu.addMenu(_motion_sub(_("Out"), [
            (_("Auto Direction"),  MenuAnimate.KEN_BURNS_OUT),
            (_("Left to Right"),   MenuAnimate.KEN_BURNS_OUT_LEFT_TO_RIGHT),
            (_("Right to Left"),   MenuAnimate.KEN_BURNS_OUT_RIGHT_TO_LEFT),
            (_("Top to Bottom"),   MenuAnimate.KEN_BURNS_OUT_TOP_TO_BOTTOM),
            (_("Bottom to Top"),   MenuAnimate.KEN_BURNS_OUT_BOTTOM_TO_TOP),
        ]))
        Camera_Menu.addMenu(Zoom_Pan_Menu)
        Animate_Menu.addMenu(Camera_Menu)

        
        Animate_Menu.addMenu(_motion_sub(_("Credits"), [
            (_("Scroll Up"),   MenuAnimate.CREDITS_UP),
            (_("Scroll Down"), MenuAnimate.CREDITS_DOWN),
        ]))

        if clip_has_visual:
            menu.addMenu(Animate_Menu)

        
        Transform_Menu = StyledContextMenu(title=_("Transform"), parent=self)
        No_Transform = Transform_Menu.addAction(_("No Transform"))
        No_Transform.triggered.connect(partial(self.No_Transform_Triggered, clip_ids))
        Transform_Menu.addSeparator()

        Rotation_Menu = StyledContextMenu(title=_("Rotate"), parent=self)
        Rotation_None = Rotation_Menu.addAction(_("No Rotation"))
        Rotation_None.triggered.connect(partial(
            self.Rotate_Triggered, MenuRotate.NONE, clip_ids))
        Rotation_Menu.addSeparator()
        Rotation_90_Right = Rotation_Menu.addAction(_("Rotate 90 (Right)"))
        Rotation_90_Right.triggered.connect(partial(
            self.Rotate_Triggered, MenuRotate.RIGHT_90, clip_ids))
        Rotation_90_Left = Rotation_Menu.addAction(_("Rotate 90 (Left)"))
        Rotation_90_Left.triggered.connect(partial(
            self.Rotate_Triggered, MenuRotate.LEFT_90, clip_ids))
        Rotation_180_Flip = Rotation_Menu.addAction(_("Rotate 180 (Flip)"))
        Rotation_180_Flip.triggered.connect(partial(
            self.Rotate_Triggered, MenuRotate.FLIP_180, clip_ids))
        Transform_Menu.addMenu(Rotation_Menu)

        Crop_Menu = StyledContextMenu(title=_("Crop"), parent=self)
        Crop_None = Crop_Menu.addAction(_("No Crop"))
        Crop_None.triggered.connect(partial(self.Crop_Triggered, clip_ids, 'none'))
        Crop_Menu.addSeparator()
        Crop_NoResize = Crop_Menu.addAction(_("Crop (No Resize)"))
        Crop_NoResize.triggered.connect(partial(self.Crop_Triggered, clip_ids, 'crop'))
        Crop_Resize = Crop_Menu.addAction(_("Crop (Resize)"))
        Crop_Resize.triggered.connect(partial(self.Crop_Triggered, clip_ids, 'resize'))
        Transform_Menu.addMenu(Crop_Menu)

        Layout_Menu = StyledContextMenu(title=_("Layout"), parent=self)
        Layout_None = Layout_Menu.addAction(_("Reset Layout"))
        Layout_None.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.NONE, clip_ids))
        Layout_Menu.addSeparator()
        Layout_Center = Layout_Menu.addAction(_("1/4 Size - Center"))
        Layout_Center.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.CENTER, clip_ids))
        Layout_Top_Left = Layout_Menu.addAction(_("1/4 Size - Top Left"))
        Layout_Top_Left.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.TOP_LEFT, clip_ids))
        Layout_Top_Right = Layout_Menu.addAction(_("1/4 Size - Top Right"))
        Layout_Top_Right.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.TOP_RIGHT, clip_ids))
        Layout_Bottom_Left = Layout_Menu.addAction(_("1/4 Size - Bottom Left"))
        Layout_Bottom_Left.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.BOTTOM_LEFT, clip_ids))
        Layout_Bottom_Right = Layout_Menu.addAction(_("1/4 Size - Bottom Right"))
        Layout_Bottom_Right.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.BOTTOM_RIGHT, clip_ids))
        Layout_Menu.addSeparator()
        Layout_Bottom_All_With_Aspect = Layout_Menu.addAction(_("Show All (Maintain Ratio)"))
        Layout_Bottom_All_With_Aspect.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.ALL_WITH_ASPECT, clip_ids))
        Layout_Bottom_All_Without_Aspect = Layout_Menu.addAction(_("Show All (Distort)"))
        Layout_Bottom_All_Without_Aspect.triggered.connect(partial(
            self.Layout_Triggered, MenuLayout.ALL_WITHOUT_ASPECT, clip_ids))
        Transform_Menu.addMenu(Layout_Menu)

        if clip_has_visual:
            menu.addMenu(Transform_Menu)

        if clip_has_visual:
            
            Look_Menu = StyledContextMenu(title=_("Look"), parent=self)
            Reset_Look = Look_Menu.addAction(_("Reset Look"))
            Reset_Look.triggered.connect(partial(self.Reset_Look_Triggered, clip_ids))
            Look_Menu.addSeparator()


            Film_Menu = StyledContextMenu(title=_("Film"), parent=self)
            Film_Grain_Menu = StyledContextMenu(title=_("Film Grain"), parent=self)
            Film_Grain_None = Film_Grain_Menu.addAction(_("No Film Grain"))
            Film_Grain_None.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_NONE, clip_ids))
            Film_Grain_Menu.addSeparator()
            Film_Grain_35mm_Fine = Film_Grain_Menu.addAction(_("35mm Fine"))
            Film_Grain_35mm_Fine.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_35MM_FINE, clip_ids))
            Film_Grain_35mm_Classic = Film_Grain_Menu.addAction(_("35mm Classic"))
            Film_Grain_35mm_Classic.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_35MM_CLASSIC, clip_ids))
            Film_Grain_35mm_Gritty = Film_Grain_Menu.addAction(_("35mm Gritty"))
            Film_Grain_35mm_Gritty.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_35MM_GRITTY, clip_ids))
            Film_Grain_16mm_Classic = Film_Grain_Menu.addAction(_("16mm Classic"))
            Film_Grain_16mm_Classic.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_16MM_CLASSIC, clip_ids))
            Film_Grain_Super_8 = Film_Grain_Menu.addAction(_("Super 8"))
            Film_Grain_Super_8.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_SUPER_8, clip_ids))
            Film_Grain_High_ISO = Film_Grain_Menu.addAction(_("High ISO"))
            Film_Grain_High_ISO.triggered.connect(partial(
                self.Film_Grain_Triggered, FILM_GRAIN_PRESET_HIGH_ISO, clip_ids))
            Film_Menu.addMenu(Film_Grain_Menu)

            self._add_effect_preset_menu(
                Film_Menu,
                _("Analog Tape"),
                "AnalogTape",
                _("No Analog Tape"),
                [
                    (_("Subtle"), "subtle"),
                    (_("VHS"), "vhs"),
                    (_("Heavy"), "heavy"),
                ],
                clip_ids,
            )

            Look_Menu.addMenu(Film_Menu)

            Focus_Menu = StyledContextMenu(title=_("Focus"), parent=self)
            self._add_effect_preset_menu(
                Focus_Menu,
                _("Sharpen"),
                "Sharpen",
                _("No Sharpen"),
                [
                    (_("Subtle"), "subtle"),
                    (_("Medium"), "medium"),
                    (_("Strong"), "strong"),
                ],
                clip_ids,
            )
            self._add_effect_preset_menu(
                Focus_Menu,
                _("Blur"),
                "Blur",
                _("No Blur"),
                [
                    (_("Soft Focus"), "soft_focus"),
                    (_("Medium"), "medium"),
                    (_("Heavy"), "heavy"),
                ],
                clip_ids,
            )

            if Focus_Menu.actions():
                Look_Menu.addMenu(Focus_Menu)

            Lighting_Menu = StyledContextMenu(title=_("Lighting"), parent=self)
            self._add_effect_preset_menu(
                Lighting_Menu,
                _("Shadow"),
                "Shadow",
                _("No Shadow"),
                [
                    (_("Subtle"), "subtle"),
                    (_("Soft"), "soft"),
                    (_("Strong"), "strong"),
                    (_("Long"), "long"),
                ],
                clip_ids,
            )
            self._add_effect_preset_menu(
                Lighting_Menu,
                _("Glow"),
                "Glow",
                _("No Glow"),
                [
                    (_("Soft White"), "soft_white"),
                    (_("Warm"), "warm"),
                    (_("Neon"), "neon"),
                    (_("Inner Glow"), "inner"),
                ],
                clip_ids,
            )

            if Lighting_Menu.actions():
                Look_Menu.addMenu(Lighting_Menu)

            Look_Menu.addSeparator()
            Analyze_Colors = Look_Menu.addAction(
                QIcon(os.path.join(info.PATH, "themes/cosmic/images/view-analysis.svg")),
                _("Analyze Colors"))
            Analyze_Colors.triggered.connect(lambda: get_app().window.show_scope_video_docks())

            menu.addMenu(Look_Menu)

        
        Time_Menu = StyledContextMenu(title=_("Speed"), parent=self)
        Time_None = Time_Menu.addAction(_("Reset Speed"))
        Time_None.triggered.connect(partial(self.Time_Triggered, MenuTime.NONE, clip_ids, '1X'))
        Time_Menu.addSeparator()

        Reverse_Action = Time_Menu.addAction(_("Reverse"))
        Reverse_Action.triggered.connect(
            partial(self.Time_Triggered, MenuTime.REVERSE, clip_ids, '1X')
        )

        Time_Menu.addSeparator()
        for speed, speed_values in [
            (_("Speed Up"), ['2X', '4X', '8X', '16X']),
            (_("Slow Down"), ['1/2X', '1/4X', '1/8X', '1/16X'])
        ]:
            Speed_Menu = StyledContextMenu(title=speed, parent=self)

            for direction, direction_value in [
                (_("Forward"), MenuTime.FORWARD),
                (_("Backward"), MenuTime.BACKWARD)
            ]:
                Direction_Menu = StyledContextMenu(title=direction, parent=self)

                for actual_speed in speed_values:
                    
                    Time_Option = Direction_Menu.addAction(_(actual_speed))
                    Time_Option.triggered.connect(
                        partial(self.Time_Triggered, direction_value, clip_ids, actual_speed))

                
                Speed_Menu.addMenu(Direction_Menu)
            
            Time_Menu.addMenu(Speed_Menu)

        
        Repeat_Menu = StyledContextMenu(title=_("Repeat"), parent=self)
        for pattern_title, pattern in [(_("Loop"), "loop"), (_("Ping-Pong"), "pingpong")]:
            Pattern_Menu = StyledContextMenu(title=pattern_title, parent=self)
            for direction_title, start_dir in [(_("Forward"), 1), (_("Reverse"), -1)]:
                Dir_Menu = StyledContextMenu(title=direction_title, parent=self)
                for count in [2, 3, 4, 5, 8, 10]:
                    Action = Dir_Menu.addAction(_("{}X").format(count))
                    Action.triggered.connect(
                        partial(self.Repeat_Triggered, pattern, start_dir, count, clip_ids))
                Pattern_Menu.addMenu(Dir_Menu)
            Repeat_Menu.addMenu(Pattern_Menu)
        Custom_Action = Repeat_Menu.addAction(_("Custom"))
        Custom_Action.triggered.connect(partial(self.Repeat_Custom, clip_ids))
        Time_Menu.addMenu(Repeat_Menu)

        
        Time_Menu.addSeparator()
        for freeze_type, trigger_type in [
            (_("Freeze"), MenuTime.FREEZE),
            (_("Freeze && Zoom"), MenuTime.FREEZE_ZOOM)
        ]:
            Freeze_Menu = StyledContextMenu(title=freeze_type, parent=self)

            for freeze_seconds in [2, 4, 6, 8, 10, 20, 30]:
                
                Time_Option = Freeze_Menu.addAction(_('{} seconds').format(freeze_seconds))
                Time_Option.triggered.connect(
                    partial(self.Time_Triggered, trigger_type, clip_ids, freeze_seconds, playhead_position))

            
            Time_Menu.addMenu(Freeze_Menu)

        
        menu.addMenu(Time_Menu)

        
        Audio_Menu = StyledContextMenu(title=_("Audio"), parent=self)
        audio_menu_has_actions = False
        Record_Voiceover = Audio_Menu.addAction(
            self._microphone_icon(),
            _("Record"))
        Record_Voiceover.triggered.connect(lambda: self._record_from_clip(clip))
        audio_menu_has_actions = True
        Audio_Menu.addSeparator()

        Volume_Menu = StyledContextMenu(title=_("Volume"), parent=self)
        Volume_None = Volume_Menu.addAction(_("Reset Volume"))
        Volume_None.triggered.connect(partial(self.Volume_Triggered, MenuVolume.NONE, clip_ids))
        Volume_Menu.addSeparator()

        Vol_Level_Menu = StyledContextMenu(title=_("Level"), parent=self)
        for level in reversed(range(0, 140, 10)):
            vol_action = Vol_Level_Menu.addAction(_("Level {level}%").format(level=level))
            vol_action.triggered.connect(partial(self.Volume_Triggered, MenuVolume.LEVEL, clip_ids, "Entire Clip", level))
        Volume_Menu.addMenu(Vol_Level_Menu)

        Volume_Menu.addSeparator()

        Vol_Fade_In_Menu = StyledContextMenu(title=_("Fade In"), parent=self)
        Vol_Fade_In_Fast = Vol_Fade_In_Menu.addAction(_("Fast"))
        Vol_Fade_In_Fast.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_IN_FAST, clip_ids, "Start of Clip"))
        Vol_Fade_In_Slow = Vol_Fade_In_Menu.addAction(_("Slow"))
        Vol_Fade_In_Slow.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_IN_SLOW, clip_ids, "Start of Clip"))
        Volume_Menu.addMenu(Vol_Fade_In_Menu)

        Vol_Fade_Out_Menu = StyledContextMenu(title=_("Fade Out"), parent=self)
        Vol_Fade_Out_Fast = Vol_Fade_Out_Menu.addAction(_("Fast"))
        Vol_Fade_Out_Fast.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_OUT_FAST, clip_ids, "End of Clip"))
        Vol_Fade_Out_Slow = Vol_Fade_Out_Menu.addAction(_("Slow"))
        Vol_Fade_Out_Slow.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_OUT_SLOW, clip_ids, "End of Clip"))
        Volume_Menu.addMenu(Vol_Fade_Out_Menu)

        Vol_Fade_In_Out_Menu = StyledContextMenu(title=_("Fade In and Out"), parent=self)
        Vol_Fade_In_Out_Fast = Vol_Fade_In_Out_Menu.addAction(_("Fast"))
        Vol_Fade_In_Out_Fast.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_IN_OUT_FAST, clip_ids, "Entire Clip"))
        Vol_Fade_In_Out_Slow = Vol_Fade_In_Out_Menu.addAction(_("Slow"))
        Vol_Fade_In_Out_Slow.triggered.connect(partial(self.Volume_Triggered, MenuVolume.FADE_IN_OUT_SLOW, clip_ids, "Entire Clip"))
        Volume_Menu.addMenu(Vol_Fade_In_Out_Menu)

        if clip_has_audio:
            Audio_Menu.addMenu(Volume_Menu)
            audio_menu_has_actions = True

        Split_Audio_Channels_Menu = StyledContextMenu(title=_("Separate"), parent=self)
        Split_Single_Clip = Split_Audio_Channels_Menu.addAction(_("Single Clip (all channels)"))
        Split_Single_Clip.triggered.connect(partial(
            self.Split_Audio_Triggered, MenuSplitAudio.SINGLE, clip_ids))
        Split_Multiple_Clips = Split_Audio_Channels_Menu.addAction(_("Multiple Clips (each channel)"))
        Split_Multiple_Clips.triggered.connect(partial(
            self.Split_Audio_Triggered, MenuSplitAudio.MULTIPLE, clip_ids))
        if clip_has_audio:
            Audio_Menu.addMenu(Split_Audio_Channels_Menu)
            audio_menu_has_actions = True

        if clip_has_audio:
            Audio_Menu.addSeparator()
        if self._clip_has_audio(clip):
            if self._clip_has_visible_waveform(clip):
                ToggleWaveform = Audio_Menu.addAction(
                    QIcon(os.path.join(info.PATH, "themes/cosmic/images/view-waveform-flat.svg")),
                    _("Hide Waveform"))
                ToggleWaveform.triggered.connect(partial(self.Hide_Waveform_Triggered, clip_ids))
            else:
                ToggleWaveform = Audio_Menu.addAction(
                    QIcon(os.path.join(info.PATH, "themes/cosmic/images/view-waveform.svg")),
                    _("Show Waveform"))
                ToggleWaveform.triggered.connect(partial(self.Show_Waveform_Triggered, clip_ids))
        if clip_has_audio:
            Analyze_Levels = Audio_Menu.addAction(
                QIcon(os.path.join(info.PATH, "themes/cosmic/images/view-analysis.svg")),
                _("Analyze Levels"))
            Analyze_Levels.triggered.connect(lambda: get_app().window.show_scope_audio_dock())
            audio_menu_has_actions = True

        if audio_menu_has_actions:
            menu.addMenu(Audio_Menu)

        
        if clip:
            start_of_clip = float(clip.data["start"])
            end_of_clip = float(clip.data["end"])
            position_of_clip = float(clip.data["position"])
            if (
                playhead_position >= position_of_clip
                and playhead_position <= (position_of_clip + (end_of_clip - start_of_clip))
            ):
                
                Slice_Menu = StyledContextMenu(title=_("Slice"), parent=self)
                Slice_Keep_Both = Slice_Menu.addAction(_("Keep Both Sides"))
                Slice_Keep_Both.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_BOTH, clip_ids, tran_ids, playhead_position))
                Slice_Keep_Left = Slice_Menu.addAction(_("Keep Left Side"))
                Slice_Keep_Left.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_LEFT, clip_ids, tran_ids, playhead_position))
                Slice_Keep_Right = Slice_Menu.addAction(_("Keep Right Side"))
                Slice_Keep_Right.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_RIGHT, clip_ids, tran_ids, playhead_position))

                
                Slice_Menu.addSeparator()
                Slice_Keep_Left = Slice_Menu.addAction(_("Keep Left Side (Ripple)"))
                Slice_Keep_Left.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_LEFT, clip_ids, tran_ids, playhead_position, True))
                Slice_Keep_Right = Slice_Menu.addAction(_("Keep Right Side (Ripple)"))
                Slice_Keep_Right.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_RIGHT, clip_ids, tran_ids, playhead_position, True))

                menu.addMenu(Slice_Menu)

        
        menu.addSeparator()
        menu.addAction(self.window.actionProperties)

        
        menu.addSeparator()
        menu.addAction(self.window.actionRemoveClip)

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    def Show_Waveform_Triggered(self, clip_ids, transaction_id=None):
        """Show a waveform for all selected clips"""

        log.info("Show waveform requested for clips: %s", clip_ids)

        
        
        files = {}
        for clip_id in clip_ids:
            
            clip = Clip.get(id=clip_id)
            if not clip:
                log.warning("Skipping waveform request for missing clip: %s", clip_id)
                continue
            file_id = clip.data.get("file_id")

            if file_id not in files:
                files[file_id] = []
            files[file_id].append(clip.data.get("id"))

        
        get_audio_data(files, transaction_id=transaction_id)

    def Hide_Waveform_Triggered(self, clip_ids):
        """Hide the waveform for the selected clip"""

        
        for clip_id in clip_ids:
            
            clip = Clip.get(id=clip_id)
            clip.data = {"ui": {"audio_data": []}}
            clip.save()

    def fileAudioDataReady_Triggered(self, file_id, ui_data, tid):
        log.debug("fileAudioDataReady_Triggered received for file: %s" % file_id)

        
        get_app().updates.transaction_id = tid

        get_app().window.actionClearWaveformData.setEnabled(True)
        file = File.get(id=file_id)
        if file:
            file.data = ui_data
            file.save()

        
        get_app().updates.transaction_id = None

    def clipAudioDataReady_Triggered(self, clip_id, ui_data, tid):
        
        audio_samples = ui_data.get("ui", {}).get("audio_data") if isinstance(ui_data, dict) else []
        sample_count = len(audio_samples) if isinstance(audio_samples, list) else 0
        log.info(
            "Waveform data ready for clip %s (samples: %s)", clip_id, sample_count
        )

        
        get_app().updates.transaction_id = tid

        get_app().window.actionClearWaveformData.setEnabled(True)
        clip = Clip.get(id=clip_id)
        if clip:
            existing_ui = clip.data.get("ui", {}) if isinstance(clip.data, dict) else {}
            incoming_ui = ui_data.get("ui") if isinstance(ui_data, dict) else None
            incoming_audio = incoming_ui.get("audio_data") if isinstance(incoming_ui, dict) else None
            preserve_existing_waveform = (
                incoming_audio is None and isinstance(existing_ui.get("audio_data"), list)
            )

            
            
            if preserve_existing_waveform:
                merged_ui = dict(existing_ui)
                if isinstance(incoming_ui, dict):
                    merged_ui.update(incoming_ui)
                merged_ui["audio_data"] = existing_ui.get("audio_data")
                ui_data = dict(ui_data or {})
                ui_data["ui"] = merged_ui

            if isinstance(ui_data, dict):
                clip_ui = ui_data.get("ui")
                if not isinstance(clip_ui, dict):
                    clip_ui = {}
                    ui_data["ui"] = clip_ui
                if not preserve_existing_waveform and isinstance(clip_ui.get("audio_data"), list):
                    clip_ui["waveform_token"] = str(tid or self.get_uuid())
            clip.data = ui_data
            clip.save()
            if hasattr(self, "clip_painter"):
                self.clip_painter.clear_cache()
            QTimer.singleShot(0, self.update)

        
        get_app().updates.transaction_id = None

    def Thumbnail_Updated(self, clip_id, thumbnail_frame=1):
        """Callback when thumbnail needs to be updated"""
        clips = Clip.filter(id=clip_id)
        for clip in clips:
            
            GetThumbPath(clip.data.get("file_id"), thumbnail_frame, clear_cache=True)

            if ViewClass == TimelineWidget:
                if hasattr(self, "clip_painter"):
                    self.clip_painter.invalidate_clip_thumbnails(clip.id)
                self.update()
                continue

            
            self.run_js(JS_SCOPE_SELECTOR + ".updateThumbnail('" + clip_id + "');")

    def Split_Audio_Triggered(self, action, clip_ids):
        """Callback for split audio context menus"""
        log.debug("Split_Audio_Triggered")

        
        _ = get_app()._tr

        
        tid = self.get_uuid()
        get_app().updates.transaction_id = tid

        
        for clip_id in clip_ids:

            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            
            all_tracks = get_app().project.get("layers")

            reader = clip.data.get("reader", {})
            has_audio = reader.get("has_audio")
            has_audio = True if has_audio is None else bool(has_audio)
            channels_value = reader.get("channels")
            try:
                channel_count = int(channels_value) if channels_value is not None else None
            except (TypeError, ValueError):
                channel_count = None
            has_video = reader.get("has_video")
            has_video = True if has_video is None else bool(has_video)
            original_layer = clip.data.get("layer")

            if (not has_audio) or (channel_count is not None and channel_count <= 0):
                log.info("Split audio skipped for clip %s (no audio)", clip_id)
                continue

            def get_track_below(layer_number):
                """Return the track number directly below the provided layer, creating one when needed."""
                window = getattr(get_app(), "window", None)
                create_below = getattr(window, "create_track_below", None)
                if callable(create_below):
                    return create_below(layer_number)

                next_track_number = layer_number
                found_track = False
                for track in reversed(sorted(all_tracks, key=itemgetter('number'))):
                    if found_track:
                        next_track_number = track.get("number")
                        break
                    if track.get("number") == layer_number:
                        found_track = True
                        continue
                return next_track_number

            
            clip_title = clip.data["title"]

            
            if not has_video:
                if action == MenuSplitAudio.SINGLE:
                    
                    p = smartedit.Point(1, -1.0, smartedit.CONSTANT)
                    p_object = json.loads(p.Json())
                    clip.data["channel_filter"] = {"Points": [p_object]}
                    clip.save()

                    
                    log.info("Generate waveform for audio-only clip id: %s" % clip.id)
                    self.Show_Waveform_Triggered([clip.id], transaction_id=tid)
                    continue

                if action == MenuSplitAudio.MULTIPLE:
                    channels = channel_count

                    separate_clip_ids = []
                    current_layer = original_layer
                    for channel in range(0, channels):
                        log.debug("Adding clip for channel %s" % channel)

                        
                        p = smartedit.Point(1, channel, smartedit.CONSTANT)
                        p_object = json.loads(p.Json())
                        clip.data["channel_filter"] = {"Points": [p_object]}

                        
                        p = smartedit.Point(1, 0.0, smartedit.CONSTANT)
                        p_object = json.loads(p.Json())
                        clip.data["has_video"] = {"Points": [p_object]}
                        clip.data["scale"] = smartedit.SCALE_NONE

                        
                        target_layer = current_layer if channel == 0 else get_track_below(current_layer)
                        clip.data['layer'] = target_layer
                        current_layer = clip.data['layer']

                        
                        channel_label = _("(channel %s)") % (channel + 1)
                        clip.data["title"] = clip_title + " " + channel_label

                        
                        clip.save()
                        separate_clip_ids.append(clip.id)

                        
                        if channel < channels - 1:
                            clip.id = None
                            clip.type = 'insert'
                            clip.data.pop('id', None)
                            if clip.key and len(clip.key) > 1:
                                clip.key.pop(1)

                    
                    log.info("Generate waveform for split audio track clip ids: %s" % str(separate_clip_ids))
                    self.Show_Waveform_Triggered(separate_clip_ids, transaction_id=tid)
                    continue

            
            p = smartedit.Point(1, -1.0, smartedit.CONSTANT)  
            p_object = json.loads(p.Json())
            clip.data["has_audio"] = {"Points": [p_object]}

            
            clip.id = None
            clip.type = 'insert'
            clip.data.pop('id')
            clip.key.pop(1)

            if action == MenuSplitAudio.SINGLE:
                
                p = smartedit.Point(1, -1.0, smartedit.CONSTANT)
                p_object = json.loads(p.Json())
                clip.data["channel_filter"] = {"Points": [p_object]}

                
                p = smartedit.Point(1, 0.0, smartedit.CONSTANT)  
                p_object = json.loads(p.Json())
                clip.data["has_video"] = {"Points": [p_object]}
                
                
                clip.data["scale"] = smartedit.SCALE_NONE

                
                target_layer = get_track_below(original_layer)
                clip.data['layer'] = target_layer

                
                channel_label = _("(all channels)")
                clip.data["title"] = clip_title + " " + channel_label
                
                clip.save()

                
                log.info("Generate waveform for split audio track clip id: %s" % clip.id)
                self.Show_Waveform_Triggered([clip.id], transaction_id=tid)

            if action == MenuSplitAudio.MULTIPLE:
                
                channels = channel_count

                
                separate_clip_ids = []
                current_layer = original_layer
                for channel in range(0, channels):
                    log.debug("Adding clip for channel %s" % channel)

                    
                    p = smartedit.Point(1, channel, smartedit.CONSTANT)
                    p_object = json.loads(p.Json())
                    clip.data["channel_filter"] = {"Points": [p_object]}

                    
                    p = smartedit.Point(1, 0.0, smartedit.CONSTANT)  
                    p_object = json.loads(p.Json())
                    clip.data["has_video"] = {"Points": [p_object]}
                    
                    
                    clip.data["scale"] = smartedit.SCALE_NONE

                    
                    target_layer = get_track_below(current_layer)
                    clip.data['layer'] = target_layer
                    current_layer = clip.data['layer']

                    
                    channel_label = _("(channel %s)") % (channel + 1)
                    clip.data["title"] = clip_title + " " + channel_label

                    
                    clip.save()
                    separate_clip_ids.append(clip.id)

                    
                    clip.id = None
                    clip.type = 'insert'
                    clip.data.pop('id')

                
                log.info("Generate waveform for split audio track clip ids: %s" % str(separate_clip_ids))
                self.Show_Waveform_Triggered(separate_clip_ids, transaction_id=tid)

        for clip_id in clip_ids:

            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            reader = clip.data.get("reader", {})
            has_video = reader.get("has_video")
            has_video = True if has_video is None else bool(has_video)

            if not has_video:
                continue

            
            p = smartedit.Point(1, 0.0, smartedit.CONSTANT)  
            p_object = json.loads(p.Json())
            clip.data["has_audio"] = {"Points": [p_object]}

            
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
            clip.save()

        
        get_app().updates.transaction_id = None

    def Crop_Triggered(self, clip_ids, mode):
        """Add/remove/select the Crop effect based on mode"""
        get_app().window.clearSelections()
        first_effect_id = None
        first_clip_id = None
        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip:
                continue
            effects = clip.data.setdefault('effects', [])
            existing = next((e for e in effects if e.get('class_name') == 'Crop'), None)
            if mode == 'none':
                if existing:
                    effects.remove(existing)
                    self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
                continue

            if not existing:
                effect = smartedit.EffectInfo().CreateEffect('Crop')
                effect_json = json.loads(effect.Json())
                effects.append(effect_json)
                existing = effect_json

            
            resize_val = True if mode == 'resize' else False
            existing['resize'] = resize_val
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)

            if not first_effect_id and existing.get('id'):
                first_effect_id = existing['id']
                first_clip_id = clip_id

        if first_effect_id:
            self.addSelection(first_effect_id, 'effect', True)
            self.window.KeyFrameTransformSignal.emit(first_effect_id, first_clip_id)
        elif mode == 'none' and clip_ids:
            self.addSelection(clip_ids[0], 'clip', True)
            self.window.KeyFrameTransformSignal.emit('', '')

    def _clip_has_video(self, clip):
        if not clip:
            return False
        reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
        has_video = reader.get("has_video")
        return True if has_video is None else bool(has_video)

    def _clip_has_audio(self, clip):
        if not clip:
            return False
        reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
        has_audio = reader.get("has_audio")
        return True if has_audio is None else bool(has_audio)

    def _clip_has_visual(self, clip):
        """Return True if the clip has video OR has waveform rendering enabled."""
        if not clip:
            return False
        reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
        has_video = reader.get("has_video")
        if has_video is None or bool(has_video):
            return True
        return bool(clip.data.get("waveform", False))

    def _create_film_grain_effect_json(self):
        effect = smartedit.EffectInfo().CreateEffect(FILM_GRAIN_CLASS_NAME)
        if effect is None:
            raise RuntimeError("Unable to create Film Grain effect")
        effect.Id(get_app().project.generate_id())
        return json.loads(effect.Json())

    def _can_create_effect(self, class_name):
        return smartedit.EffectInfo().CreateEffect(class_name) is not None

    def _add_effect_preset_menu(self, parent_menu, title, class_name, reset_label, preset_items, clip_ids):
        if not self._can_create_effect(class_name):
            return None

        preset_menu = StyledContextMenu(title=title, parent=self)
        reset_action = preset_menu.addAction(reset_label)
        reset_action.triggered.connect(partial(
            self._apply_effect_preset, class_name, "none", clip_ids))
        preset_menu.addSeparator()

        for label, preset_name in preset_items:
            preset_action = preset_menu.addAction(label)
            preset_action.triggered.connect(partial(
                self._apply_effect_preset, class_name, preset_name, clip_ids))

        parent_menu.addMenu(preset_menu)
        return preset_menu

    def _create_effect_json(self, class_name):
        effect = smartedit.EffectInfo().CreateEffect(class_name)
        if effect is None:
            raise RuntimeError("Unable to create {} effect".format(class_name))
        effect.Id(get_app().project.generate_id())
        return json.loads(effect.Json())

    def _is_look_managed_effect(self, effect_json, class_name=None):
        if not isinstance(effect_json, dict):
            return False
        if effect_json.get("ui-menu") != LOOK_EFFECT_UI_MENU:
            return False
        return class_name is None or effect_json.get("class_name") == class_name

    def _parse_effect_color(self, value):
        if not isinstance(value, str):
            return None
        color = value.strip()
        if color.startswith("#"):
            color = color[1:]
        if len(color) not in (6, 8):
            return None
        try:
            red = int(color[0:2], 16)
            green = int(color[2:4], 16)
            blue = int(color[4:6], 16)
            alpha = int(color[6:8], 16) if len(color) == 8 else 255
        except ValueError:
            return None
        return {
            "red": red,
            "green": green,
            "blue": blue,
            "alpha": alpha,
        }

    def _set_effect_property_value(self, effect_json, property_name, value):
        property_data = effect_json.get(property_name)
        color_channels = self._parse_effect_color(value)
        if color_channels and isinstance(property_data, dict):
            for channel, channel_value in color_channels.items():
                channel_data = property_data.get(channel)
                if isinstance(channel_data, dict) and isinstance(channel_data.get("Points"), list):
                    channel_data["Points"] = [
                        json.loads(smartedit.Point(1, float(channel_value), smartedit.BEZIER).Json())
                    ]
        elif isinstance(property_data, dict) and isinstance(property_data.get("Points"), list):
            property_data["Points"] = [json.loads(smartedit.Point(1, float(value), smartedit.BEZIER).Json())]
        elif property_name in effect_json:
            effect_json[property_name] = value

    def _apply_effect_preset(self, class_name, preset_name, clip_ids):
        """Apply a simple Look effect preset, or remove the effect for the none preset."""
        presets = LOOK_EFFECT_PRESETS.get(class_name, {})
        if preset_name not in presets:
            return

        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip or not self._clip_has_visual(clip):
                continue

            original_clip_data = json.loads(json.dumps(clip.data))
            effects = clip.data.get("effects")
            if not isinstance(effects, list):
                effects = list(effects) if effects else []
                clip.data["effects"] = effects

            matching_indexes = [
                index for index, effect_json in enumerate(effects)
                if self._is_look_managed_effect(effect_json, class_name)
            ]

            if preset_name == "none":
                if not matching_indexes:
                    continue
                clip.data["effects"] = [
                    effect_json for effect_json in effects
                    if not self._is_look_managed_effect(effect_json, class_name)
                ]
                self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
                get_app().updates.apply_last_action_to_history(original_clip_data)
                continue

            try:
                preset_effect = self._create_effect_json(class_name)
            except RuntimeError:
                continue
            preset_effect["ui-menu"] = LOOK_EFFECT_UI_MENU

            if matching_indexes:
                existing_effect = effects[matching_indexes[0]]
                if existing_effect.get("id"):
                    preset_effect["id"] = existing_effect["id"]
                if "order" in existing_effect:
                    preset_effect["order"] = existing_effect["order"]

            for property_name, value in presets[preset_name].items():
                self._set_effect_property_value(preset_effect, property_name, value)

            if matching_indexes:
                effects[matching_indexes[0]] = preset_effect
                for index in reversed(matching_indexes[1:]):
                    del effects[index]
            else:
                effects.append(preset_effect)

            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
            get_app().updates.apply_last_action_to_history(original_clip_data)

    def Reset_Look_Triggered(self, clip_ids):
        """Remove all effects managed by the clip Look menu."""
        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip or not self._clip_has_visual(clip):
                continue

            effects = clip.data.get("effects")
            if not isinstance(effects, list):
                continue

            filtered_effects = [
                effect_json for effect_json in effects
                if not isinstance(effect_json, dict)
                or (
                    effect_json.get("class_name") not in LOOK_RESET_EFFECT_CLASSES
                    and not self._is_look_managed_effect(effect_json)
                )
            ]
            if len(filtered_effects) == len(effects):
                continue

            original_clip_data = json.loads(json.dumps(clip.data))
            clip.data["effects"] = filtered_effects
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
            get_app().updates.apply_last_action_to_history(original_clip_data)

    def Film_Grain_Triggered(self, preset_name, clip_ids):
        """Apply Film Grain presets for selected clips."""
        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip or not self._clip_has_visual(clip):
                continue

            original_clip_data = json.loads(json.dumps(clip.data))
            effects = clip.data.get("effects")
            if not isinstance(effects, list):
                effects = list(effects) if effects else []
                clip.data["effects"] = effects

            matching_indexes = [
                index for index, effect_json in enumerate(effects)
                if is_film_grain_effect(effect_json)
            ]

            if preset_name == FILM_GRAIN_PRESET_NONE:
                if not matching_indexes:
                    continue
                clip.data["effects"] = [
                    effect_json for effect_json in effects
                    if not is_film_grain_effect(effect_json)
                ]
                self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
                get_app().updates.apply_last_action_to_history(original_clip_data)
                continue

            source_effect = (
                effects[matching_indexes[0]]
                if matching_indexes
                else self._create_film_grain_effect_json()
            )
            preset_effect = apply_film_grain_preset(source_effect, preset_name)

            if matching_indexes:
                existing_effect = effects[matching_indexes[0]]
                if existing_effect.get("id"):
                    preset_effect["id"] = existing_effect["id"]
                if "order" in existing_effect:
                    preset_effect["order"] = existing_effect["order"]
                for index in reversed(matching_indexes[1:]):
                    del effects[index]
                effects[matching_indexes[0]] = preset_effect
            else:
                effects.append(preset_effect)

            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
            get_app().updates.apply_last_action_to_history(original_clip_data)

    def Layout_Triggered(self, action, clip_ids):
        """Callback for the layout context menus"""
        log.debug(action)

        if action in (MenuLayout.ALL_WITH_ASPECT, MenuLayout.ALL_WITHOUT_ASPECT):
            for clip_id in clip_ids:
                clip = Clip.get(id=clip_id)
                if clip:
                    self.show_all_clips(
                        clip,
                        action == MenuLayout.ALL_WITHOUT_ASPECT,
                        clip_ids=clip_ids,
                    )
                    break
            return

        
        for clip_id in clip_ids:

            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            new_gravity = smartedit.GRAVITY_CENTER
            if action == MenuLayout.CENTER:
                new_gravity = smartedit.GRAVITY_CENTER
            if action == MenuLayout.TOP_LEFT:
                new_gravity = smartedit.GRAVITY_TOP_LEFT
            elif action == MenuLayout.TOP_RIGHT:
                new_gravity = smartedit.GRAVITY_TOP_RIGHT
            elif action == MenuLayout.BOTTOM_LEFT:
                new_gravity = smartedit.GRAVITY_BOTTOM_LEFT
            elif action == MenuLayout.BOTTOM_RIGHT:
                new_gravity = smartedit.GRAVITY_BOTTOM_RIGHT

            if action == MenuLayout.NONE:
                
                clip.data["scale"] = smartedit.SCALE_FIT
                clip.data["gravity"] = smartedit.GRAVITY_CENTER

                
                p = smartedit.Point(1, 1.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data["scale_x"] = {"Points": [p_object]}
                clip.data["scale_y"] = {"Points": [p_object]}

                
                p = smartedit.Point(1, 0.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data["location_x"] = {"Points": [p_object]}
                clip.data["location_y"] = {"Points": [p_object]}

            if action in [MenuLayout.CENTER,
                          MenuLayout.TOP_LEFT,
                          MenuLayout.TOP_RIGHT,
                          MenuLayout.BOTTOM_LEFT,
                          MenuLayout.BOTTOM_RIGHT]:
                
                clip.data["scale"] = smartedit.SCALE_FIT
                clip.data["gravity"] = new_gravity

                
                p = smartedit.Point(1, 0.5, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data["scale_x"] = {"Points": [p_object]}
                clip.data["scale_y"] = {"Points": [p_object]}

                
                p = smartedit.Point(1, 0.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data["location_x"] = {"Points": [p_object]}
                clip.data["location_y"] = {"Points": [p_object]}

            
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)

    def Animate_Triggered(self, action, clip_ids, transaction_id=None):
        """Apply one-click motion presets to selected clips.

        Each MenuAnimate action encodes the animation type and its zone:
          In actions  → first 1 second of the clip
          Out actions → last 1 second of the clip
          Continuous  → entire clip duration
          Pan actions → entire clip, also sets scale mode to SCALE_CROP

        Keyframe coordinates follow SmartEdit conventions:
          location ±1.0 ≈ one full frame dimension (offscreen)
          scale    1.0  = 100%
          rotation degrees (positive = clockwise)
          shear    dimensionless skew factor
          origin   0.0–1.0 (0 = top/left edge, 0.5 = center, 1.0 = bottom/right)
        """
        log.debug(action)
        tid = transaction_id or self.get_uuid()
        try:
            get_app().updates.transaction_id = tid

            for clip_id in clip_ids:
                clip = Clip.get(id=clip_id)
                if not clip:
                    continue

                fps = get_app().project.get("fps")
                fps_float = float(fps["num"]) / float(fps["den"])

                
                s = round(float(clip.data["start"]) * fps_float) + 1   
                e = round(float(clip.data["end"])   * fps_float) + 1   
                dur = max(1, e - s)                                     

                
                zone = max(1, round(fps_float))
                in_end    = min(s + zone, e)   
                out_start = max(s, e - zone)   

                
                
                
                try:
                    timeline_frame = int(self.window.preview_thread.current_frame or 1)
                except Exception:
                    timeline_frame = 1
                try:
                    timeline_seconds = max(0.0, (timeline_frame - 1) / fps_float)
                    clip_position = float(clip.data.get("position", 0.0))
                    clip_playhead = round(
                        (float(clip.data["start"]) + timeline_seconds - clip_position) * fps_float
                    ) + 1
                except Exception:
                    clip_playhead = s
                if s <= clip_playhead <= e:
                    emph_start = clip_playhead
                else:
                    emph_start = s
                emph_end = min(emph_start + zone, e)

                
                def kf(frame, val, interp=smartedit.BEZIER):
                    """Build a keyframe point dict."""
                    return json.loads(smartedit.Point(int(frame), val, interp).Json())

                def add(key, *pts):
                    """Append keyframe points to a clip channel."""
                    for p in pts:
                        self.AddPoint(clip.data[key], p)

                
                c = self.window.timeline_sync.timeline.GetClip(clip_id)

                _PROP_IDENTITY = {
                    'scale_x': 1.0, 'scale_y': 1.0,
                    'location_x': 0.0, 'location_y': 0.0,
                    'alpha': 1.0, 'rotation': 0.0,
                    'shear_x': 0.0, 'shear_y': 0.0,
                }

                def _base(prop, frame):
                    """Return the clip's current value of prop at frame (identity fallback)."""
                    if c is not None:
                        obj = getattr(c, prop, None)
                        if obj is not None:
                            return obj.GetValue(int(round(frame)))
                    return _PROP_IDENTITY.get(prop, 0.0)

                def _rel(prop, preset_val, base_val):
                    """Adjust a preset value relative to the clip's current base value.
                    Scale/alpha are multiplicative; location/rotation/shear are additive."""
                    if prop in ('scale_x', 'scale_y', 'alpha'):
                        return preset_val * base_val
                    return preset_val + base_val

                clip.data["gravity"] = smartedit.GRAVITY_CENTER

                
                
                
                def _reset_motion():
                    clip.data["scale"]      = smartedit.SCALE_FIT
                    clip.data["scale_x"]    = {"Points": [kf(s, 1.0)]}
                    clip.data["scale_y"]    = {"Points": [kf(s, 1.0)]}
                    clip.data["location_x"] = {"Points": [kf(s, 0.0)]}
                    clip.data["location_y"] = {"Points": [kf(s, 0.0)]}
                    clip.data["rotation"]   = {"Points": [kf(s, 0.0)]}
                    clip.data["shear_x"]    = {"Points": [kf(s, 0.0)]}
                    clip.data["shear_y"]    = {"Points": [kf(s, 0.0)]}
                    clip.data["alpha"]      = {"Points": [kf(s, 1.0)]}
                    clip.data["origin_x"]   = {"Points": [kf(s, 0.5)]}
                    clip.data["origin_y"]   = {"Points": [kf(s, 0.5)]}
                    effects = clip.data.get("effects", [])
                    clip.data["effects"] = [
                        eff for eff in (effects if isinstance(effects, list) else [])
                        if not isinstance(eff, dict)
                        or (
                            eff.get("class_name") not in ("Blur", "Mask")
                            or eff.get("ui-menu") == LOOK_EFFECT_UI_MENU
                        )
                    ]

                _WIPE_SVG_FILENAMES = {
                    "circle_in_to_out.svg",
                    "circle_out_to_in.svg",
                    "fade.svg",
                    "wipe_left_to_right.svg",
                    "wipe_right_to_left.svg",
                    "wipe_top_to_bottom.svg",
                    "wipe_bottom_to_top.svg",
                }

                def _find_or_create_motion_effect(class_name):
                    """Return a reusable motion effect and collapse duplicate preset effects."""
                    effects = clip.data.get("effects")
                    if not isinstance(effects, list):
                        effects = []
                        clip.data["effects"] = effects

                    def _points(prop):
                        data = prop if isinstance(prop, dict) else {}
                        return data.get("Points") if isinstance(data.get("Points"), list) else []

                    def _point_values(prop):
                        return [point.get("co", {}).get("Y") for point in _points(prop)]

                    def _is_legacy_motion_effect(eff):
                        if eff.get("ui-menu") not in (None, ""):
                            return False
                        if class_name == "Blur":
                            horizontal = _point_values(eff.get("horizontal_radius"))
                            vertical = _point_values(eff.get("vertical_radius"))
                            return (
                                horizontal == vertical
                                and horizontal in ([50.0, 0.0], [0.0, 50.0])
                            )
                        if class_name == "Mask":
                            reader = eff.get("mask_reader") or eff.get("reader") or {}
                            path = reader.get("path", "") if isinstance(reader, dict) else ""
                            brightness = _point_values(eff.get("brightness"))
                            return (
                                os.path.basename(path) in _WIPE_SVG_FILENAMES
                                and brightness in ([1.0, -1.0], [-1.0, 1.0])
                            )
                        return False

                    matching_indexes = [
                        idx for idx, eff in enumerate(effects)
                        if isinstance(eff, dict)
                        and eff.get("class_name") == class_name
                        and (
                            eff.get("ui-menu") == MOTION_EFFECT_UI_MENU
                            or _is_legacy_motion_effect(eff)
                        )
                    ]
                    if matching_indexes:
                        keep_index = matching_indexes[0]
                        fx = effects[keep_index]
                        fx["ui-menu"] = MOTION_EFFECT_UI_MENU
                        for idx in reversed(matching_indexes[1:]):
                            del effects[idx]
                        return fx, False

                    effect = smartedit.EffectInfo().CreateEffect(class_name)
                    fx = json.loads(effect.Json())
                    fx["id"] = get_app().project.generate_id()
                    fx["ui-menu"] = MOTION_EFFECT_UI_MENU
                    effects.append(fx)
                    return fx, True

                def _set_motion_effect_points(fx, prop, *pts, replace_all=False):
                    if not isinstance(fx.get(prop), dict) or not isinstance(fx[prop].get("Points"), list):
                        fx[prop] = {"Points": []}
                    if replace_all:
                        fx[prop]["Points"] = []
                    else:
                        self._remove_keypoints_in_range(fx[prop], pts[0]["co"]["X"], pts[-1]["co"]["X"])
                    for pt in pts:
                        self.AddPoint(fx[prop], pt)

                def _make_wipe_fx(svg_filename, t_start, t_end, brightness_start, brightness_end,
                                  contrast=20.0):
                    """Reuse or attach a Mask effect (wipe) using the given SVG transition."""
                    svg_path = os.path.join(info.PATH, "transitions", "common", svg_filename)
                    reader_json = self._get_transition_reader_json(svg_path)
                    if not reader_json:
                        return
                    fx, created = _find_or_create_motion_effect("Mask")
                    fx["mask_reader"] = deepcopy(reader_json)
                    fx["reader"]      = deepcopy(reader_json)
                    x1, y1, x2, y2 = _KEYFRAME_EASING['ease_in_out']
                    p0 = kf(t_start, brightness_start)
                    p0['handle_right'] = {'X': x1, 'Y': y1}
                    p1 = kf(t_end, brightness_end)
                    p1['handle_left'] = {'X': x2, 'Y': y2}
                    _set_motion_effect_points(fx, "brightness", p0, p1, replace_all=created)
                    _set_motion_effect_points(fx, "contrast", kf(t_start, contrast), replace_all=created)

                def _make_blur_fx(t_start, r_start, t_end, r_end):
                    """Reuse or attach a Blur effect (horizontal + vertical radius)."""
                    fx, created = _find_or_create_motion_effect("Blur")
                    x1, y1, x2, y2 = _KEYFRAME_EASING['ease_in_out']

                    def _eased_pts():
                        q0 = kf(t_start, r_start)
                        q0['handle_right'] = {'X': x1, 'Y': y1}
                        q1 = kf(t_end, r_end)
                        q1['handle_left'] = {'X': x2, 'Y': y2}
                        return [q0, q1]

                    _set_motion_effect_points(fx, "horizontal_radius", *_eased_pts(), replace_all=created)
                    _set_motion_effect_points(fx, "vertical_radius", *_eased_pts(), replace_all=created)

                def _apply_preset(preset_name, t_start, t_end, resting_frame):
                    """Apply an animation preset scaled to [t_start, t_end] frames.

                    Values are applied relative to the clip's current state at resting_frame:
                    scale/alpha are multiplied by the base value; location/rotation/shear
                    are offset by it.  Easing handles from KEYFRAME_EASING are applied to
                    consecutive point pairs.  The zone [t_start, t_end] is cleared of
                    existing keyframes for each touched property before insertion.
                    """
                    preset = _ANIMATION_PRESETS.get(preset_name, {})
                    if not preset:
                        return
                    src_dur = 30.0  
                    tgt_dur = max(1, t_end - t_start)

                    for prop, points in preset.items():
                        if prop not in clip.data:
                            continue

                        base = _base(prop, resting_frame)

                        
                        self._remove_keypoints_in_range(clip.data[prop], t_start, t_end)

                        
                        
                        
                        self.AddPoint(clip.data[prop], kf(t_start, base))
                        self.AddPoint(clip.data[prop], kf(t_end,   base))

                        
                        scaled = []
                        for pt in points:
                            src_frame = pt[0]
                            src_val   = pt[1]
                            easing    = pt[2] if len(pt) > 2 else None
                            norm      = (src_frame - 1) / src_dur
                            tgt_frame = t_start + round(norm * tgt_dur)
                            adj_val   = _rel(prop, src_val, base)
                            scaled.append((tgt_frame, adj_val, easing))

                        
                        for i, (tgt_frame, adj_val, easing) in enumerate(scaled):
                            p = kf(tgt_frame, adj_val)
                            
                            if easing and easing in _KEYFRAME_EASING:
                                x1, y1, x2, y2 = _KEYFRAME_EASING[easing]
                                p['handle_right'] = {'X': x1, 'Y': y1}
                            
                            if i > 0:
                                prev_easing = scaled[i - 1][2]
                                if prev_easing and prev_easing in _KEYFRAME_EASING:
                                    _, _, x2, y2 = _KEYFRAME_EASING[prev_easing]
                                    p['handle_left'] = {'X': x2, 'Y': y2}
                            self.AddPoint(clip.data[prop], p)

                
                
                _WIPE_SVG = {
                    MenuAnimate.WIPE_IN_CIRCLE_EXPAND:  "circle_in_to_out.svg",
                    MenuAnimate.WIPE_IN_CIRCLE_SHRINK:  "circle_out_to_in.svg",
                    MenuAnimate.WIPE_IN_FADE:           "fade.svg",
                    MenuAnimate.WIPE_IN_LEFT:           "wipe_left_to_right.svg",
                    MenuAnimate.WIPE_IN_RIGHT:          "wipe_right_to_left.svg",
                    MenuAnimate.WIPE_IN_TOP:            "wipe_top_to_bottom.svg",
                    MenuAnimate.WIPE_IN_BOTTOM:         "wipe_bottom_to_top.svg",
                    MenuAnimate.WIPE_OUT_CIRCLE_EXPAND: "circle_out_to_in.svg",
                    MenuAnimate.WIPE_OUT_CIRCLE_SHRINK: "circle_in_to_out.svg",
                    MenuAnimate.WIPE_OUT_FADE:          "fade.svg",
                    MenuAnimate.WIPE_OUT_LEFT:          "wipe_left_to_right.svg",
                    MenuAnimate.WIPE_OUT_RIGHT:         "wipe_right_to_left.svg",
                    MenuAnimate.WIPE_OUT_TOP:           "wipe_top_to_bottom.svg",
                    MenuAnimate.WIPE_OUT_BOTTOM:        "wipe_bottom_to_top.svg",
                    MenuAnimate.FOCUS_WIPE_IN_CIRCLE_EXPAND:  "circle_in_to_out.svg",
                    MenuAnimate.FOCUS_WIPE_IN_CIRCLE_SHRINK:  "circle_out_to_in.svg",
                    MenuAnimate.FOCUS_WIPE_IN_LEFT:           "wipe_left_to_right.svg",
                    MenuAnimate.FOCUS_WIPE_IN_RIGHT:          "wipe_right_to_left.svg",
                    MenuAnimate.FOCUS_WIPE_IN_TOP:            "wipe_top_to_bottom.svg",
                    MenuAnimate.FOCUS_WIPE_IN_BOTTOM:         "wipe_bottom_to_top.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_EXPAND: "circle_out_to_in.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_SHRINK: "circle_in_to_out.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_LEFT:          "wipe_left_to_right.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_RIGHT:         "wipe_right_to_left.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_TOP:           "wipe_top_to_bottom.svg",
                    MenuAnimate.FOCUS_WIPE_OUT_BOTTOM:        "wipe_bottom_to_top.svg",
                }

                def _camera_context():
                    reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
                    source_width, source_height = source_dimensions_from_reader(reader)
                    try:
                        project_width = get_app().project.get("width")
                        project_height = get_app().project.get("height")
                    except Exception:
                        project_width, project_height = None, None
                    return project_width, project_height, source_width, source_height

                def _apply_camera_motion(values):
                    clip.data["scale"] = smartedit.SCALE_CROP
                    for prop in ("scale_x", "scale_y", "location_x", "location_y"):
                        self._remove_keypoints_in_range(clip.data[prop], s, e)
                    add("scale_x", kf(s, values.scale_x[0]), kf(e, values.scale_x[1]))
                    add("scale_y", kf(s, values.scale_y[0]), kf(e, values.scale_y[1]))
                    add("location_x", kf(s, values.location_x[0]), kf(e, values.location_x[1]))
                    add("location_y", kf(s, values.location_y[0]), kf(e, values.location_y[1]))

                if action == MenuAnimate.NONE:
                    _reset_motion()

                else:
                    
                    if not isinstance(clip.data.get("effects"), list):
                        clip.data["effects"] = []

                    
                    if action == MenuAnimate.SLIDE_IN_LEFT:
                        bx = _base('location_x', in_end)
                        self._remove_keypoints_in_range(clip.data["location_x"], s, in_end)
                        add("location_x", kf(s, bx - 1.0), kf(in_end, bx))
                    elif action == MenuAnimate.SLIDE_IN_RIGHT:
                        bx = _base('location_x', in_end)
                        self._remove_keypoints_in_range(clip.data["location_x"], s, in_end)
                        add("location_x", kf(s, bx + 1.0), kf(in_end, bx))
                    elif action == MenuAnimate.SLIDE_IN_TOP:
                        by = _base('location_y', in_end)
                        self._remove_keypoints_in_range(clip.data["location_y"], s, in_end)
                        add("location_y", kf(s, by - 1.0), kf(in_end, by))
                    elif action == MenuAnimate.SLIDE_IN_BOTTOM:
                        by = _base('location_y', in_end)
                        self._remove_keypoints_in_range(clip.data["location_y"], s, in_end)
                        add("location_y", kf(s, by + 1.0), kf(in_end, by))

                    
                    elif action == MenuAnimate.SLIDE_OUT_LEFT:
                        bx = _base('location_x', out_start)
                        self._remove_keypoints_in_range(clip.data["location_x"], out_start, e)
                        add("location_x", kf(out_start, bx), kf(e, bx - 1.0))
                    elif action == MenuAnimate.SLIDE_OUT_RIGHT:
                        bx = _base('location_x', out_start)
                        self._remove_keypoints_in_range(clip.data["location_x"], out_start, e)
                        add("location_x", kf(out_start, bx), kf(e, bx + 1.0))
                    elif action == MenuAnimate.SLIDE_OUT_TOP:
                        by = _base('location_y', out_start)
                        self._remove_keypoints_in_range(clip.data["location_y"], out_start, e)
                        add("location_y", kf(out_start, by), kf(e, by - 1.0))
                    elif action == MenuAnimate.SLIDE_OUT_BOTTOM:
                        by = _base('location_y', out_start)
                        self._remove_keypoints_in_range(clip.data["location_y"], out_start, e)
                        add("location_y", kf(out_start, by), kf(e, by + 1.0))

                    
                    elif action == MenuAnimate.BLUR_IN:
                        _make_blur_fx(s, 50.0, in_end, 0.0)
                        ba = _base('alpha', in_end)
                        self._remove_keypoints_in_range(clip.data["alpha"], s, in_end)
                        add("alpha", kf(s, 0.0), kf(in_end, ba))

                    
                    elif action == MenuAnimate.BLUR_OUT:
                        _make_blur_fx(out_start, 0.0, e, 50.0)
                        ba = _base('alpha', out_start)
                        self._remove_keypoints_in_range(clip.data["alpha"], out_start, e)
                        add("alpha", kf(out_start, ba), kf(e, 0.0))

                    
                    elif action in (MenuAnimate.WIPE_IN_CIRCLE_EXPAND,
                                    MenuAnimate.WIPE_IN_CIRCLE_SHRINK,
                                    MenuAnimate.WIPE_IN_FADE,
                                    MenuAnimate.WIPE_IN_LEFT, MenuAnimate.WIPE_IN_RIGHT,
                                    MenuAnimate.WIPE_IN_TOP,  MenuAnimate.WIPE_IN_BOTTOM):
                        _make_wipe_fx(_WIPE_SVG[action], s, in_end, 1.0, -1.0)

                    
                    elif action in (MenuAnimate.WIPE_OUT_CIRCLE_EXPAND,
                                    MenuAnimate.WIPE_OUT_CIRCLE_SHRINK,
                                    MenuAnimate.WIPE_OUT_FADE,
                                    MenuAnimate.WIPE_OUT_LEFT, MenuAnimate.WIPE_OUT_RIGHT,
                                    MenuAnimate.WIPE_OUT_TOP,  MenuAnimate.WIPE_OUT_BOTTOM):
                        _make_wipe_fx(_WIPE_SVG[action], out_start, e, -1.0, 1.0)

                    
                    elif action in (MenuAnimate.FOCUS_WIPE_IN_CIRCLE_EXPAND,
                                    MenuAnimate.FOCUS_WIPE_IN_CIRCLE_SHRINK,
                                    MenuAnimate.FOCUS_WIPE_IN_LEFT, MenuAnimate.FOCUS_WIPE_IN_RIGHT,
                                    MenuAnimate.FOCUS_WIPE_IN_TOP,  MenuAnimate.FOCUS_WIPE_IN_BOTTOM):
                        _make_blur_fx(s, 50.0, in_end, 0.0)
                        _make_wipe_fx(_WIPE_SVG[action], s, in_end, 1.0, -1.0, contrast=10.0)

                    
                    elif action in (MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_EXPAND,
                                    MenuAnimate.FOCUS_WIPE_OUT_CIRCLE_SHRINK,
                                    MenuAnimate.FOCUS_WIPE_OUT_LEFT, MenuAnimate.FOCUS_WIPE_OUT_RIGHT,
                                    MenuAnimate.FOCUS_WIPE_OUT_TOP,  MenuAnimate.FOCUS_WIPE_OUT_BOTTOM):
                        _make_blur_fx(out_start, 0.0, e, 50.0)
                        _make_wipe_fx(_WIPE_SVG[action], out_start, e, -1.0, 1.0, contrast=10.0)

                    
                    elif action == MenuAnimate.POP_IN:
                        peak = in_end - max(1, round(0.2 * (in_end - s)))
                        bsx = _base('scale_x', in_end)
                        bsy = _base('scale_y', in_end)
                        ba  = _base('alpha',   in_end)
                        for prop in ("scale_x", "scale_y", "alpha"):
                            self._remove_keypoints_in_range(clip.data[prop], s, in_end)
                        add("scale_x", kf(s, 0.0), kf(peak, 1.1 * bsx), kf(in_end, bsx))
                        add("scale_y", kf(s, 0.0), kf(peak, 1.1 * bsy), kf(in_end, bsy))
                        add("alpha",   kf(s, 0.0), kf(in_end, ba))
                    elif action == MenuAnimate.POP_OUT:
                        peak = out_start + max(1, round(0.2 * (e - out_start)))
                        bsx = _base('scale_x', out_start)
                        bsy = _base('scale_y', out_start)
                        ba  = _base('alpha',   out_start)
                        for prop in ("scale_x", "scale_y", "alpha"):
                            self._remove_keypoints_in_range(clip.data[prop], out_start, e)
                        add("scale_x", kf(out_start, bsx), kf(peak, 1.1 * bsx), kf(e, 0.0))
                        add("scale_y", kf(out_start, bsy), kf(peak, 1.1 * bsy), kf(e, 0.0))
                        add("alpha",   kf(out_start, ba), kf(e, 0.0))

                    
                    elif action == MenuAnimate.SPIRAL_IN:
                        br  = _base('rotation', in_end)
                        bsx = _base('scale_x',  in_end)
                        bsy = _base('scale_y',  in_end)
                        ba  = _base('alpha',    in_end)
                        for prop in ("rotation", "scale_x", "scale_y", "alpha"):
                            self._remove_keypoints_in_range(clip.data[prop], s, in_end)
                        add("rotation", kf(s, -360.0 + br), kf(in_end, br))
                        add("scale_x",  kf(s, 0.0),         kf(in_end, bsx))
                        add("scale_y",  kf(s, 0.0),         kf(in_end, bsy))
                        add("alpha",    kf(s, 0.0),         kf(in_end, ba))
                    elif action == MenuAnimate.SPIRAL_OUT:
                        br  = _base('rotation', out_start)
                        bsx = _base('scale_x',  out_start)
                        bsy = _base('scale_y',  out_start)
                        ba  = _base('alpha',    out_start)
                        for prop in ("rotation", "scale_x", "scale_y", "alpha"):
                            self._remove_keypoints_in_range(clip.data[prop], out_start, e)
                        add("rotation", kf(out_start, br),  kf(e, 360.0 + br))
                        add("scale_x",  kf(out_start, bsx), kf(e, 0.0))
                        add("scale_y",  kf(out_start, bsy), kf(e, 0.0))
                        add("alpha",    kf(out_start, ba),  kf(e, 0.0))

                    
                    elif action in _JSON_ANIM:
                        if action in _EMPHASIS_ACTIONS:
                            _apply_preset(_JSON_ANIM[action], emph_start, emph_end, emph_start)
                        elif action in _IN_ACTIONS:
                            _apply_preset(_JSON_ANIM[action], s, in_end, in_end)
                        else:
                            _apply_preset(_JSON_ANIM[action], out_start, e, out_start)

                    
                    elif action == MenuAnimate.CAM_PUSH_IN:
                        _apply_camera_motion(push_pull_keyframes(zoom_in=True))
                    elif action == MenuAnimate.CAM_PULL_OUT:
                        _apply_camera_motion(push_pull_keyframes(zoom_in=False))

                    
                    elif action in (MenuAnimate.CAM_PAN_AUTO,
                                    MenuAnimate.CAM_PAN_LEFT,  MenuAnimate.CAM_PAN_RIGHT,
                                    MenuAnimate.CAM_PAN_UP,    MenuAnimate.CAM_PAN_DOWN):
                        pan_direction = {
                            MenuAnimate.CAM_PAN_AUTO: PAN_AUTO,
                            MenuAnimate.CAM_PAN_LEFT: PAN_LEFT,
                            MenuAnimate.CAM_PAN_RIGHT: PAN_RIGHT,
                            MenuAnimate.CAM_PAN_UP: PAN_UP,
                            MenuAnimate.CAM_PAN_DOWN: PAN_DOWN,
                        }[action]
                        _apply_camera_motion(camera_pan_keyframes(pan_direction, *_camera_context()))

                    
                    elif action in (
                            MenuAnimate.KEN_BURNS_IN, MenuAnimate.KEN_BURNS_OUT,
                            MenuAnimate.KEN_BURNS_IN_LEFT_TO_RIGHT,
                            MenuAnimate.KEN_BURNS_IN_RIGHT_TO_LEFT,
                            MenuAnimate.KEN_BURNS_IN_TOP_TO_BOTTOM,
                            MenuAnimate.KEN_BURNS_IN_BOTTOM_TO_TOP,
                            MenuAnimate.KEN_BURNS_OUT_LEFT_TO_RIGHT,
                            MenuAnimate.KEN_BURNS_OUT_RIGHT_TO_LEFT,
                            MenuAnimate.KEN_BURNS_OUT_TOP_TO_BOTTOM,
                            MenuAnimate.KEN_BURNS_OUT_BOTTOM_TO_TOP):
                        direction = {
                            MenuAnimate.KEN_BURNS_IN: KEN_BURNS_AUTO,
                            MenuAnimate.KEN_BURNS_OUT: KEN_BURNS_AUTO,
                            MenuAnimate.KEN_BURNS_IN_LEFT_TO_RIGHT: KEN_BURNS_LEFT_TO_RIGHT,
                            MenuAnimate.KEN_BURNS_IN_RIGHT_TO_LEFT: KEN_BURNS_RIGHT_TO_LEFT,
                            MenuAnimate.KEN_BURNS_IN_TOP_TO_BOTTOM: KEN_BURNS_TOP_TO_BOTTOM,
                            MenuAnimate.KEN_BURNS_IN_BOTTOM_TO_TOP: KEN_BURNS_BOTTOM_TO_TOP,
                            MenuAnimate.KEN_BURNS_OUT_LEFT_TO_RIGHT: KEN_BURNS_LEFT_TO_RIGHT,
                            MenuAnimate.KEN_BURNS_OUT_RIGHT_TO_LEFT: KEN_BURNS_RIGHT_TO_LEFT,
                            MenuAnimate.KEN_BURNS_OUT_TOP_TO_BOTTOM: KEN_BURNS_TOP_TO_BOTTOM,
                            MenuAnimate.KEN_BURNS_OUT_BOTTOM_TO_TOP: KEN_BURNS_BOTTOM_TO_TOP,
                        }[action]
                        zoom_in = action in (
                            MenuAnimate.KEN_BURNS_IN,
                            MenuAnimate.KEN_BURNS_IN_LEFT_TO_RIGHT,
                            MenuAnimate.KEN_BURNS_IN_RIGHT_TO_LEFT,
                            MenuAnimate.KEN_BURNS_IN_TOP_TO_BOTTOM,
                            MenuAnimate.KEN_BURNS_IN_BOTTOM_TO_TOP)
                        _apply_camera_motion(ken_burns_keyframes(zoom_in, direction, *_camera_context()))

                    
                    elif action == MenuAnimate.CREDITS_UP:
                        clip.data["scale"] = smartedit.SCALE_CROP
                        add("location_y",
                            kf(s,  1.0, smartedit.LINEAR),
                            kf(e, -1.0, smartedit.LINEAR))
                    elif action == MenuAnimate.CREDITS_DOWN:
                        clip.data["scale"] = smartedit.SCALE_CROP
                        add("location_y",
                            kf(s, -1.0, smartedit.LINEAR),
                            kf(e,  1.0, smartedit.LINEAR))

                self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True, transaction_id=tid)
        finally:
            if not transaction_id:
                get_app().updates.transaction_id = None

    def AddPoint(self, keyframe, new_point):
        """Add a Point to a Keyframe dict. Always remove existing points,
        if any collisions are found"""
        
        cleaned_points = [
            point
            for point in keyframe["Points"]
            if point.get("co", {}).get("X") != new_point.get("co", {}).get("X")
        ]
        cleaned_points.append(new_point)

        
        keyframe["Points"] = cleaned_points

    def _remove_keypoints_in_range(self, points_data, frame_start, frame_end):
        """Remove all keyframe points with X in [frame_start, frame_end]."""
        points_data["Points"] = [
            p for p in points_data["Points"]
            if not (frame_start <= p.get("co", {}).get("X", -1) <= frame_end)
        ]


    def Copy_Triggered(self, action, clip_ids, tran_ids, effect_ids):
        """Callback for copy context menus"""
        log.debug(action)

        
        copied_objects = []
        for clip_id in clip_ids:

            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            
            if action == MenuCopy.KEYFRAMES_ALL:
                clip.data = {'alpha': clip.data['alpha'],
                             'gravity': clip.data['gravity'],
                             'scale_x': clip.data['scale_x'],
                             'scale_y': clip.data['scale_y'],
                             'shear_x': clip.data['shear_x'],
                             'shear_y': clip.data['shear_y'],
                             'rotation': clip.data['rotation'],
                             'location_x': clip.data['location_x'],
                             'location_y': clip.data['location_y'],
                             'time': clip.data['time'],
                             'volume': clip.data['volume']}
            elif action == MenuCopy.KEYFRAMES_ALPHA:
                clip.data = {'alpha': clip.data['alpha']}
            elif action == MenuCopy.KEYFRAMES_SCALE:
                clip.data = {'gravity': clip.data['gravity'],
                             'scale_x': clip.data['scale_x'],
                             'scale_y': clip.data['scale_y']}
            elif action == MenuCopy.KEYFRAMES_SHEAR:
                clip.data = {'shear_x': clip.data['shear_x'],
                             'shear_y': clip.data['shear_y']}
            elif action == MenuCopy.KEYFRAMES_ROTATE:
                clip.data = {'gravity': clip.data['gravity'],
                             'rotation': clip.data['rotation']}
            elif action == MenuCopy.KEYFRAMES_LOCATION:
                clip.data = {'gravity': clip.data['gravity'],
                             'location_x': clip.data['location_x'],
                             'location_y': clip.data['location_y']}
            elif action == MenuCopy.KEYFRAMES_TIME:
                clip.data = {'time': clip.data['time']}
            elif action == MenuCopy.KEYFRAMES_VOLUME:
                clip.data = {'volume': clip.data['volume']}
            elif action == MenuCopy.ALL_EFFECTS:
                clip.data = {'effects': clip.data['effects']}

            
            copied_objects.append(clip)

        
        for tran_id in tran_ids:

            
            tran = Transition.get(id=tran_id)
            if not tran:
                
                continue

            if action == MenuCopy.KEYFRAMES_ALL:
                tran.data = {'brightness': tran.data['brightness'],
                             'contrast': tran.data['contrast']}
            elif action == MenuCopy.KEYFRAMES_BRIGHTNESS:
                tran.data = {'brightness': tran.data['brightness']}
            elif action == MenuCopy.KEYFRAMES_CONTRAST:
                tran.data = {'contrast': tran.data['contrast']}

            
            copied_objects.append(tran)

        
        for effect_id in effect_ids:

            
            effect = Effect.get(id=effect_id)
            if not effect:
                
                continue

            if action == MenuCopy.EFFECT:
                copied_objects.append(effect)

        
        get_app().clipboard().setMimeData(ClipboardManager.to_mime(copied_objects))

    def RemoveGap_Triggered(self, found_start, found_end, layer_number):
        """Callback for removing gap context menus"""
        log.info(f"Removing gap from {found_start} to {found_end} on layer {layer_number}")

        
        tid = str(uuid.uuid4())
        get_app().updates.transaction_id = tid

        gap_size = found_end - found_start
        for clip in Clip.filter(layer=layer_number) + Transition.filter(layer=layer_number):
            if clip.data.get("position", 0.0) > found_start:
                clip.data["position"] -= gap_size
                clip.save()

        
        get_app().updates.transaction_id = None

    def RemoveAllGaps_Triggered(self, found_start, layer_number):
        """Callback for removing all gaps on a layer starting from the detected gap"""
        log.info(f"Removing all gaps on layer {layer_number} starting from {found_start}")

        
        tid = str(uuid.uuid4())
        get_app().updates.transaction_id = tid

        
        clips_and_transitions = sorted(
            Clip.filter(layer=layer_number) + Transition.filter(layer=layer_number),
            key=lambda c: c.data.get("position", 0.0)
        )

        
        groups = []
        current_group = []
        current_group_start = None
        current_group_end = None

        for item in clips_and_transitions:
            left_edge = item.data.get("position", 0.0)
            right_edge = left_edge + (item.data.get("end", 0.0) - item.data.get("start", 0.0))

            if current_group and left_edge <= current_group_end:
                current_group.append(item)
                current_group_end = max(current_group_end, right_edge)
            else:
                if current_group:
                    groups.append((current_group_start, current_group_end, current_group))
                current_group = [item]
                current_group_start = left_edge
                current_group_end = right_edge

        if current_group:
            groups.append((current_group_start, current_group_end, current_group))

        
        last_end = found_start
        total_offset = 0.0
        modified_items = []

        for group_start, group_end, group_items in groups:
            
            if group_end <= found_start:
                last_end = max(last_end, group_end)
                continue

            
            shifted_start = group_start - total_offset

            
            if shifted_start > last_end:
                gap_size = shifted_start - last_end
                total_offset += gap_size
                shifted_start -= gap_size
                log.info(f"Removing gap from {last_end} to {last_end + gap_size} on layer {layer_number}")

            
            for item in group_items:
                item.data["position"] -= total_offset
                modified_items.append(item)

            last_end = group_end - total_offset

        
        for item in modified_items:
            item.save()

        
        get_app().updates.transaction_id = None

    def Paste_Triggered(self, action, clip_ids, tran_ids):
        """Callback for paste context menus"""
        log.debug(action)

        if ViewClass == TimelineWidget and self._context_menu_paste_data and not clip_ids and not tran_ids:
            paste_data = dict(self._context_menu_paste_data)
            self._context_menu_paste_data = None
            self._handle_paste_callback(clip_ids, tran_ids, paste_data)
            return

        
        if self.context_menu_cursor_position:
            global_mouse_pos = self.context_menu_cursor_position
        else:
            global_mouse_pos = QCursor.pos()
        local_mouse_pos = self.mapFromGlobal(global_mouse_pos)

        if ViewClass == TimelineWidget:
            seconds, track_number = self._qwidget_paste_coordinates(local_mouse_pos, clip_ids, tran_ids)
            self._handle_paste_callback(clip_ids, tran_ids, {"position": seconds, "track": track_number})
            return

        self.run_js(
            JS_SCOPE_SELECTOR + ".getJavaScriptPosition({}, {});".format(
                local_mouse_pos.x(), local_mouse_pos.y()
            ),
            partial(self._handle_paste_callback, clip_ids, tran_ids),
        )

    def Nudge_Triggered(self, action, clip_ids, tran_ids):
        """Callback for nudging clips/transitions by a specified number of frames."""
        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        nudge_duration = float(action) / fps_float  
        log.debug(f"Nudging by {nudge_duration} seconds")

        
        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip:
                continue

            
            new_position = max(clip.data['position'] + nudge_duration, 0.0)
            clip.data['position'] = new_position
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)

        
        for tran_id in tran_ids:
            tran = Transition.get(id=tran_id)
            if not tran:
                continue

            
            new_position = max(tran.data['position'] + nudge_duration, 0.0)
            tran.data['position'] = new_position
            self.update_transition_data(tran.data, only_basic_props=False)

    def Align_Triggered(self, action, clip_ids, tran_ids):
        """Callback for alignment context menus"""
        log.debug(action)

        left_edge = -1.0
        right_edge = -1.0

        
        for clip_id in clip_ids:
            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            position = float(clip.data["position"])
            start_of_clip = float(clip.data["start"])
            end_of_clip = float(clip.data["end"])

            if position < left_edge or left_edge == -1.0:
                left_edge = position
            if position + (end_of_clip - start_of_clip) > right_edge or right_edge == -1.0:
                right_edge = position + (end_of_clip - start_of_clip)

        
        for tran_id in tran_ids:
            
            tran = Transition.get(id=tran_id)
            if not tran:
                
                continue

            position = float(tran.data["position"])
            start_of_tran = float(tran.data["start"])
            end_of_tran = float(tran.data["end"])

            if position < left_edge or left_edge == -1.0:
                left_edge = position
            if position + (end_of_tran - start_of_tran) > right_edge or right_edge == -1.0:
                right_edge = position + (end_of_tran - start_of_tran)

        
        for clip_id in clip_ids:
            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            if action == MenuAlign.LEFT:
                clip.data['position'] = left_edge
            elif action == MenuAlign.RIGHT:
                position = float(clip.data["position"])
                start_of_clip = float(clip.data["start"])
                end_of_clip = float(clip.data["end"])
                right_clip_edge = position + (end_of_clip - start_of_clip)

                clip.data['position'] = position + (right_edge - right_clip_edge)

            
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)

        
        for tran_id in tran_ids:
            
            tran = Transition.get(id=tran_id)
            if not tran:
                
                continue

            if action == MenuAlign.LEFT:
                tran.data['position'] = left_edge
            elif action == MenuAlign.RIGHT:
                position = float(tran.data["position"])
                start_of_tran = float(tran.data["start"])
                end_of_tran = float(tran.data["end"])
                right_tran_edge = position + (end_of_tran - start_of_tran)

                tran.data['position'] = position + (right_edge - right_tran_edge)

            
            self.update_transition_data(tran.data, only_basic_props=False)

    def Fade_Triggered(self, action, clip_ids, position="Entire Clip", transaction_id=None):
        """Callback for fade context menus — fades both alpha (video) and volume (audio)"""
        log.debug(action)

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        clips_with_waveforms = []

        
        tid = transaction_id or self.get_uuid()

        try:
            
            get_app().updates.transaction_id = tid

            
            for clip_id in clip_ids:

                
                clip = Clip.get(id=clip_id)
                if not clip:
                    continue

                start_of_clip = round(float(clip.data["start"]) * fps_float) + 1
                end_of_clip = round(float(clip.data["end"]) * fps_float) + 1

                
                
                start_animation = start_of_clip
                end_animation = end_of_clip
                if position == "Start of Clip" and action in [MenuFade.IN_FAST, MenuFade.OUT_FAST]:
                    start_animation = start_of_clip
                    end_animation = min(start_of_clip + (1.0 * fps_float), end_of_clip)
                elif position == "Start of Clip" and action in [MenuFade.IN_SLOW, MenuFade.OUT_SLOW]:
                    start_animation = start_of_clip
                    end_animation = min(start_of_clip + (3.0 * fps_float), end_of_clip)
                elif position == "End of Clip" and action in [MenuFade.IN_FAST, MenuFade.OUT_FAST]:
                    start_animation = max(1.0, end_of_clip - (1.0 * fps_float))
                    end_animation = end_of_clip
                elif position == "End of Clip" and action in [MenuFade.IN_SLOW, MenuFade.OUT_SLOW]:
                    start_animation = max(1.0, end_of_clip - (3.0 * fps_float))
                    end_animation = end_of_clip

                reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
                fade_alpha = bool(reader.get("has_video", True)) or bool(clip.data.get("waveform", False))
                fade_volume = bool(reader.get("has_audio", True))

                
                
                
                if position == "Entire Clip" and action in [MenuFade.IN_OUT_FAST, MenuFade.IN_OUT_SLOW]:
                    fade_seconds = 1.0 if action == MenuFade.IN_OUT_FAST else 3.0
                    clip_frames = max(0.0, end_of_clip - start_of_clip)
                    
                    
                    fade_frames = min(fade_seconds * fps_float, clip_frames / 3.0)
                    fade_in_end = start_of_clip + fade_frames
                    fade_out_start = end_of_clip - fade_frames

                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    target_alpha = c.alpha.GetValue(int(round(fade_in_end))) if c else 1.0
                    source_alpha = c.alpha.GetValue(int(round(fade_out_start))) if c else 1.0
                    target_vol = c.volume.GetValue(int(round(fade_in_end))) if c else 1.0
                    source_vol = c.volume.GetValue(int(round(fade_out_start))) if c else 1.0

                    cleanup_end = min(start_of_clip + (3.0 * fps_float), end_of_clip)
                    cleanup_start = max(start_of_clip, end_of_clip - (3.0 * fps_float))

                    def apply_combined_fade(keyframe, target_value, source_value):
                        self._remove_keypoints_in_range(keyframe, start_of_clip, cleanup_end)
                        self._remove_keypoints_in_range(keyframe, cleanup_start, end_of_clip)
                        self.AddPoint(keyframe, json.loads(smartedit.Point(
                            start_of_clip, 0.0, smartedit.BEZIER).Json()))
                        self.AddPoint(keyframe, json.loads(smartedit.Point(
                            fade_in_end, target_value, smartedit.BEZIER).Json()))
                        self.AddPoint(keyframe, json.loads(smartedit.Point(
                            fade_out_start, source_value, smartedit.BEZIER).Json()))
                        self.AddPoint(keyframe, json.loads(smartedit.Point(
                            end_of_clip, 0.0, smartedit.BEZIER).Json()))

                    if fade_alpha:
                        apply_combined_fade(clip.data['alpha'], target_alpha, source_alpha)
                    if fade_volume:
                        apply_combined_fade(clip.data['volume'], target_vol, source_vol)

                    self.update_clip_data(
                        clip.data, only_basic_props=False, ignore_reader=True, transaction_id=tid)
                    if clip.data.get("ui", {}).get("audio_data", []):
                        clips_with_waveforms.append(clip.id)
                    continue

                if action == MenuFade.NONE:
                    p_object = json.loads(smartedit.Point(1, 1.0, smartedit.BEZIER).Json())
                    if fade_alpha:
                        clip.data['alpha'] = {"Points": [p_object]}
                    if fade_volume:
                        clip.data['volume'] = {"Points": [p_object]}

                elif action in [MenuFade.IN_FAST, MenuFade.IN_SLOW]:
                    
                    
                    fade_in_zone_end = min(start_of_clip + (3.0 * fps_float), end_of_clip)

                    
                    
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    target_alpha = c.alpha.GetValue(int(round(fade_in_zone_end))) if c else 1.0
                    target_vol = c.volume.GetValue(int(round(fade_in_zone_end))) if c else 1.0

                    if fade_alpha:
                        self._remove_keypoints_in_range(clip.data['alpha'], start_of_clip, fade_in_zone_end)
                        self.AddPoint(clip.data['alpha'], json.loads(smartedit.Point(start_animation, 0.0, smartedit.BEZIER).Json()))
                        self.AddPoint(clip.data['alpha'], json.loads(smartedit.Point(end_animation, target_alpha, smartedit.BEZIER).Json()))
                    if fade_volume:
                        self._remove_keypoints_in_range(clip.data['volume'], start_of_clip, fade_in_zone_end)
                        self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(start_animation, 0.0, smartedit.BEZIER).Json()))
                        self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(end_animation, target_vol, smartedit.BEZIER).Json()))

                elif action in [MenuFade.OUT_FAST, MenuFade.OUT_SLOW]:
                    
                    
                    fade_out_zone_start = max(1.0, end_of_clip - (3.0 * fps_float))

                    
                    
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    source_alpha = c.alpha.GetValue(int(round(fade_out_zone_start))) if c else 1.0
                    source_vol = c.volume.GetValue(int(round(fade_out_zone_start))) if c else 1.0

                    if fade_alpha:
                        self._remove_keypoints_in_range(clip.data['alpha'], fade_out_zone_start, end_of_clip)
                        self.AddPoint(clip.data['alpha'], json.loads(smartedit.Point(start_animation, source_alpha, smartedit.BEZIER).Json()))
                        self.AddPoint(clip.data['alpha'], json.loads(smartedit.Point(end_animation, 0.0, smartedit.BEZIER).Json()))
                    if fade_volume:
                        self._remove_keypoints_in_range(clip.data['volume'], fade_out_zone_start, end_of_clip)
                        self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(start_animation, source_vol, smartedit.BEZIER).Json()))
                        self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(end_animation, 0.0, smartedit.BEZIER).Json()))

                
                self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True, transaction_id=tid)

                
                if clip.data.get("ui", {}).get("audio_data", []):
                    clips_with_waveforms.append(clip.id)

            
            if clips_with_waveforms:
                self.Show_Waveform_Triggered(clips_with_waveforms, transaction_id=tid)
        finally:
            
            if not transaction_id:
                get_app().updates.transaction_id = None

    @pyqtSlot(str, str, float)
    def RazorSliceAtCursor(self, clip_id, trans_id, cursor_position):
        """Callback from javascript that the razor tool was clicked"""

        
        slice_mode = MenuSlice.KEEP_BOTH
        if modifiers_has(QCoreApplication.instance().keyboardModifiers(), Qt.ControlModifier):
            slice_mode = MenuSlice.KEEP_RIGHT
        elif modifiers_has(QCoreApplication.instance().keyboardModifiers(), Qt.ShiftModifier):
            slice_mode = MenuSlice.KEEP_LEFT

        if clip_id:
            
            QTimer.singleShot(0, partial(self.Slice_Triggered, slice_mode, [clip_id], [], cursor_position))
        elif trans_id:
            
            QTimer.singleShot(0, partial(self.Slice_Triggered, slice_mode, [], [trans_id], cursor_position))

    def Slice_Triggered(self, action, clip_ids, trans_ids, playhead_position=0, ripple=False):
        """Callback for slice context menus"""
        
        fps = get_app().project.get("fps")
        fps_num = float(fps["num"])
        fps_den = float(fps["den"])

        
        locked_layers = [t.get("number") for t in get_app().project.get("layers") if t.get("lock")]

        
        tid = self.get_uuid()
        get_app().updates.transaction_id = tid

        
        get_app().window.IgnoreUpdates.emit(True, True)
        new_starting_frame = -1

        try:
            
            playhead_position = float(round((playhead_position * fps_num) / fps_den) * fps_den) / fps_num
            if action == MenuSlice.KEEP_LEFT: playhead_position += fps_den / fps_num

            
            for clip_id in clip_ids:

                
                clip = Clip.get(id=clip_id)
                if not clip or clip.data.get("layer") in locked_layers:
                    continue

                original_position = float(clip.data["position"])  
                start_of_clip = float(clip.data["start"])  
                end_of_clip = float(clip.data["end"])  
                original_duration = end_of_clip - start_of_clip  

                if action == MenuSlice.KEEP_LEFT:
                    
                    new_end = start_of_clip + (playhead_position - original_position)
                    clip.data["end"] = new_end
                    clip.data["duration"] = max(0.0, new_end - start_of_clip)

                    if ripple:
                        removed_duration = original_duration - (clip.data["end"] - start_of_clip)
                        self.ripple_delete_gap(playhead_position, clip.data["layer"], removed_duration)

                elif action == MenuSlice.KEEP_RIGHT:
                    
                    new_start = start_of_clip + (playhead_position - original_position)
                    clip.data["position"] = playhead_position  
                    clip.data["start"] = new_start
                    clip.data["duration"] = max(0.0, end_of_clip - new_start)

                    if ripple:
                        removed_duration = original_duration - (end_of_clip - new_start)
                        clip.data["position"] = original_position  
                        self.ripple_delete_gap(playhead_position, clip.data["layer"], removed_duration)

                        
                        new_starting_frame = original_position * (fps_num / fps_den) + 1

                elif action == MenuSlice.KEEP_BOTH:
                    
                    new_end = start_of_clip + (playhead_position - original_position)
                    clip.data["end"] = new_end
                    clip.data["duration"] = max(0.0, new_end - start_of_clip)

                    
                    right_clip = Clip.get(id=clip_id)
                    if not right_clip:
                        continue

                    
                    
                    
                    right_clip_data = deepcopy(right_clip.data)
                    right_clip_key = list(right_clip.key)

                    right_clip.id = None
                    right_clip.type = 'insert'
                    right_clip.data = right_clip_data
                    right_clip.data.pop('id', None)
                    if len(right_clip_key) > 1:
                        right_clip_key.pop(1)
                    right_clip.key = right_clip_key
                    right_clip.data["position"] = playhead_position
                    right_clip.data["start"] = clip.data["end"]
                    right_clip.data["end"] = end_of_clip
                    right_start = float(right_clip.data["start"])
                    right_end = float(right_clip.data.get("end", right_start))
                    right_clip.data["duration"] = max(0.0, right_end - right_start)
                    self._assign_new_effect_ids(right_clip.data)
                    right_clip.save()

                
                self.update_clip_data(clip.data, only_basic_props=True, ignore_reader=True)

            
            self.redraw_audio_timer.start()

            
            for trans_id in trans_ids:
                trans = Transition.get(id=trans_id)
                if not trans or trans.data.get("layer") in locked_layers:
                    continue

                original_position = float(trans.data["position"])  
                start_of_tran = float(trans.data["start"])  
                end_of_tran = float(trans.data["end"])  
                original_duration = end_of_tran - start_of_tran  

                if action == MenuSlice.KEEP_LEFT:
                    
                    new_end = start_of_tran + (playhead_position - original_position)
                    trans.data["end"] = new_end
                    trans.data["duration"] = max(0.0, new_end - start_of_tran)

                    if ripple:
                        removed_duration = original_duration - (trans.data["end"] - start_of_tran)
                        self.ripple_delete_gap(playhead_position, trans.data["layer"], removed_duration)

                elif action == MenuSlice.KEEP_RIGHT:
                    
                    new_start = start_of_tran + (playhead_position - original_position)
                    trans.data["position"] = playhead_position
                    trans.data["start"] = new_start
                    trans.data["duration"] = max(0.0, end_of_tran - new_start)
                    if ripple:
                        removed_duration = original_duration - (end_of_tran - new_start)
                        trans.data["position"] = original_position
                        self.ripple_delete_gap(playhead_position, trans.data["layer"], removed_duration)

                        
                        new_starting_frame = original_position * (fps_num / fps_den) + 1

                elif action == MenuSlice.KEEP_BOTH:
                    
                    new_end = start_of_tran + (playhead_position - original_position)
                    trans.data["end"] = new_end
                    trans.data["duration"] = max(0.0, new_end - start_of_tran)

                    
                    right_tran = Transition.get(id=trans_id)
                    if not right_tran:
                        continue

                    
                    
                    right_tran_data = deepcopy(right_tran.data)
                    right_tran_key = list(right_tran.key)
                    right_tran.id = None
                    right_tran.type = 'insert'
                    right_tran.data = right_tran_data
                    right_tran.data.pop('id', None)
                    if len(right_tran_key) > 1:
                        right_tran_key.pop(1)
                    right_tran.key = right_tran_key
                    right_tran.data["position"] = playhead_position
                    right_tran.data["start"] = trans.data["end"]
                    right_tran.data["end"] = end_of_tran
                    right_start = float(right_tran.data["start"])
                    right_end = float(right_tran.data.get("end", right_start))
                    right_tran.data["duration"] = max(0.0, right_end - right_start)
                    right_tran.save()

                
                self.update_transition_data(trans.data, only_basic_props=False)
        finally:
            get_app().updates.transaction_id = None

            
            get_app().window.IgnoreUpdates.emit(False, True)

            if new_starting_frame != -1:
                
                self.window.SeekSignal.emit(round(new_starting_frame), True)

    def ripple_delete_gap(self, ripple_start, layer, ripple_gap):
        """Remove the ripple gap and adjust subsequent items"""
        
        clips = [clip for clip in Clip.filter(layer=layer) if clip.data.get("position", 0.0) >= ripple_start]
        transitions = [tran for tran in Transition.filter(layer=layer) if tran.data.get("position", 0.0) >= ripple_start]

        
        for clip in clips:
            clip.data["position"] -= ripple_gap
            clip.save()

        for trans in transitions:
            trans.data["position"] -= ripple_gap
            trans.save()

    def Volume_Triggered(self, action, clip_ids, position="Entire Clip", level=1.0, transaction_id=None):
        """Callback for volume context menus"""
        log.debug(action)

        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        clips_with_waveforms = []

        tid = transaction_id or self.get_uuid()

        try:
            get_app().updates.transaction_id = tid

            for clip_id in clip_ids:
                clip = Clip.get(id=clip_id)
                if not clip:
                    continue

                start_of_clip = round(float(clip.data["start"]) * fps_float) + 1
                end_of_clip = round(float(clip.data["end"]) * fps_float) + 1

                
                start_animation = start_of_clip
                end_animation = end_of_clip
                if position == "Start of Clip" and action in [MenuVolume.FADE_IN_FAST, MenuVolume.FADE_OUT_FAST]:
                    end_animation = min(start_of_clip + (1.0 * fps_float), end_of_clip)
                elif position == "Start of Clip" and action in [MenuVolume.FADE_IN_SLOW, MenuVolume.FADE_OUT_SLOW]:
                    end_animation = min(start_of_clip + (3.0 * fps_float), end_of_clip)
                elif position == "End of Clip" and action in [MenuVolume.FADE_IN_FAST, MenuVolume.FADE_OUT_FAST]:
                    start_animation = max(1.0, end_of_clip - (1.0 * fps_float))
                elif position == "End of Clip" and action in [MenuVolume.FADE_IN_SLOW, MenuVolume.FADE_OUT_SLOW]:
                    start_animation = max(1.0, end_of_clip - (3.0 * fps_float))

                
                if position == "Entire Clip" and action in [MenuVolume.FADE_IN_OUT_FAST, MenuVolume.FADE_IN_OUT_SLOW]:
                    if action == MenuVolume.FADE_IN_OUT_FAST:
                        self.Volume_Triggered(MenuVolume.FADE_IN_FAST, clip_ids, "Start of Clip", transaction_id=tid)
                        self.Volume_Triggered(MenuVolume.FADE_OUT_FAST, clip_ids, "End of Clip", transaction_id=tid)
                    else:
                        self.Volume_Triggered(MenuVolume.FADE_IN_SLOW, clip_ids, "Start of Clip", transaction_id=tid)
                        self.Volume_Triggered(MenuVolume.FADE_OUT_SLOW, clip_ids, "End of Clip", transaction_id=tid)
                    return

                if action == MenuVolume.NONE:
                    clip.data['volume'] = {"Points": [json.loads(smartedit.Point(1, 1.0, smartedit.BEZIER).Json())]}

                elif action == MenuVolume.LEVEL:
                    
                    clip.data['volume'] = {"Points": [json.loads(smartedit.Point(1, float(level) / 100.0, smartedit.BEZIER).Json())]}

                elif action in [MenuVolume.FADE_IN_FAST, MenuVolume.FADE_IN_SLOW]:
                    fade_in_zone_end = min(start_of_clip + (3.0 * fps_float), end_of_clip)
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    target_vol = c.volume.GetValue(int(round(fade_in_zone_end))) if c else 1.0
                    self._remove_keypoints_in_range(clip.data['volume'], start_of_clip, fade_in_zone_end)
                    self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(start_animation, 0.0, smartedit.BEZIER).Json()))
                    self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(end_animation, target_vol, smartedit.BEZIER).Json()))

                elif action in [MenuVolume.FADE_OUT_FAST, MenuVolume.FADE_OUT_SLOW]:
                    fade_out_zone_start = max(1.0, end_of_clip - (3.0 * fps_float))
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    source_vol = c.volume.GetValue(int(round(fade_out_zone_start))) if c else 1.0
                    self._remove_keypoints_in_range(clip.data['volume'], fade_out_zone_start, end_of_clip)
                    self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(start_animation, source_vol, smartedit.BEZIER).Json()))
                    self.AddPoint(clip.data['volume'], json.loads(smartedit.Point(end_animation, 0.0, smartedit.BEZIER).Json()))

                
                self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True, transaction_id=tid)

                if clip.data.get("ui", {}).get("audio_data", []):
                    clips_with_waveforms.append(clip.id)

            if clips_with_waveforms:
                self.Show_Waveform_Triggered(clips_with_waveforms, transaction_id=tid)
        finally:
            if not transaction_id:
                get_app().updates.transaction_id = None

    def Rotate_Triggered(self, action, clip_ids, position="Start of Clip"):
        """Callback for rotate context menus"""
        log.debug(action)

        
        for clip_id in clip_ids:

            
            clip = Clip.get(id=clip_id)
            if not clip:
                
                continue

            if action == MenuRotate.NONE:
                
                p = smartedit.Point(1, 0.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data['rotation'] = {"Points": [p_object]}

            if action == MenuRotate.RIGHT_90:
                
                p = smartedit.Point(1, 90.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data['rotation'] = {"Points": [p_object]}

            if action == MenuRotate.LEFT_90:
                
                p = smartedit.Point(1, -90.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data['rotation'] = {"Points": [p_object]}

            if action == MenuRotate.FLIP_180:
                
                p = smartedit.Point(1, 180.0, smartedit.BEZIER)
                p_object = json.loads(p.Json())
                clip.data['rotation'] = {"Points": [p_object]}

            
            self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)

    def No_Transform_Triggered(self, clip_ids):
        """Reset rotation, crop, and layout for all selected clips in a single undo step."""
        tid = self.get_uuid()
        get_app().updates.transaction_id = tid
        try:
            self.Rotate_Triggered(MenuRotate.NONE, clip_ids)
            self.Crop_Triggered(clip_ids, 'none')
            self.Layout_Triggered(MenuLayout.NONE, clip_ids)
        finally:
            get_app().updates.transaction_id = None

    def Time_Triggered(self, action, clip_ids, speed="1X", playhead_position=0.0):
        """Callback for time context menus"""
        log.debug(action)

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        clips_with_waveforms = []
        transaction_id = self.get_uuid()

        
        for clip_id in clip_ids:
            
            clip = Clip.get(id=clip_id)

            if not clip:
                
                continue

            
            original_clip_data = json.loads(json.dumps(clip.data))

            
            if clip.data.get("ui", {}).get("audio_data", []):
                clips_with_waveforms.append(clip.id)

            
            if action in [MenuTime.FREEZE, MenuTime.FREEZE_ZOOM]:
                freeze_seconds = float(speed)

                original_duration = clip.data["duration"]
                original_end = float(clip.data["end"])
                log.info('Updating timing for clip ID {}, original duration: {}'.format(clip.id, original_duration))
                log.debug(clip.data)

                
                clip.data["end"] = float(clip.data["end"]) + freeze_seconds
                clip.data["duration"] = float(clip.data["duration"]) + freeze_seconds

                
                start_animation_seconds = float(clip.data["start"]) + (playhead_position - float(clip.data["position"]))
                start_animation_frames = round(start_animation_seconds * fps_float) + 1
                start_animation_frames_value = start_animation_frames
                end_animation_seconds = start_animation_seconds + freeze_seconds
                end_animation_frames = round(end_animation_seconds * fps_float) + 1
                end_of_clip_seconds = float(clip.data["end"])
                end_of_clip_frames = round((end_of_clip_seconds) * fps_float) + 1
                end_of_clip_frames_value = round((original_end) * fps_float) + 1

                
                start_volume_value = 1.0

                
                if len(clip.data["time"]["Points"]) > 1:
                    del clip.data["time"]["Points"][-1]
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    if c:
                        start_animation_frames_value = c.time.GetLong(start_animation_frames)

                
                if len(clip.data["volume"]["Points"]) > 1:
                    c = self.window.timeline_sync.timeline.GetClip(clip_id)
                    if c:
                        start_volume_value = c.volume.GetValue(start_animation_frames)

                
                p = smartedit.Point(start_animation_frames, start_animation_frames_value, smartedit.LINEAR)
                self.AddPoint(clip.data['time'], json.loads(p.Json()))
                p1 = smartedit.Point(end_animation_frames, start_animation_frames_value, smartedit.LINEAR)
                self.AddPoint(clip.data['time'], json.loads(p1.Json()))
                p2 = smartedit.Point(end_of_clip_frames, end_of_clip_frames_value, smartedit.LINEAR)
                self.AddPoint(clip.data['time'], json.loads(p2.Json()))

                
                p = smartedit.Point(start_animation_frames - 1, start_volume_value, smartedit.LINEAR)
                self.AddPoint(clip.data['volume'], json.loads(p.Json()))
                p = smartedit.Point(start_animation_frames, 0.0, smartedit.LINEAR)
                self.AddPoint(clip.data['volume'], json.loads(p.Json()))
                p2 = smartedit.Point(end_animation_frames - 1, 0.0, smartedit.LINEAR)
                self.AddPoint(clip.data['volume'], json.loads(p2.Json()))
                p3 = smartedit.Point(end_animation_frames, start_volume_value, smartedit.LINEAR)
                self.AddPoint(clip.data['volume'], json.loads(p3.Json()))

                if action == MenuTime.FREEZE_ZOOM:
                    p = smartedit.Point(start_animation_frames, 1.0, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_x'], json.loads(p.Json()))
                    p = smartedit.Point(start_animation_frames, 1.0, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_y'], json.loads(p.Json()))
                    diff_halfed = (end_animation_frames - start_animation_frames) / 2.0
                    p1 = smartedit.Point(start_animation_frames + diff_halfed, 1.05, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_x'], json.loads(p1.Json()))
                    p1 = smartedit.Point(start_animation_frames + diff_halfed, 1.05, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_y'], json.loads(p1.Json()))
                    p1 = smartedit.Point(end_animation_frames, 1.0, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_x'], json.loads(p1.Json()))
                    p1 = smartedit.Point(end_animation_frames, 1.0, smartedit.BEZIER)
                    self.AddPoint(clip.data['scale_y'], json.loads(p1.Json()))

            else:

                if action == MenuTime.NONE:
                    
                    reset_repeat(clip)
                    reader = clip.data.get("reader", {}) or {}
                    try:
                        c_obj = self.window.timeline_sync.timeline.GetClip(clip_id)
                    except Exception:
                        c_obj = None

                    start_sec = float(clip.data.get("start", 0.0))
                    duration_sec = 0.0
                    try:
                        duration_sec = float(reader.get("duration", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        duration_sec = 0.0

                    if duration_sec <= 0.0 and c_obj:
                        try:
                            duration_sec = float(getattr(c_obj.Reader().info, "duration", 0.0))
                        except Exception:
                            duration_sec = 0.0
                    if duration_sec <= 0.0:
                        try:
                            duration_sec = float(clip.data.get("duration", 0.0))
                        except (TypeError, ValueError):
                            duration_sec = 0.0

                    if is_single_image_media(reader):
                        duration_sec = float(get_app().get_settings().get("default-image-length") or 10.0)

                    if duration_sec <= 0.0:
                        duration_sec = 1.0 / fps_float

                    target_frames = max(1, int(round(duration_sec * fps_float)))
                    snapped_duration = target_frames / fps_float
                    target_end_sec = start_sec + snapped_duration

                    
                    retime_clip(clip, target_end_sec, clip.data.get("position"), direction=1)

                    
                    clip.data["time"] = {"Points": [{"co": {"X": 1, "Y": 1}, "interpolation": smartedit.LINEAR}]}

                elif action == MenuTime.REVERSE:
                    start_sec = float(clip.data.get("start", 0.0))
                    try:
                        target_end_sec = float(clip.data.get("end", start_sec))
                    except (TypeError, ValueError):
                        target_end_sec = start_sec

                    if target_end_sec <= start_sec:
                        try:
                            duration_sec = float(clip.data.get("duration", 0.0))
                        except (TypeError, ValueError):
                            duration_sec = 0.0
                        if duration_sec <= 0.0:
                            duration_sec = 1.0 / fps_float
                        target_end_sec = start_sec + duration_sec

                    retime_clip(clip, target_end_sec, clip.data.get("position"), direction=-1)

                else:
                    speed_label = speed.replace('X', '')
                    parts = speed_label.split('/')
                    if len(parts) == 2:
                        speed_factor = float(parts[0]) / float(parts[1])
                    else:
                        speed_factor = float(speed_label)

                    original_duration = float(clip.data["end"]) - float(clip.data["start"])
                    new_duration = original_duration / speed_factor
                    new_end_time = float(clip.data["start"]) + new_duration
                    direction = 1 if action == MenuTime.FORWARD else -1

                    retime_clip(clip, new_end_time, clip.data.get("position"), direction)

            
            self.update_clip_data(
                clip.data,
                only_basic_props=False,
                ignore_reader=True,
                transaction_id=transaction_id,
            )
            get_app().updates.apply_last_action_to_history(original_clip_data)

        
        if clips_with_waveforms:
            self.Show_Waveform_Triggered(clips_with_waveforms, transaction_id=transaction_id)

    def Repeat_Triggered(self, pattern, direction, passes, clip_ids, delay_frames=0, ramp=0.0):
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        clips_with_waveforms = []
        transaction_id = self.get_uuid()
        for clip_id in clip_ids:
            clip = Clip.get(id=clip_id)
            if not clip:
                continue
            if clip.data.get("ui", {}).get("audio_data", []):
                clips_with_waveforms.append(clip.id)
            apply_repeat(clip, pattern, direction, passes, delay_frames, ramp, fps_float)
            self.update_clip_data(
                clip.data,
                only_basic_props=False,
                ignore_reader=True,
                transaction_id=transaction_id,
            )
        self._extend_timeline_to_fit_items()
        if clips_with_waveforms:
            self.Show_Waveform_Triggered(clips_with_waveforms, transaction_id=transaction_id)

    def Repeat_Custom(self, clip_ids):
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        dlg = RepeatDialog(self)
        if dlg.exec_():
            pattern, direction, passes, delay_frames, ramp = dlg.get_values(fps_float)
            self.Repeat_Triggered(pattern, direction, passes, clip_ids, delay_frames, ramp)


    @pyqtSlot(str, float, float)
    def RetimeClip(self, clip_id, new_end, new_position):
        """Public slot to retime a clip from the timeline UI (Timing Mode)."""
        clip = Clip.get(id=clip_id)
        if not clip:
            return

        audio_data = clip.data.get("ui", {}).get("audio_data")
        has_waveform = audio_data not in (None, [])

        original_clip_data = json.loads(json.dumps(clip.data))
        if not retime_clip(clip, new_end, new_position, direction=1):
            return

        
        ui_data = clip.data.get("ui")
        if isinstance(ui_data, dict) and "audio_data" in ui_data:
            ui_data.pop("audio_data", None)
            ui_data.pop("audio_data_rms", None)
            ui_data.pop("audio_data_rate", None)
            ui_data.pop("audio_data_format", None)

        tid = str(uuid.uuid4())
        self.update_clip_data(
            clip.data,
            only_basic_props=False,
            ignore_reader=True,
            transaction_id=tid,
        )
        get_app().updates.apply_last_action_to_history(original_clip_data)

        if has_waveform:
            self.Show_Waveform_Triggered([clip.id], transaction_id=tid)

    def show_all_clips(self, clip, stretch=False, clip_ids=None):
        """ Show all clips at the same time (arranged col by col, row by row)  """
        from math import sqrt

        
        
        available_clips = []
        if clip_ids:
            selected_ids = {str(clip_id) for clip_id in clip_ids}
            for c in Clip.filter():
                clip_id = str(getattr(c, "id", c.data.get("id")))
                if clip_id in selected_ids:
                    available_clips.append(c)
        else:
            start_position = float(clip.data["position"])
            for c in Clip.filter():
                if (float(c.data["position"]) >= (start_position - 0.5)
                   and float(c.data["position"]) <= (start_position + 0.5)):
                    
                    available_clips.append(c)

        if not available_clips:
            return

        
        number_of_clips = len(available_clips)
        number_of_rows = int(sqrt(number_of_clips))
        max_clips_on_row = float(number_of_clips) / float(number_of_rows)

        
        if max_clips_on_row > float(int(max_clips_on_row)):
            max_clips_on_row = int(max_clips_on_row + 1)
        else:
            max_clips_on_row = int(max_clips_on_row)

        
        height = 1.0 / float(number_of_rows)
        width = 1.0 / float(max_clips_on_row)

        clip_index = 0

        
        for row in range(0, number_of_rows):

            
            for col in range(0, max_clips_on_row):
                if clip_index >= number_of_clips:
                    continue

                
                X = float(col) * width
                Y = float(row) * height

                
                selected_clip = available_clips[clip_index]
                selected_clip.data["gravity"] = smartedit.GRAVITY_TOP_LEFT

                if stretch:
                    selected_clip.data["scale"] = smartedit.SCALE_STRETCH
                else:
                    selected_clip.data["scale"] = smartedit.SCALE_FIT

                if stretch:
                    scale_x = width
                    scale_y = height
                else:
                    scale_x = scale_y = min(width, height)

                
                w = smartedit.Point(1, scale_x, smartedit.BEZIER)
                w_object = json.loads(w.Json())
                selected_clip.data["scale_x"] = {"Points": [w_object]}
                h = smartedit.Point(1, scale_y, smartedit.BEZIER)
                h_object = json.loads(h.Json())
                selected_clip.data["scale_y"] = {"Points": [h_object]}
                x_point = smartedit.Point(1, X, smartedit.BEZIER)
                x_object = json.loads(x_point.Json())
                selected_clip.data["location_x"] = {"Points": [x_object]}
                y_point = smartedit.Point(1, Y, smartedit.BEZIER)
                y_object = json.loads(y_point.Json())
                selected_clip.data["location_y"] = {"Points": [y_object]}

                log.info('Updating clip id: %s' % selected_clip.data["id"])
                log.info('width: %s, height: %s' % (width, height))

                
                clip_index += 1

                
                self.update_clip_data(selected_clip.data, only_basic_props=False, ignore_reader=True)

    def Reverse_Transition_Triggered(self, tran_ids):
        """Callback for reversing a transition"""
        log.info("Reverse_Transition_Triggered")

        
        for tran_id in tran_ids:

            
            tran = Transition.get(id=tran_id)
            if not tran:
                
                continue

            
            tran_data_copy = json.loads(json.dumps(tran.data))
            fps = get_app().project.get("fps")
            fps_float = float(fps["num"]) / float(fps["den"])
            duration = tran.data.get("end", 0.0) - tran.data.get("start", 0.0)
            total_frames = round(duration * fps_float)

            for prop in ("brightness", "contrast"):
                if prop in tran_data_copy:
                    self._reverse_keyframes(tran_data_copy[prop], total_frames)

            
            tran.data = tran_data_copy
            self.update_transition_data(tran.data, only_basic_props=False)

    @pyqtSlot(str)
    def ShowTransitionMenu(self, tran_id=None):
        log.info('ShowTransitionMenu: %s' % tran_id)
        self._context_menu_paste_data = None

        
        _ = get_app()._tr

        
        tran = Transition.get(id=tran_id)
        if not tran:
            
            return

        
        tran_ids = self.window.selected_transitions
        clip_ids = self.window.selected_clips

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])

        
        playhead_position = float(self.window.preview_thread.current_frame) / fps_float

        
        copied_object = ClipboardManager.from_mime(get_app().clipboard().mimeData())
        has_clipboard = False
        if copied_object and isinstance(copied_object, Transition):
            has_clipboard = True

        menu = StyledContextMenu(parent=self)

        
        if len(tran_ids) + len(clip_ids) > 1:
            
            Copy_All = menu.addAction(_("Copy"))
            Copy_All.setShortcuts(self.window.getShortcutByName("copyAll"))
            Copy_All.triggered.connect(self.window.copyAll)
            
            Cut_All = menu.addAction(_("Cut"))
            Cut_All.setShortcuts(self.window.getShortcutByName("cutAll"))
            Cut_All.triggered.connect(self.window.cutAll)
        else:
            
            Copy_Menu = StyledContextMenu(title=_("Copy"), parent=self)
            Copy_Tran = Copy_Menu.addAction(_("Transition"))
            Copy_Tran.setShortcuts(self.window.getShortcutByName("copyAll"))
            Copy_Tran.triggered.connect(partial(self.Copy_Triggered, MenuCopy.TRANSITION, [], [tran_id], []))

            Keyframe_Menu = StyledContextMenu(title=_("Keyframes"), parent=self)
            Copy_Keyframes_All = Keyframe_Menu.addAction(_("All"))
            Copy_Keyframes_All.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_ALL, [], [tran_id], []))
            Keyframe_Menu.addSeparator()
            Copy_Keyframes_Brightness = Keyframe_Menu.addAction(_("Brightness"))
            Copy_Keyframes_Brightness.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_BRIGHTNESS, [], [tran_id], []))
            Copy_Keyframes_Scale = Keyframe_Menu.addAction(_("Contrast"))
            Copy_Keyframes_Scale.triggered.connect(partial(
                self.Copy_Triggered, MenuCopy.KEYFRAMES_CONTRAST, [], [tran_id], []))

            
            Copy_Menu.addMenu(Keyframe_Menu)
            menu.addMenu(Copy_Menu)

        
        Cut_All = menu.addAction(_("Cut"))
        Cut_All.setShortcuts(self.window.getShortcutByName("cutAll"))
        Cut_All.triggered.connect(self.window.cutAll)

        
        if has_clipboard:
            
            Paste_Tran = menu.addAction(_("Paste"))
            Paste_Tran.triggered.connect(partial(self.Paste_Triggered, MenuCopy.PASTE, [], tran_ids))

        menu.addSeparator()

        
        if len(clip_ids) > 1:
            Alignment_Menu = StyledContextMenu(title=_("Align"), parent=self)
            Align_Left = Alignment_Menu.addAction(_("Left"))
            Align_Left.triggered.connect(partial(self.Align_Triggered, MenuAlign.LEFT, clip_ids, tran_ids))
            Align_Right = Alignment_Menu.addAction(_("Right"))
            Align_Right.triggered.connect(partial(self.Align_Triggered, MenuAlign.RIGHT, clip_ids, tran_ids))

            
            menu.addMenu(Alignment_Menu)

        
        if tran:
            start_of_tran = float(tran.data["start"])
            end_of_tran = float(tran.data["end"])
            position_of_tran = float(tran.data["position"])
            if (playhead_position >= position_of_tran
               and playhead_position <= (position_of_tran + (end_of_tran - start_of_tran))):
                
                Slice_Menu = StyledContextMenu(title=_("Slice"), parent=self)
                Slice_Keep_Both = Slice_Menu.addAction(_("Keep Both Sides"))
                Slice_Keep_Both.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_BOTH, clip_ids, tran_ids, playhead_position))
                Slice_Keep_Left = Slice_Menu.addAction(_("Keep Left Side"))
                Slice_Keep_Left.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_LEFT, clip_ids, tran_ids, playhead_position))
                Slice_Keep_Right = Slice_Menu.addAction(_("Keep Right Side"))
                Slice_Keep_Right.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_RIGHT, clip_ids, tran_ids, playhead_position))

                
                Slice_Menu.addSeparator()
                Slice_Keep_Left = Slice_Menu.addAction(_("Keep Left Side (Ripple)"))
                Slice_Keep_Left.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_LEFT, clip_ids, tran_ids, playhead_position, True))
                Slice_Keep_Right = Slice_Menu.addAction(_("Keep Right Side (Ripple)"))
                Slice_Keep_Right.triggered.connect(partial(
                    self.Slice_Triggered, MenuSlice.KEEP_RIGHT, clip_ids, tran_ids, playhead_position, True))

                menu.addMenu(Slice_Menu)

        
        Reverse_Transition = menu.addAction(_("Reverse Transition"))
        Reverse_Transition.triggered.connect(partial(self.Reverse_Transition_Triggered, tran_ids))

        
        menu.addSeparator()
        menu.addAction(self.window.actionProperties)

        
        menu.addSeparator()
        menu.addAction(self.window.actionRemoveTransition)

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot(str)
    def ShowTrackMenu(self, layer_id=None):
        log.info('ShowTrackMenu: %s', layer_id)
        self._context_menu_paste_data = None

        
        _ = get_app()._tr

        
        track = Track.get(id=layer_id)
        if not track:
            return

        if layer_id not in self.window.selected_tracks:
            self.window.selected_tracks = [layer_id]

        
        found_gap = False
        first_gap_start = 0.0
        layer_number = track.data.get("number", 0)

        
        clips_and_transitions = sorted(
            Clip.filter(layer=layer_number) + Transition.filter(layer=layer_number),
            key=lambda c: c.data.get("position", 0.0)
        )

        
        last_end = 0.0

        
        for clip in clips_and_transitions:
            left_edge = clip.data.get("position", 0.0)
            right_edge = left_edge + (clip.data.get("end", 0.0) - clip.data.get("start", 0.0))

            
            if left_edge > last_end:
                found_gap = True
                first_gap_start = last_end
                break  

            
            last_end = max(last_end, right_edge)

        
        locked = track.data.get("lock", False)

        menu = StyledContextMenu(parent=self)
        menu.addAction(self.window.actionAddTrackAbove)
        menu.addAction(self.window.actionAddTrackBelow)
        menu.addAction(self.window.actionRenameTrack)
        if found_gap:
            
            log.info(f"Found gap at {first_gap_start}")
            menu.addAction(self.window.actionRemoveAllGaps)
            try:
                
                self.window.actionRemoveAllGaps.triggered.disconnect()
            except TypeError:
                pass  
            self.window.actionRemoveAllGaps.triggered.connect(
                partial(self.RemoveAllGaps_Triggered, first_gap_start, int(layer_number))
            )
        if locked:
            menu.addAction(self.window.actionUnlockTrack)
            self.window.actionRemoveTrack.setEnabled(False)
        else:
            menu.addAction(self.window.actionLockTrack)
            self.window.actionRemoveTrack.setEnabled(True)
        menu.addSeparator()
        menu.addAction(self.window.actionRemoveTrack)

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot(str)
    def ShowMarkerMenu(self, marker_id=None):
        log.info('ShowMarkerMenu: %s' % marker_id)
        self._context_menu_paste_data = None

        if marker_id not in self.window.selected_markers:
            self.window.selected_markers = [marker_id]

        menu = StyledContextMenu(parent=self)
        menu.addAction(self.window.actionRemoveMarker)

        
        self.context_menu_cursor_position = QCursor.pos()
        return menu.show_at(self.context_menu_cursor_position)

    @pyqtSlot()
    def EnableCacheThread(self):
        
        smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = True

    @pyqtSlot()
    def EnableCacheThreadNoRefresh(self):
        """Enable playback caching without forcing an extra refresh seek."""
        smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = True

    @pyqtSlot()
    def DisableCacheThread(self):
        
        smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = False

    @pyqtSlot()
    def TrimPreviewMode(self):
        self.window.TrimPreviewMode.emit()

    @pyqtSlot()
    def TimelinePreviewMode(self):
        self.window.TimelinePreviewMode.emit()

    @pyqtSlot()
    def BeginTrimRefresh(self):
        setattr(self.window, "_trim_refresh_pending", True)

    @pyqtSlot(str, str)
    def RefreshTrimmedTimelineItem(self, item_json, edge):
        try:
            item_data = json.loads(item_json) if not isinstance(item_json, dict) else item_json
        except Exception:
            log.debug("Failed to parse trim JSON data", exc_info=True)
            return

        setattr(self.window, "_trim_refresh_pending", True)
        if ViewClass == TimelineWidget:
            item_id = item_data.get("id")
            self._pending_trim_refresh = {
                "id": item_id,
                "edge": edge,
                "data": item_data,
            }
            QTimer.singleShot(0, self._apply_pending_trim_refresh)
            return

        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"]) if fps else 0.0
        if fps_float <= 0.0:
            return

        position = float(item_data.get("position", 0.0) or 0.0)
        start = float(item_data.get("start", 0.0) or 0.0)
        end = float(item_data.get("end", start) or start)
        duration = max(0.0, end - start)
        frame_duration = 1.0 / fps_float

        if edge == "left":
            target_seconds = position
        else:
            target_seconds = position + max(0.0, duration - frame_duration)

        target_frame = max(1, int(round(target_seconds * fps_float)) + 1)
        self.window.LoadTimelineAndSeekSignal.emit(target_frame)
        QTimer.singleShot(0, lambda: setattr(self.window, "_trim_refresh_pending", False))

    def _action_contains_item_id(self, action, item_id):
        if not action or not item_id:
            return False
        for part in action.key or []:
            if isinstance(part, dict) and part.get("id") == item_id:
                return True
        values = getattr(action, "values", None)
        if isinstance(values, dict) and values.get("id") == item_id:
            return True
        return False

    def _apply_pending_trim_refresh(self):
        pending = self._pending_trim_refresh
        if not pending:
            return
        self._pending_trim_refresh = None
        item_data = pending.get("data") or {}
        edge = pending.get("edge")

        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"]) if fps else 0.0
        if fps_float <= 0.0:
            return

        position = float(item_data.get("position", 0.0) or 0.0)
        start = float(item_data.get("start", 0.0) or 0.0)
        end = float(item_data.get("end", start) or start)
        duration = max(0.0, end - start)
        frame_duration = 1.0 / fps_float

        if edge == "left":
            target_seconds = position
        else:
            target_seconds = position + max(0.0, duration - frame_duration)

        target_frame = max(1, int(round(target_seconds * fps_float)) + 1)
        self.window.LoadTimelineAndSeekSignal.emit(target_frame)
        QTimer.singleShot(0, lambda: setattr(self.window, "_trim_refresh_pending", False))

    @pyqtSlot(str, int)
    def PreviewClipFrame(self, clip_id, frame_number):

        
        clip = Clip.get(id=clip_id)
        if not clip:
            
            return

        reader = clip.data.get("reader", {}) if isinstance(clip.data, dict) else {}
        preview_path = None

        file_id = clip.data.get("file_id") if isinstance(clip.data, dict) else None
        if file_id:
            file_obj = File.get(id=file_id)
            if file_obj:
                preview_path = file_obj.absolute_path()

        if not preview_path:
            preview_path = absolute_media_path(reader.get("path"))

        if not preview_path:
            return

        
        frame_number = max(frame_number, 1)

        
        mapped_frame = frame_number
        timeline_sync = getattr(self.window, "timeline_sync", None)
        timeline = getattr(timeline_sync, "timeline", None)
        if timeline:
            try:
                clip_instance = timeline.GetClip(clip_id)
            except Exception as exc:
                clip_instance = None
                log.debug("Unable to fetch clip %s for preview: %s", clip_id, exc, exc_info=True)
            if clip_instance and getattr(clip_instance, "time", None):
                try:
                    if clip_instance.time.GetCount() > 1:
                        mapped_value = clip_instance.time.GetValue(frame_number)
                        mapped_frame = int(round(float(mapped_value)))
                except (TypeError, ValueError):
                    pass
                except Exception as exc:
                    log.debug("Failed to map time curve for clip %s: %s", clip_id, exc, exc_info=True)

        frame_number = max(mapped_frame, 1)

        
        self.window.LoadFileSignal.emit(preview_path)
        self.window.SpeedSignal.emit(0)

        
        self.window.SeekSignal.emit(frame_number, True)

    @pyqtSlot(str, int)
    def PreviewTransitionFrame(self, transition_id, frame_number):
        """Preview a specific source frame from a transition mask."""

        transition = Transition.get(id=transition_id)
        if not transition:
            return

        transition_data = transition.data if isinstance(transition.data, dict) else {}
        reader = self._transition_mask_reader(transition_data)
        preview_path = absolute_media_path(reader.get("path")) if isinstance(reader, dict) else None
        if not preview_path:
            return

        frame_number = max(int(frame_number or 1), 1)

        
        
        self.window.LoadFilePreviewSignal.emit(preview_path, True)
        self.window.SpeedSignal.emit(0)

        
        self.window.SeekSignal.emit(frame_number, True)

    @pyqtSlot(int)
    def SeekToKeyframe(self, frame_number):
        """Seek to a specific frame when a keyframe point is clicked"""

        
        self.window.SeekSignal.emit(frame_number, True)

        
        self.window.actionProperties.trigger()

    @pyqtSlot(int, bool)
    def PlayheadMoved(self, position_frames, start_preroll=True):
        
        self.window.LoadFileSignal.emit('')

        seek_state = (int(position_frames), bool(start_preroll))
        if self._last_playhead_seek_state == seek_state:
            return

        
        self.last_position_frames = position_frames
        self._last_playhead_seek_state = seek_state

        
        self.window.SeekSignal.emit(position_frames, bool(start_preroll))

    @pyqtSlot(int)
    def movePlayhead(self, position_frames):
        """ Move the playhead since the position has changed inside SmartEdit (probably due to the video player) """
        if ViewClass == TimelineWidget:
            TimelineWidget.update_playhead_pos(self, position_frames)
            return
        
        self.run_js(JS_SCOPE_SELECTOR + ".movePlayheadToFrame(%s);" % (str(position_frames)))

    @pyqtSlot()
    def centerOnPlayhead(self):
        """ Center the timeline on the current playhead position """
        if ViewClass == TimelineWidget:
            TimelineWidget.centerOnPlayhead(self)
            return
        
        self.run_js(JS_SCOPE_SELECTOR + '.centerOnPlayhead();')

    @pyqtSlot(int)
    def SetSnappingMode(self, enable_snapping):
        """ Enable / Disable snapping mode """
        
        if ViewClass == TimelineWidget:
            TimelineWidget.setSnappingMode(self, enable_snapping)
        else:
            self.run_js(JS_SCOPE_SELECTOR + ".setSnappingMode(%s);" % int(enable_snapping))

    @pyqtSlot(int)
    def SetRazorMode(self, enable_razor):
        """ Enable / Disable razor mode """
        
        if ViewClass == TimelineWidget:
            TimelineWidget.setRazorMode(self, enable_razor)
        else:
            self.run_js(JS_SCOPE_SELECTOR + ".setRazorMode(%s);" % int(enable_razor))

    @pyqtSlot(int)
    def SetTimingMode(self, enable_timing):
        """ Enable / Disable timing mode """
        
        if ViewClass == TimelineWidget:
            TimelineWidget.setTimingMode(self, enable_timing)
        else:
            self.run_js(JS_SCOPE_SELECTOR + ".setTimingMode(%s);" % int(enable_timing))

    @pyqtSlot(str)
    def SetPropertyFilter(self, property):
        """ Filter a specific property name """
        self.run_js(JS_SCOPE_SELECTOR + ".setPropertyFilter('%s');" % property)

    @pyqtSlot(int)
    def SetPlayheadFollow(self, enable_follow):
        """ Enable / Disable playhead follow on seek """
        self.run_js(JS_SCOPE_SELECTOR + ".setFollow({});".format(int(enable_follow)))

    @pyqtSlot(str, str, bool)
    def addSelection(self, item_id, item_type, clear_existing=False):
        """ Add the selected item to the current selection """
        self.window.SelectionAdded.emit(item_id, item_type, clear_existing)
        if item_id and item_type == "effect":
            
            self.window.actionProperties.trigger()

    def addRippleSelection(self, item_id, item_type):
        if ViewClass == TimelineWidget:
            TimelineWidget.selectRipple(self, item_id, item_type)
        elif item_type == "clip":
            self.run_js(JS_SCOPE_SELECTOR + ".selectClipRipple('{}', false, null);".format(item_id))
        elif item_type == "transition":
            self.run_js(JS_SCOPE_SELECTOR + ".selectTransitionRipple('{}', false, null);".format(item_id))

    def AddSelectionJS(self, item_id, item_type, clear_existing=False):
        """Invoke JavaScript selection routine"""
        if ViewClass == TimelineWidget:
            if clear_existing:
                TimelineWidget.clear_all_selections(self)
                clear_existing = False
            self.addSelection(str(item_id), item_type, clear_existing)
            return

        clear_js = 'true' if clear_existing else 'false'
        if item_type == "clip":
            self.run_js(JS_SCOPE_SELECTOR + ".selectClip('{}', {}, null);".format(item_id, clear_js))
        elif item_type == "transition":
            self.run_js(JS_SCOPE_SELECTOR + ".selectTransition('{}', {}, null);".format(item_id, clear_js))
        elif item_type == "effect":
            self.run_js(JS_SCOPE_SELECTOR + ".selectEffect('{}', {}, null);".format(item_id, clear_js))

    @pyqtSlot(str, str)
    def removeSelection(self, item_id, item_type):
        """ Remove the selected clip from the selection """
        self.window.SelectionRemoved.emit(item_id, item_type)

    @pyqtSlot(str, str)
    def qt_log(self, level="INFO", message=None):
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "FATAL": logging.FATAL,
            }
        if isinstance(level, str):
            level = levels.get(level, logging.INFO)
        self.log_fn(level, message)

    @pyqtSlot()
    def zoomIn(self):
        get_app().window.sliderZoomWidget.zoomIn()

    @pyqtSlot()
    def zoomOut(self):
        get_app().window.sliderZoomWidget.zoomOut()

    def update_scroll(self, newScroll):
        """Force a scroll event on the timeline (i.e. the zoom slider is moving, so we need to scroll the timeline)"""
        
        self.run_js(JS_SCOPE_SELECTOR + ".setScroll(" + str(newScroll) + ");")

    
    def update_zoom(self, newScale):
        if ViewClass == TimelineWidget:
            TimelineWidget.setZoomFactor(self, newScale, emit=False)
        else:
            _ = get_app()._tr

            
            cursor_y = self.mapFromGlobal(self.cursor().pos()).y()
            if cursor_y >= 0:
                cursor_x = self.mapFromGlobal(self.cursor().pos()).x()
            else:
                cursor_x = 0

            
            self.run_js(JS_SCOPE_SELECTOR + ".setScale(" + str(newScale) + "," + str(cursor_x) + ");")

            
            self.redraw_audio_timer.start()

        
        
        current_scale = round(float(get_app().project.get("scale") or 15.0), 6)
        new_scale = round(float(newScale), 6)

        
        if abs(new_scale - current_scale) > 1e-6:
            get_app().updates.ignore_history = True
            get_app().updates.update(["scale"], new_scale)
            get_app().updates.ignore_history = False

    def _mime_text_payload(self, mime):
        """Return text payload from a mime object, if available."""
        try:
            text = mime.text()
        except Exception:
            text = ""
        if text:
            return text
        for fmt in ("text/plain", "application/json"):
            try:
                raw = mime.data(fmt)
            except Exception:
                raw = None
            if not raw:
                continue
            try:
                return bytes(raw).decode("utf-8", "ignore")
            except Exception:
                try:
                    return raw.data().decode("utf-8", "ignore")
                except Exception:
                    continue
        return ""

    def _mime_json_list(self, mime):
        """Parse a JSON list from mime text, if present."""
        payload = self._mime_text_payload(mime)
        if not payload:
            return []
        try:
            data_list = json.loads(payload)
        except Exception:
            return []
        if not isinstance(data_list, list):
            data_list = [data_list]
        return data_list

    def _parse_js_position_result(self, result):
        """Normalize JS position results into a dict."""
        if isinstance(result, dict):
            return result
        if result is None:
            return None
        if isinstance(result, (bytes, bytearray)):
            try:
                result = result.decode("utf-8", "ignore")
            except Exception:
                return None
        if isinstance(result, str):
            if not result:
                return None
            try:
                parsed = json.loads(result)
            except Exception:
                return None
            return parsed if isinstance(parsed, dict) else None
        return None

    def _run_js_position(self, x, y, callback):
        """Run getJavaScriptPosition and normalize its result."""
        code = (
            "(function(){"
            "try{var r="
            + JS_SCOPE_SELECTOR
            + ".getJavaScriptPosition("
            + str(x)
            + ","
            + str(y)
            + ");return JSON.stringify(r);}catch(e){return JSON.stringify({error:String(e)});}"
            "})()"
        )

        def _wrapped(result):
            parsed = self._parse_js_position_result(result)
            if parsed is None:
                log.warning("Timeline js_position: empty result (%s)", result)
            elif parsed.get("error"):
                log.warning("Timeline js_position error: %s", parsed.get("error"))
            callback(parsed)

        self.run_js(code, _wrapped)

    
    def dragEnterEvent(self, event):
        if ViewClass == TimelineWidget:
            TimelineWidget.dragEnterEvent(self, event)
            return
        
        get_app().setOverrideCursor(QCursor(Qt.WaitCursor))

        
        self.ClearAllSelections()
        get_app().processEvents()

        
        data_list = []
        initial_pos = _event_posf(event)

        
        fps_float = float(get_app().project.get("fps")["num"]) / float(get_app().project.get("fps")["den"])
        snap_to_grid = lambda t: round(t * fps_float) / fps_float

        
        if event.mimeData().html():
            self.item_type = event.mimeData().html()
            data_list = self._mime_json_list(event.mimeData())
        
        elif event.mimeData().hasUrls():
            self.item_type = "clip"
            urls = event.mimeData().urls()

            
            get_app().window.files_model.process_urls(urls, import_quietly=True, prevent_image_seq=True)

            
            for uri in urls:
                filepath = uri.toLocalFile()
                if not os.path.exists(filepath) or not os.path.isfile(filepath):
                    continue  

                
                for file in File.filter(path=filepath):
                    if file:
                        data_list.append(file.id)

        
        if not self.item_type:
            return

        self.new_item = True
        self.item_ids = []

        
        get_app().restoreOverrideCursor()

        
        def handle_js_position(pos, js_position_data):
            
            tid = self.get_uuid()
            get_app().updates.transaction_id = tid

            if not js_position_data:
                log.warning("Timeline dragEnter js_position: empty result")
                return
            js_position = snap_to_grid(js_position_data.get('position', 0.0))
            js_nearest_track = js_position_data.get('track', 0)
            if not js_nearest_track:
                try:
                    js_nearest_track = int(self.timeline_sync.timeline.GetTrackCount())
                except Exception:
                    js_nearest_track = 0

            pos.setX(js_position)

            
            for index, drag_id in enumerate(data_list):
                ignore_refresh = False if index == len(data_list) - 1 else True
                new_item = None

                
                if self.item_type == "clip":
                    
                    new_item = self.addClip(drag_id, pos, js_nearest_track, ignore_refresh, call_manual_move=False)

                
                elif self.item_type == "transition":
                    new_item = self.addTransition(drag_id, pos, js_nearest_track, ignore_refresh, call_manual_move=False)

                
                if new_item:
                    pos += QPointF(new_item["end"] - new_item["start"], 0)

            
            self.run_js(JS_SCOPE_SELECTOR + ".startManualMove('{}', '{}');".format(self.item_type, json.dumps(self.item_ids)))

        
        def _deferred_js_position():
            self._run_js_position(
                initial_pos.x(),
                initial_pos.y(),
                partial(handle_js_position, initial_pos),
            )
        QTimer.singleShot(0, _deferred_js_position)

        
        event.accept()

    
    def addClip(
        self,
        file_id,
        position,
        track,
        ignore_refresh=False,
        call_manual_move=True,
        auto_transition=False,
    ):
        
        file = File.get(id=file_id)
        if not file:
            log.warning("addClip: file_id not found: %s", file_id)
            return  

        
        filename = os.path.basename(file.data["path"])
        file_path = file.absolute_path()

        
        fps_float = float(get_app().project.get("fps")["num"]) / float(get_app().project.get("fps")["den"])
        snap_to_grid = lambda t: round(t * fps_float) / fps_float

        
        c = smartedit.Clip(file_path)

        
        new_clip = json.loads(c.Json())
        new_clip["file_id"] = file.id
        new_clip["title"] = file.data.get("name", filename)
        new_clip["reader"] = file.data

        
        if not new_clip.get("reader"):
            return  

        
        apply_file_caption_to_clip(new_clip, file)

        
        start_value = file.data.get("start", new_clip.get("start", 0.0))
        try:
            start_sec = float(start_value)
        except (TypeError, ValueError):
            start_sec = 0.0
        start_sec = snap_to_grid(start_sec)
        new_clip["start"] = start_sec

        duration_value = file.data.get("duration")
        if duration_value is None:
            duration_value = new_clip["reader"].get("duration")
        try:
            duration_sec = float(duration_value or 0.0)
        except (TypeError, ValueError):
            duration_sec = 0.0

        default_img_len = get_app().get_settings().get("default-image-length") or 10.0
        if is_single_image_media(new_clip["reader"]):
            duration_sec = float(default_img_len)

        end_override = file.data.get("end")
        if end_override is not None:
            try:
                end_sec = float(end_override)
            except (TypeError, ValueError):
                end_sec = start_sec
            end_sec = snap_to_grid(end_sec)
            duration_sec = max(0.0, end_sec - start_sec)
        else:
            if duration_sec <= 0.0:
                duration_sec = 1.0 / fps_float
            duration_frames = max(1, int(round(duration_sec * fps_float)))
            duration_sec = duration_frames / fps_float
            end_sec = start_sec + duration_sec

        if duration_sec <= 0.0:
            duration_sec = 1.0 / fps_float
            end_sec = start_sec + duration_sec

        new_clip["duration"] = duration_sec
        new_clip["end"] = end_sec

        
        new_clip["position"] = position.x()
        new_clip["layer"] = track
        if auto_transition:
            new_clip["_auto_transition"] = True

        
        self._ensure_layers_exist([track])
        self.update_clip_data(new_clip, only_basic_props=False, ignore_refresh=ignore_refresh)

        
        self.item_ids.append(new_clip.get('id'))

        
        reader = new_clip.get("reader", {}) if isinstance(new_clip.get("reader"), dict) else {}
        has_video = reader.get("has_video")
        has_video = True if has_video is None else bool(has_video)
        has_audio = reader.get("has_audio")
        has_audio = True if has_audio is None else bool(has_audio)
        clip_id = new_clip.get("id")
        if has_audio and not has_video and clip_id:
            self.Show_Waveform_Triggered([clip_id])

        
        if call_manual_move:
            self.run_js(JS_SCOPE_SELECTOR + ".startManualMove('{}', '{}');".format(self.item_type, json.dumps(self.item_ids)))
        return new_clip

    @pyqtSlot(list)
    def ScrollbarChanged(self, new_positions):
        """Timeline scrollbars changed"""
        get_app().window.TimelineScrolled.emit(new_positions)

    
    @pyqtSlot(float)
    def resizeTimeline(self, new_duration):
        """Resize the duration of the timeline"""
        log.debug(f"Changing timeline to length: {new_duration}")
        get_app().updates.update_untracked(["duration"], new_duration)
        get_app().window.TimelineResize.emit()

    def _get_transition_reader_json(self, file_path, create=True):
        """Return cached transition reader JSON, creating it when requested."""
        if not file_path:
            return None
        normalized_path = os.path.normpath(str(file_path))

        reader_cache = getattr(self, "_transition_reader_json_cache", None)
        if reader_cache is None:
            reader_cache = {}
            self._transition_reader_json_cache = reader_cache

        cache_key = os.path.abspath(normalized_path)
        reader_json = reader_cache.get(cache_key)
        if reader_json is None and create:
            reader_json = self._load_transition_reader_data(normalized_path)
            if isinstance(reader_json, dict):
                reader_cache[cache_key] = deepcopy(reader_json)
        return deepcopy(reader_json) if isinstance(reader_json, dict) else None

    
    def addTransition(
        self,
        file_path,
        position,
        track,
        ignore_refresh=False,
        call_manual_move=True,
        defer_reader=False,
    ):
        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])
        snap_to_grid = lambda t: round(t * fps_float) / fps_float
        duration = snap_to_grid(get_app().get_settings().get("default-transition-length"))
        file_path = os.path.normpath(str(file_path))

        
        reader_json = self._get_transition_reader_json(file_path, create=not defer_reader)
        if not defer_reader and not isinstance(reader_json, dict):
            log.warning("Unable to add transition, invalid reader path: %s", file_path)
            return None
        if not isinstance(reader_json, dict):
            reader_json = {"path": file_path}

        
        transition_data = {
            "id": get_app().project.generate_id(),
            "layer": track,
            "title": "Transition",
            "type": "Mask",
            "position": snap_to_grid(position.x()),
            "start": 0,
            "end": duration,
            "reader": deepcopy(reader_json),
            "replace_image": False
        }
        self._set_transition_mask_defaults(transition_data)

        
        self._auto_orient_transition_keyframes(transition_data)

        
        self._ensure_layers_exist([track])
        self.update_transition_data(transition_data, only_basic_props=False, ignore_refresh=ignore_refresh)

        
        if not isinstance(getattr(self, "item_ids", None), list):
            self.item_ids = []
        self.item_ids.append(transition_data.get('id'))

        
        if call_manual_move:
            self.run_js(JS_SCOPE_SELECTOR + ".startManualMove('{}','{}');".format(self.item_type, json.dumps(self.item_ids)))
        return transition_data

    def _load_transition_reader_data(self, file_path):
        """Build transition reader JSON, with a platform-safe fallback path."""
        if not file_path:
            return None
        if not os.path.exists(file_path):
            log.warning("Transition file does not exist: %s", file_path)
            return None

        try:
            transition_reader = smartedit.QtImageReader(file_path)
            return json.loads(transition_reader.Json())
        except Exception:
            log.debug("QtImageReader failed for transition: %s", file_path, exc_info=1)

        clip = None
        try:
            clip = smartedit.Clip(file_path)
            reader = clip.Reader()
            if reader:
                return json.loads(reader.Json())
        except Exception:
            log.debug("Clip reader fallback failed for transition: %s", file_path, exc_info=1)
        finally:
            if clip:
                try:
                    clip.Close()
                except Exception:
                    pass

        return None

    
    def addEffect(self, effect_names, event_position):
        if ViewClass == TimelineWidget:
            self._add_effect_qwidget(effect_names, event_position)
            return

        
        def callback(self, effect_names, callback_data):
            js_position = callback_data.get('position', 0.0)
            js_nearest_track = callback_data.get('track', 0)

            
            name = effect_names[0]

            
            possible_clips = Clip.filter(layer=js_nearest_track)
            for clip in possible_clips:
                if js_position == 0 or (
                    clip.data["position"]
                    <= js_position
                    <= clip.data["position"] + (clip.data["end"] - clip.data["start"])
                ):
                    log.info("Applying effect {} to clip ID {}".format(name, clip.id))
                    log.debug(clip)
                    original_clip_data = json.loads(json.dumps(clip.data))

                    
                    if name in effect_options:

                        
                        effect_params = effect_options.get(name)

                        
                        from windows.process_effect import ProcessEffect

                        try:
                            win = ProcessEffect(clip.id, name, effect_params)

                        except ModuleNotFoundError as e:
                            print("[ERROR]: " + str(e))
                            return

                        print("Effect %s" % name)
                        print("Effect options: %s" % effect_options)

                        
                        result = win.exec_()

                        if result == QDialog.Accepted:
                            log.info('Start processing')
                        else:
                            log.info('Cancel processing')
                            return

                        
                        effect = win.effect 

                        if effect is None:
                            break
                    else:
                        
                        effect = smartedit.EffectInfo().CreateEffect(name)

                        
                        effect.Id(get_app().project.generate_id())

                    effect_json = json.loads(effect.Json())

                    
                    clip.data["effects"].append(effect_json)

                    
                    self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
                    get_app().updates.apply_last_action_to_history(original_clip_data)

        
        self.run_js(JS_SCOPE_SELECTOR + ".getJavaScriptPosition({}, {});"
            .format(event_position.x(), event_position.y()), partial(callback, self, effect_names))

    def _add_effect_qwidget(self, effect_names, event_position):
        if not effect_names:
            return
        try:
            pos_seconds = float(event_position.x())
        except AttributeError:
            pos_seconds = float(event_position)
        track_num = 0
        try:
            track_num = int(event_position.y())
        except AttributeError:
            try:
                track_num = int(event_position)
            except (TypeError, ValueError):
                track_num = 0

        for clip in Clip.filter(layer=track_num):
            data = clip.data if isinstance(clip.data, dict) else {}
            clip_position = float(data.get("position", 0.0) or 0.0)
            clip_start = float(data.get("start", 0.0) or 0.0)
            clip_end = float(data.get("end", clip_start) or clip_start)
            duration = clip_end - clip_start
            if duration <= 0.0:
                continue
            clip_finish = clip_position + duration
            if pos_seconds == 0.0 or clip_position <= pos_seconds <= clip_finish:
                self._apply_effect_to_clip(clip, effect_names[0])
                break

    def _apply_effect_to_clip(self, clip, effect_name):
        if not effect_name:
            return
        log.info("Applying effect %s to clip ID %s", effect_name, clip.id)
        original_clip_data = json.loads(json.dumps(clip.data))
        if effect_name in effect_options:
            effect_params = effect_options.get(effect_name)
            from windows.process_effect import ProcessEffect
            try:
                win = ProcessEffect(clip.id, effect_name, effect_params)
            except ModuleNotFoundError as e:
                print("[ERROR]: " + str(e))
                return
            result = win.exec_()
            if result != QDialog.Accepted:
                log.info('Cancel processing')
                return
            effect = win.effect
            if effect is None:
                return
        else:
            effect = smartedit.EffectInfo().CreateEffect(effect_name)
            effect.Id(get_app().project.generate_id())

        effect_json = json.loads(effect.Json())
        if not isinstance(clip.data, dict):
            clip.data = {}
        effects = clip.data.get("effects")
        if not isinstance(effects, list):
            effects = list(effects) if effects else []
            clip.data["effects"] = effects
        effects.append(effect_json)
        self.update_clip_data(clip.data, only_basic_props=False, ignore_reader=True)
        get_app().updates.apply_last_action_to_history(original_clip_data)

    
    def dragMoveEvent(self, event):
        if ViewClass == TimelineWidget:
            TimelineWidget.dragMoveEvent(self, event)
            return
        
        event.accept()

        
        pos = _event_posf(event)

        
        if self.item_type in ["clip", "transition"]:
            self.run_js(JS_SCOPE_SELECTOR + ".moveItem({}, {});".format(pos.x(), pos.y()))

    
    def dropEvent(self, event):
        if ViewClass == TimelineWidget:
            TimelineWidget.dropEvent(self, event)
            return

        log.info("Dropping item on timeline - item_ids: %s, item_type: %s" % (self.item_ids, self.item_type))

        
        event.accept()

        def cleanup_drop():
            self.new_item = False
            self.item_type = None
            self.item_ids = []
            get_app().updates.transaction_id = None

        
        if self.item_type in ["clip", "transition"] and not self.item_ids:
            mime = event.mimeData()
            data_list = []
            data_list = self._mime_json_list(mime)
            if not data_list and mime.hasUrls():
                urls = mime.urls()
                get_app().window.files_model.process_urls(urls, import_quietly=True, prevent_image_seq=True)
                for uri in urls:
                    filepath = uri.toLocalFile()
                    if not os.path.exists(filepath) or not os.path.isfile(filepath):
                        continue
                    for file in File.filter(path=filepath):
                        if file:
                            data_list.append(file.id)
            if data_list:
                pos = _event_posf(event)

                def handle_js_position(pos, js_position_data):
                    tid = self.get_uuid()
                    get_app().updates.transaction_id = tid

                    fps_float = float(get_app().project.get("fps")["num"]) / float(get_app().project.get("fps")["den"])
                    snap_to_grid = lambda t: round(t * fps_float) / fps_float
                    if not js_position_data:
                        log.warning("Timeline drop fallback js_position: empty result")
                        cleanup_drop()
                        return
                    js_position = snap_to_grid(js_position_data.get('position', 0.0))
                    js_nearest_track = js_position_data.get('track', 0)
                    if not js_nearest_track:
                        try:
                            js_nearest_track = int(self.timeline_sync.timeline.GetTrackCount())
                        except Exception:
                            js_nearest_track = 0
                    pos.setX(js_position)

                    self.item_ids = []
                    for index, drag_id in enumerate(data_list):
                        ignore_refresh = False if index == len(data_list) - 1 else True
                        if self.item_type == "clip":
                            self.addClip(drag_id, pos, js_nearest_track, ignore_refresh, call_manual_move=False)
                        elif self.item_type == "transition":
                            self.addTransition(drag_id, pos, js_nearest_track, ignore_refresh, call_manual_move=False)

                    if self.item_ids:
                        self.run_js(
                            JS_SCOPE_SELECTOR + ".updateRecentItemJSON('{}', '{}', '{}');"
                            .format(self.item_type, json.dumps(self.item_ids), get_app().updates.transaction_id)
                        )
                    cleanup_drop()

                def _deferred_drop_position():
                    self._run_js_position(
                        pos.x(),
                        pos.y(),
                        partial(handle_js_position, pos),
                    )
                QTimer.singleShot(0, _deferred_drop_position)
                return

        if self.item_type == "effect":
            pos = _event_posf(event)
            data = self._mime_json_list(event.mimeData())
            self.addEffect(data, pos)

        elif self.item_type in ["clip", "transition"] and self.item_ids:
            
            self.run_js(JS_SCOPE_SELECTOR + ".updateRecentItemJSON('{}', '{}', '{}');"
                        .format(self.item_type, json.dumps(self.item_ids), get_app().updates.transaction_id))
            
            files_model = getattr(self.window, "files_model", None)
            if files_model:
                files_model.selection_model.clearSelection()
                files_model.list_selection_model.clearSelection()
            self.setFocus(Qt.OtherFocusReason)

        
        cleanup_drop()

    def dragLeaveEvent(self, event):
        """A drag is in-progress and the user moves mouse outside of timeline"""
        if ViewClass == TimelineWidget:
            TimelineWidget.dragLeaveEvent(self, event)
            return

        log.debug('dragLeaveEvent - Undo drop')

        
        event.accept()

        
        for item_id in self.item_ids:
            self.window.removeSelection(item_id, self.item_type)

            if self.item_type == "clip":
                
                clips = Clip.filter(id=item_id)
                for c in clips:
                    c.delete()

            elif self.item_type == "transition":
                
                transitions = Transition.filter(id=item_id)
                for t in transitions:
                    t.delete()

        
        self.new_item = False
        self.item_type = None
        self.item_ids = []

    def set_audio_recording_previews(self, previews):
        """Draw transient recording clips without committing project data."""
        preview_clips = []
        for preview in previews or []:
            if not isinstance(preview, dict):
                continue
            try:
                duration = max(0.05, float(preview.get("duration") or 0.0))
            except (TypeError, ValueError):
                duration = 0.05
            source_type = str(preview.get("source_type") or "recording")
            preview_id = str(preview.get("id") or "recording-preview-%s" % source_type)
            file_id = str(preview.get("file_id") or "")
            has_audio = source_type == "mic"
            has_video = source_type in ("screen", "webcam")
            try:
                fps_value = float(preview.get("fps") or getattr(self, "fps_float", 30.0) or 30.0)
            except (TypeError, ValueError):
                fps_value = 30.0
            fps_value = max(1.0, fps_value)
            video_length = max(1, int(round(duration * fps_value)))
            reader = {
                "has_audio": has_audio,
                "has_video": has_video,
                "media_type": "audio" if has_audio and not has_video else "video",
                "path": "",
                "duration": duration,
                "start": 0.0,
                "end": duration,
                "video_length": video_length,
                "fps": {"num": int(round(fps_value)), "den": 1},
            }
            if file_id:
                reader["id"] = file_id
            if has_video:
                try:
                    reader["width"] = int(preview.get("width") or 1280)
                    reader["height"] = int(preview.get("height") or 720)
                except (TypeError, ValueError):
                    reader["width"] = 1280
                    reader["height"] = 720

            preview_clip = Clip()
            preview_clip.id = preview_id
            try:
                position = max(0.0, float(preview.get("position") or 0.0))
            except (TypeError, ValueError):
                position = 0.0
            try:
                track = int(preview.get("track") or 1)
            except (TypeError, ValueError):
                track = 1
            preview_clip.data = {
                "id": preview_clip.id,
                "file_id": file_id,
                "title": preview.get("title") or get_app()._tr("Recording"),
                "position": position,
                "layer": track,
                "start": 0.0,
                "end": duration,
                "duration": duration,
                "reader": reader,
            }
            if has_audio:
                audio_data = list(preview.get("audio_data") or [])
                audio_rms = list(preview.get(WAVEFORM_RMS_KEY) or [])
                preview_clip.data["ui"] = {
                    "audio_data": audio_data,
                    WAVEFORM_RMS_KEY: audio_rms,
                    WAVEFORM_RATE_KEY: int(preview.get(WAVEFORM_RATE_KEY) or 20),
                    WAVEFORM_FORMAT_KEY: ABSOLUTE_WAVEFORM_FORMAT,
                    "waveform_token": "%s:%s" % (len(audio_data), len(audio_rms)),
                }
                preview_clip.data["waveform"] = True
            preview_clips.append(preview_clip)

        self._recording_preview_clips = preview_clips
        if hasattr(self, "geometry"):
            self.geometry.mark_dirty()
        
        
        self.update()

    def set_audio_recording_preview(self, preview_id, position, track, duration, audio_data):
        """Draw a transient recording clip without committing project data."""
        duration = max(0.05, float(duration or 0.0))
        self.set_audio_recording_previews([{
            "id": str(preview_id),
            "source_type": "mic",
            "position": max(0.0, float(position or 0.0)),
            "track": int(track or 1),
            "duration": duration,
            "audio_data": list(audio_data or []),
        }])

    def clear_audio_recording_preview(self):
        """Remove the transient recording clip from the timeline view."""
        if not getattr(self, "_recording_preview_clips", None):
            return
        self._recording_preview_clips = []
        if hasattr(self, "geometry"):
            self.geometry.mark_dirty()
        self.update()

    def redraw_audio_onTimeout(self):
        """Timer is ready to redraw audio (if any)"""
        log.debug('redraw_audio_onTimeout')

        
        self.run_js(JS_SCOPE_SELECTOR + ".reDrawAllAudioData();")

    def ClearAllSelections(self):
        """Clear all selections in JavaScript"""

        
        if ViewClass == TimelineWidget:
            TimelineWidget.clear_all_selections(self)
        else:
            self.run_js(JS_SCOPE_SELECTOR + ".clearAllSelections();")

    def SelectAll(self):
        """Select all clips and transitions in JavaScript"""

        
        if ViewClass == TimelineWidget:
            TimelineWidget.select_all_items(self)
        else:
            self.run_js(JS_SCOPE_SELECTOR + ".selectAll();")

    def render_cache_json(self):
        """Render the cached frames to the timeline (called every X seconds), and only if changed"""

        
        try:
            if self.window.timeline_sync and self.window.timeline_sync.timeline:
                cache_object = self.window.timeline_sync.timeline.GetCache()
                if not cache_object:
                    return
                
                cache_json = cache_object.Json()
                cache_dict = json.loads(cache_json)
                if not isinstance(cache_dict, dict):
                    return
                cache_version = cache_dict["version"]

                if self.cache_renderer_version == cache_version:
                    
                    return
                
                self.cache_renderer_version = cache_version
                if ViewClass == TimelineWidget:
                    self.update_playback_cache(cache_dict)
                else:
                    self.run_js(JS_SCOPE_SELECTOR + ".renderCache({});".format(cache_json))
        except Exception as ex:
            
            log.warning("Exception processing timeline cache: %s", ex)

    def handle_selection(self):
        
        self.run_js(JS_SCOPE_SELECTOR + ".refreshTimeline();")

    def __init__(self, window):
        if ViewClass == TimelineWidget:
            TimelineWidget.__init__(self)
        else:
            super().__init__()
        self.setObjectName("TimelineView")

        app = get_app()
        self.window = window
        self.setAcceptDrops(True)
        self.last_position_frames = None
        self._last_playhead_seek_state = None
        self.context_menu_cursor_position = None
        self._context_menu_paste_data = None
        self._pending_trim_refresh = None

        
        self.log_fn = log.log

        
        app.updates.add_listener(self)

        
        window.TimelineZoom.connect(self.update_zoom)
        window.TimelineScroll.connect(self.update_scroll)
        window.TimelineCenter.connect(self.centerOnPlayhead)
        window.SetKeyframeFilter.connect(self.SetPropertyFilter)

        
        window.ThumbnailUpdated.connect(self.Thumbnail_Updated)

        
        self.new_item = False
        self.item_type = None
        self.item_ids = []

        
        self.redraw_audio_timer = QTimer(self)
        self.redraw_audio_timer.setInterval(300)
        self.redraw_audio_timer.setSingleShot(True)
        self.redraw_audio_timer.timeout.connect(self.redraw_audio_onTimeout)

        
        self.cache_renderer_version = None
        self.cache_renderer = QTimer(self)
        self.cache_renderer.setInterval(300)
        self.cache_renderer.timeout.connect(self.render_cache_json)

        
        app.aboutToQuit.connect(self.redraw_audio_timer.stop)
        app.aboutToQuit.connect(self.cache_renderer.stop)
        app.lastWindowClosed.connect(self.deleteLater)

        
        QTimer.singleShot(1500, self.cache_renderer.start)

        
        self.clipAudioDataReady.connect(self.clipAudioDataReady_Triggered)
        self.fileAudioDataReady.connect(self.fileAudioDataReady_Triggered)

        
        self.window.SelectionChanged.connect(self.handle_selection)

        
        self.keyframe_drag_original = {}
        self.keyframe_transaction_id = None
        self.show_wait_spinner = True
