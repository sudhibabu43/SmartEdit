"""
 @file
 @brief This file listens to changes, and updates the primary project data
 @author Noah Figg <eggmunkee@hotmail.com>
 @author Jonathan Thomas <jonathan@smartedit.org>
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

import copy
import glob
import os
import random
import re
import shutil
import json

from classes import info
from classes.app import get_app
from classes.image_types import get_media_type
from classes.json_data import JsonDataStore
from classes.logger import log
from classes.thumbnail import MigrateThumbnailLayout
from classes.updates import UpdateInterface
from classes.assets import get_assets_path
from classes.path_utils import comparable_local_path, normalized_local_path
from windows.views.find_file import find_missing_file
from classes.convert_framerate import change_profile

from .keyframe_scaler import KeyframeScaler

import smartedit


class ProjectDataStore(JsonDataStore, UpdateInterface):
    """ This class allows advanced searching of data structure, implements changes interface """

    def __init__(self):
        JsonDataStore.__init__(self)
        self.data_type = "project data"  
        self.default_project_filepath = os.path.join(info.PATH, 'settings', '_default.project')

        
        self.current_filepath = None

        
        self.has_unsaved_changes = False

        
        self.new()

    def needs_save(self):
        """Returns if project data has unsaved changes"""
        return self.has_unsaved_changes

    def _effect_has_reader_source(self, effect):
        """Return True when an effect already has a modern reader payload."""
        if not isinstance(effect, dict):
            return False
        for key in ("mask_reader", "reader"):
            reader = effect.get(key)
            if not isinstance(reader, dict):
                continue
            if reader.get("path") or reader.get("id") or reader.get("has_single_image"):
                return True
        return False

    def _migrate_optimized_asset_paths(self):
        """Migrate legacy proxy asset folder paths from `proxies` to `optimized`."""
        if not self.current_filepath:
            return

        asset_path = get_assets_path(self.current_filepath)
        legacy_proxy_path = os.path.join(asset_path, "proxies")
        optimized_path = os.path.join(asset_path, "optimized")

        if os.path.isdir(legacy_proxy_path) and not os.path.exists(optimized_path):
            shutil.move(legacy_proxy_path, optimized_path)
            log.info("Migrated optimized assets folder to %s", optimized_path)

        legacy_prefix = os.path.abspath(legacy_proxy_path) + os.sep
        updated = 0
        for file_data in self._data.get("files", []):
            if not isinstance(file_data, dict):
                continue
            proxy_reader = file_data.get("proxy_reader")
            if not isinstance(proxy_reader, dict):
                continue
            proxy_path = str(proxy_reader.get("path") or "")
            abs_proxy_path = os.path.abspath(proxy_path) if proxy_path else ""
            if abs_proxy_path.startswith(legacy_prefix):
                relative_path = os.path.relpath(abs_proxy_path, os.path.abspath(legacy_proxy_path))
                proxy_reader["path"] = os.path.join(optimized_path, relative_path)
                updated += 1

        info.PROXY_PATH = optimized_path
        if updated:
            log.info("Updated %s optimized reader path(s) to use %s", updated, optimized_path)

    def _drop_obsolete_effect_resource(self, effect):
        """Remove legacy resource paths once a reader payload is available."""
        if not isinstance(effect, dict):
            return
        if "resource" in effect and self._effect_has_reader_source(effect):
            effect.pop("resource", None)

    def get(self, key):
        """Get copied value of a given key in data store"""

        
        if not key:
            log.warning("ProjectDataStore cannot get empty key.")
            return None
        if not isinstance(key, list):
            key = [key]

        
        obj = self._data

        
        for key_index in range(len(key)):
            key_part = key[key_index]

            
            if not isinstance(key_part, dict) and not isinstance(key_part, str):
                log.error("Unexpected key part type: {}".format(type(key_part).__name__))
                return None

            
            
            if isinstance(key_part, dict) and isinstance(obj, list):
                
                found = False
                
                for item_index in range(len(obj)):
                    item = obj[item_index]
                    
                    match = True
                    
                    for subkey in key_part:
                        
                        subkey = subkey.lower()
                        
                        if not (subkey in item and item[subkey] == key_part[subkey]):
                            match = False
                            break
                    
                    if match:
                        found = True
                        obj = item
                        break
                
                if not found:
                    return None

            
            if isinstance(key_part, str):
                key_part = key_part.lower()

                
                if not isinstance(obj, dict):
                    log.warn(
                        "Invalid project data structure. Trying to use a key on a non-dictionary object. Key part: {} (\"{}\").\nKey: {}".format(
                            (key_index), key_part, key))
                    return None

                
                if key_part not in obj:
                    log.warn(
                        'Key not found in project. Mismatch on key part %s ("%s").\nKey: %s',
                        key_index, key_part, key)
                    return None

                
                obj = obj[key_part]

        
        return obj

    def set(self, key, value):
        """Prevent calling JsonDataStore set() method. It is not allowed in ProjectDataStore, as changes come from UpdateManager."""
        raise RuntimeError("ProjectDataStore.set() is not allowed. Changes must route through UpdateManager.")

    def _set(self, key, values=None, add=False, remove=False):
        """ Store setting, but adding isn't allowed. All possible settings must be in default settings file. """

        log.debug(
            "_set key: %s, values: %s, add: %s, remove: %s",
            key, values, add, remove)
        parent, my_key = None, ""

        
        if not isinstance(key, list):
            log.warning("_set() key must be a list. key=%s", key)
            return None
        if not key:
            log.warning("Cannot set empty key (key=%s)", key)
            return None

        
        obj = self._data

        
        for key_index in range(len(key)):
            key_part = key[key_index]

            
            if not isinstance(key_part, dict) and not isinstance(key_part, str):
                log.error("Unexpected key part type: %s", type(key_part).__name__)
                return None

            
            
            if isinstance(key_part, dict) and isinstance(obj, list):
                
                found = False
                
                for item_index in range(len(obj)):
                    item = obj[item_index]
                    
                    match = True
                    
                    for subkey in key_part.keys():
                        
                        subkey = subkey.lower()
                        
                        if not (subkey in item and item[subkey] == key_part[subkey]):
                            match = False
                            break
                    
                    if match:
                        found = True
                        obj = item
                        my_key = item_index
                        break
                
                if not found:
                    return None


            
            if isinstance(key_part, str):
                key_part = key_part.lower()

                
                if not isinstance(obj, dict):
                    return None

                
                if key_part not in obj:
                    log.warn(
                        'Key not found in project. Mismatch on key part %s ("%s").\nKey: %s',
                        key_index, key_part, key)
                    return None

                
                obj = obj[key_part]
                my_key = key_part


            
            if key_index < (len(key) - 1) or key_index == 0:
                parent = obj


        
        ret = json.loads(json.dumps(obj))

        
        if remove:
            del parent[my_key]

        else:

            
            
            if add and isinstance(parent, list):
                parent.append(values)

            
            elif isinstance(values, dict):
                if (
                    isinstance(obj, dict)
                    and isinstance(obj.get("objects"), dict)
                    and isinstance(values.get("objects"), dict)
                ):
                    values = copy.deepcopy(values)
                    object_updates = values.pop("objects", {})
                    tracked_objects = obj.setdefault("objects", {})
                    for object_id, object_values in object_updates.items():
                        if (
                            isinstance(object_values, dict)
                            and isinstance(tracked_objects.get(object_id), dict)
                        ):
                            tracked_objects[object_id].update(object_values)
                        else:
                            tracked_objects[object_id] = object_values
                
                obj.update(values)

            else:

                
                self._data[my_key] = values

        
        return ret

    
    def new(self):
        """ Try to load default project settings file, will raise error on failure """
        import smartedit

        
        if os.path.exists(info.USER_DEFAULT_PROJECT):
            try:
                self._data = self.read_from_file(info.USER_DEFAULT_PROJECT)
            except (FileNotFoundError, PermissionError):
                log.warning(
                    "Unable to load user project defaults from %s",
                    info.USER_DEFAULT_PROJECT, exc_info=1)
            except Exception:
                raise
            else:
                log.info("Loaded user project defaults from %s",
                         info.USER_DEFAULT_PROJECT)
        else:
            
            self._data = self.read_from_file(self.default_project_filepath)

        self.current_filepath = None
        self.has_unsaved_changes = False

        
        info.reset_userdirs()

        
        s = get_app().get_settings()
        default_profile_desc = s.get("default-profile")

        
        profile = self.get_profile(profile_desc=default_profile_desc)
        if not profile:
            
            profile = self.get_profile(profile_desc="HD 720p 30 fps")

        
        if profile and default_profile_desc != profile.info.description:
            log.info(f"Updating default-profile from legacy `{default_profile_desc}` to `{profile.info.description}`.")
            s.set("default-profile", profile.info.description)

        
        self.apply_default_audio_settings()

        
        self._data["id"] = self.generate_id()

    def get_profile(self, profile_desc=None, profile_key=None):
        """Attempt to find a specific profile"""
        profile = None

        
        LEGACY_PROFILE_PATH = os.path.join(info.PROFILES_PATH, "legacy")
        legacy_profile = None
        if os.path.isdir(LEGACY_PROFILE_PATH):
            for legacy_filename in os.listdir(LEGACY_PROFILE_PATH):
                legacy_profile_path = os.path.join(LEGACY_PROFILE_PATH, legacy_filename)
                try:
                    
                    temp_profile = smartedit.Profile(legacy_profile_path)
                    if profile_desc == temp_profile.info.description:
                        legacy_profile = temp_profile
                        break
                except RuntimeError:
                    
                    pass

        
        profile_dirs = [info.USER_PROFILES_PATH, info.PROFILES_PATH]
        available_dirs = [f for f in profile_dirs if os.path.exists(f)]
        for profile_folder in available_dirs:
            for file in reversed(sorted(os.listdir(profile_folder))):
                profile_path = os.path.join(profile_folder, file)
                if os.path.isdir(profile_path):
                    continue
                try:
                    
                    temp_profile = smartedit.Profile(profile_path)

                    if profile_desc == temp_profile.info.description:
                        profile = self.apply_profile(temp_profile)
                        break
                    if legacy_profile and legacy_profile.Key() == temp_profile.Key():
                        
                        legacy_profile_match = temp_profile

                except RuntimeError as e:
                    
                    log.error("Failed to parse file '%s' as a profile: %s" % (profile_path, e))

        
        
        if not profile and legacy_profile_match:
            profile = self.apply_profile(legacy_profile_match)

        return profile

    def apply_profile(self, profile):
        """Apply a specific profile to the current project data"""
        log.info("Setting profile to %s" % profile.info.description)

        
        self._data["profile"] = profile.info.description
        self._data["width"] = profile.info.width
        self._data["height"] = profile.info.height
        self._data["fps"] = {"num": profile.info.fps.num, "den": profile.info.fps.den}
        self._data["display_ratio"] = {"num": profile.info.display_ratio.num, "den": profile.info.display_ratio.den}
        self._data["pixel_ratio"] = {"num": profile.info.pixel_ratio.num, "den": profile.info.pixel_ratio.den}

        
        change_profile(self._data["clips"] + self._data["effects"] + self._data["markers"], profile)

        return profile

    def load(self, file_path, clear_thumbnails=True):
        """ Load project from file """

        self.new()

        if file_path:
            log.info("Loading project file: %s", file_path)

            
            default_project = self._data

            try:
                
                project_data = self.read_from_file(file_path, path_mode="absolute")

                
                if not project_data.get("history"):
                    project_data["history"] = {"undo": [], "redo": []}

                
                get_app().window.actionClearWaveformData.setEnabled(False)
                for file in project_data["files"]:
                    if file.get("ui",{}).get("audio_data", []):
                        get_app().window.actionClearWaveformData.setEnabled(True)
                        break

            except Exception:
                try:
                    
                    project_data = self.read_legacy_project_file(file_path)

                except Exception:
                    
                    raise

            
            self._data = self.merge_settings(default_project, project_data)

            
            self.current_filepath = file_path

            
            if clear_thumbnails:
                info.THUMBNAIL_PATH = os.path.join(get_assets_path(self.current_filepath), "thumbnail")
                info.TITLE_PATH = os.path.join(get_assets_path(self.current_filepath), "title")
                info.BLENDER_PATH = os.path.join(get_assets_path(self.current_filepath), "blender")
                info.PROTOBUF_DATA_PATH = os.path.join(get_assets_path(self.current_filepath), "protobuf_data")
                info.CLIPBOARD_PATH = os.path.join(get_assets_path(self.current_filepath), "clipboard")
                info.COMFYUI_OUTPUT_PATH = os.path.join(get_assets_path(self.current_filepath), "comfyui-output")
                info.PROXY_PATH = os.path.join(get_assets_path(self.current_filepath), "optimized")
                migrated = MigrateThumbnailLayout(info.THUMBNAIL_PATH)
                if migrated:
                    log.info("Migrated %s thumbnail(s) to per-file folders", migrated)

            self._migrate_optimized_asset_paths()

            
            self.has_unsaved_changes = False

            
            self.check_if_paths_are_valid()

            
            smartedit_thumbnails = info.get_default_path("THUMBNAIL_PATH")
            if os.path.exists(smartedit_thumbnails) and clear_thumbnails:
                
                shutil.rmtree(smartedit_thumbnails, True)
                os.mkdir(smartedit_thumbnails)

            
            self.add_to_recent_files(file_path)

            
            self.upgrade_project_data_structures()

            
            project_profile_desc = self._data.get("profile", "HD 720p 30 fps")
            profile = self.get_profile(profile_desc=project_profile_desc)
            if not profile:
                
                profile = self.get_profile(profile_desc="HD 720p 30 fps")

            
            self.apply_default_audio_settings()

        
        get_app().updates.load(self._data)

    def rescale_keyframes(self, scale_factor):
        """Adjust all keyframe coordinates from previous FPS to new FPS (using a scale factor)
           and return scaled project data without modifing the current project."""
        log.info('Scale all keyframes by a factor of %s', scale_factor)
        
        scaler = KeyframeScaler(factor=scale_factor)
        scaler(self._data)

    def read_legacy_project_file(self, file_path):
        """Attempt to read a legacy version 1.x smartedit project file"""
        import sys
        import pickle
        from classes.query import File, Track, Clip, Transition
        import smartedit
        import json

        
        _ = get_app()._tr

        
        project_data = {}
        project_data["version"] = {"smartedit-qt": info.VERSION,
                                   "libsmartedit": smartedit.SMARTEDIT_VERSION_FULL}

        
        fps = get_app().project.get("fps")
        fps_float = float(fps["num"]) / float(fps["den"])

        
        from classes.legacy.smartedit import classes as legacy_classes
        from classes.legacy.smartedit.classes import project as legacy_project
        from classes.legacy.smartedit.classes import sequences as legacy_sequences
        from classes.legacy.smartedit.classes import track as legacy_track
        from classes.legacy.smartedit.classes import clip as legacy_clip
        from classes.legacy.smartedit.classes import keyframe as legacy_keyframe
        from classes.legacy.smartedit.classes import files as legacy_files
        from classes.legacy.smartedit.classes import transition as legacy_transition
        from classes.legacy.smartedit.classes import effect as legacy_effect
        from classes.legacy.smartedit.classes import marker as legacy_marker
        sys.modules['smartedit.classes'] = legacy_classes
        sys.modules['classes.project'] = legacy_project
        sys.modules['classes.sequences'] = legacy_sequences
        sys.modules['classes.track'] = legacy_track
        sys.modules['classes.clip'] = legacy_clip
        sys.modules['classes.keyframe'] = legacy_keyframe
        sys.modules['classes.files'] = legacy_files
        sys.modules['classes.transition'] = legacy_transition
        sys.modules['classes.effect'] = legacy_effect
        sys.modules['classes.marker'] = legacy_marker

        
        failed_files = []

        with open(os.fsencode(file_path), 'rb') as f:
            try:
                
                v1_data = pickle.load(f, fix_imports=True, encoding="UTF-8")
                file_lookup = {}

                
                for item in v1_data.project_folder.items:
                    
                    if isinstance(item, legacy_files.SmartEditFile):
                        
                        try:
                            clip = smartedit.Clip(item.name)
                            reader = clip.Reader()
                            file_data = json.loads(reader.Json(), strict=False)

                            
                            file_data["media_type"] = get_media_type(file_data)

                            
                            file = File()
                            file.data = file_data
                            file.save()

                            
                            file_lookup[item.unique_id] = file

                        except Exception:
                            log.error("%s is not a valid video, audio, or image file",
                                      item.name,
                                      exc_info=1)
                            failed_files.append(item.name)

                
                track_list = Track.filter()
                for track in track_list:
                    track.delete()

                
                track_counter = 0
                for legacy_t in reversed(v1_data.sequences[0].tracks):
                    t = Track()
                    t.data = {"number": track_counter, "y": 0, "label": legacy_t.name}
                    t.save()

                    track_counter += 1

                
                track_counter = 0
                for sequence in v1_data.sequences:
                    for track in reversed(sequence.tracks):
                        for clip in track.clips:
                            
                            if clip.file_object.unique_id in file_lookup:
                                file = file_lookup[clip.file_object.unique_id]
                            else:
                                
                                log.info("Skipping importing missing file: %s" % clip.file_object.unique_id)
                                continue

                            
                            if (file.data["media_type"] == "video" or file.data["media_type"] == "image"):
                                
                                thumb_path = os.path.join(info.THUMBNAIL_PATH, "%s.png" % file.data["id"])
                            else:
                                
                                thumb_path = os.path.join(info.PATH, "images", "AudioThumbnail.svg")

                            
                            filename = os.path.basename(file.data["path"])

                            file_path = file.absolute_path()

                            
                            c = smartedit.Clip(file_path)

                            
                            new_clip = json.loads(c.Json(), strict=False)
                            new_clip["file_id"] = file.id
                            new_clip["title"] = filename

                            
                            new_clip["start"] = clip.start_time
                            new_clip["end"] = clip.end_time
                            new_clip["position"] = clip.position_on_track
                            new_clip["layer"] = track_counter

                            
                            if clip.video_fade_in or clip.video_fade_out:
                                new_clip["alpha"]["Points"] = []

                            
                            if clip.video_fade_in:
                                
                                start = smartedit.Point(round(clip.start_time * fps_float) + 1, 0.0, smartedit.BEZIER)
                                start_object = json.loads(start.Json(), strict=False)
                                end = smartedit.Point(round((clip.start_time + clip.video_fade_in_amount) * fps_float) + 1, 1.0, smartedit.BEZIER)
                                end_object = json.loads(end.Json(), strict=False)
                                new_clip["alpha"]["Points"].append(start_object)
                                new_clip["alpha"]["Points"].append(end_object)

                            
                            if clip.video_fade_out:
                                
                                start = smartedit.Point(round((clip.end_time - clip.video_fade_out_amount) * fps_float) + 1, 1.0, smartedit.BEZIER)
                                start_object = json.loads(start.Json(), strict=False)
                                end = smartedit.Point(round(clip.end_time * fps_float) + 1, 0.0, smartedit.BEZIER)
                                end_object = json.loads(end.Json(), strict=False)
                                new_clip["alpha"]["Points"].append(start_object)
                                new_clip["alpha"]["Points"].append(end_object)

                            
                            if clip.audio_fade_in or clip.audio_fade_out:
                                new_clip["volume"]["Points"] = []
                            else:
                                p = smartedit.Point(1, clip.volume / 100.0, smartedit.BEZIER)
                                p_object = json.loads(p.Json(), strict=False)
                                new_clip["volume"] = {"Points": [p_object]}

                            
                            if clip.audio_fade_in:
                                
                                start = smartedit.Point(round(clip.start_time * fps_float) + 1, 0.0, smartedit.BEZIER)
                                start_object = json.loads(start.Json(), strict=False)
                                end = smartedit.Point(round((clip.start_time + clip.video_fade_in_amount) * fps_float) + 1, clip.volume / 100.0, smartedit.BEZIER)
                                end_object = json.loads(end.Json(), strict=False)
                                new_clip["volume"]["Points"].append(start_object)
                                new_clip["volume"]["Points"].append(end_object)

                            
                            if clip.audio_fade_out:
                                
                                start = smartedit.Point(round((clip.end_time - clip.video_fade_out_amount) * fps_float) + 1, clip.volume / 100.0, smartedit.BEZIER)
                                start_object = json.loads(start.Json(), strict=False)
                                end = smartedit.Point(round(clip.end_time * fps_float) + 1, 0.0, smartedit.BEZIER)
                                end_object = json.loads(end.Json(), strict=False)
                                new_clip["volume"]["Points"].append(start_object)
                                new_clip["volume"]["Points"].append(end_object)

                            
                            clip_object = Clip()
                            clip_object.data = new_clip
                            clip_object.save()

                        
                        for trans in track.transitions:
                            
                            if not trans.resource or not os.path.exists(trans.resource):
                                trans.resource = os.path.join(info.PATH, "transitions", "common", "fade.svg")

                            
                            transition_reader = smartedit.QtImageReader(trans.resource)

                            trans_begin_value = 1.0
                            trans_end_value = -1.0
                            if trans.reverse:
                                trans_begin_value = -1.0
                                trans_end_value = 1.0

                            brightness = smartedit.Keyframe()
                            brightness.AddPoint(1, trans_begin_value, smartedit.BEZIER)
                            brightness.AddPoint(round(trans.length * fps_float) + 1, trans_end_value, smartedit.BEZIER)
                            contrast = smartedit.Keyframe(trans.softness * 10.0)

                            
                            transitions_data = {
                                "id": get_app().project.generate_id(),
                                "layer": track_counter,
                                "title": "Transition",
                                "type": "Mask",
                                "position": trans.position_on_track,
                                "start": 0,
                                "end": trans.length,
                                "brightness": json.loads(brightness.Json(), strict=False),
                                "contrast": json.loads(contrast.Json(), strict=False),
                                "reader": json.loads(transition_reader.Json(), strict=False),
                                "replace_image": False
                            }

                            
                            t = Transition()
                            t.data = transitions_data
                            t.save()

                        
                        track_counter += 1

            except Exception as ex:
                
                msg = "Failed to load legacy project file %(path)s" % {"path": file_path}
                log.error(msg, exc_info=1)
                raise RuntimeError(msg) from ex

        
        if failed_files:
            
            raise RuntimeError("Failed to load the following files:\n%s" % ", ".join(failed_files))

        
        log.info("Successfully loaded legacy project file: %s", file_path)
        return project_data

    def upgrade_project_data_structures(self):
        """Fix any issues with old project files (if any)"""
        smartedit_version = self._data["version"]["smartedit-qt"]
        libsmartedit_version = self._data["version"]["libsmartedit"]

        log.info("Project data: smartedit %s, libsmartedit %s",
                 smartedit_version, libsmartedit_version)

        if smartedit_version == "0.0.0":
            
            
            for clip in self._data["clips"]:
                
                for point in clip["alpha"]["Points"]:
                    
                    if "co" in point:
                        point["co"]["Y"] = 1.0 - point["co"]["Y"]
                    if "handle_left" in point:
                        point["handle_left"]["Y"] = 1.0 - point["handle_left"]["Y"]
                    if "handle_right" in point:
                        point["handle_right"]["Y"] = 1.0 - point["handle_right"]["Y"]

        elif smartedit_version <= "2.1.0-dev":
            
            
            for clip_type in ["clips", "effects"]:
                for clip in self._data[clip_type]:
                    for object in [clip] + clip.get('effects', []):
                        for item_key, item_data in object.items():
                            
                            if type(item_data) == dict and "Points" in item_data:
                                for point in item_data.get("Points"):
                                    
                                    if "handle_left" in point:
                                        
                                        point.get("handle_left")["X"] = 0.5
                                        point.get("handle_left")["Y"] = 1.0
                                    if "handle_right" in point:
                                        
                                        point.get("handle_right")["X"] = 0.5
                                        point.get("handle_right")["Y"] = 0.0

                            elif type(item_data) == dict and "red" in item_data:
                                for color in ["red", "blue", "green", "alpha"]:
                                    for point in item_data.get(color).get("Points"):
                                        
                                        if "handle_left" in point:
                                            
                                            point.get("handle_left")["X"] = 0.5
                                            point.get("handle_left")["Y"] = 1.0
                                        if "handle_right" in point:
                                            
                                            point.get("handle_right")["X"] = 0.5
                                            point.get("handle_right")["Y"] = 0.0

        elif smartedit_version.startswith("2.5."):
            
            log.debug("Scanning SmartEdit 2.5 project for legacy cropping")
            for clip in self._data.get("clips", []):
                
                crop_x = clip.pop("crop_x", {})
                crop_y = clip.pop("crop_y", {})
                crop_width = clip.pop("crop_width", {})
                crop_height = clip.pop("crop_height", {})

                if any([self.is_keyframe_valid(crop_x, 0.0),
                        self.is_keyframe_valid(crop_y, 0.0),
                        self.is_keyframe_valid(crop_width, 1.0),
                        self.is_keyframe_valid(crop_height, 1.0),
                       ]):
                    
                    log.info("Migrating SmartEdit 2.5 crop properties for clip %s", clip.get("id", "<unknown>"))
                    from json import loads as jl
                    effect = smartedit.EffectInfo().CreateEffect("Crop")
                    effect.Id(get_app().project.generate_id())
                    effect_json = jl(effect.Json())

                    
                    effect_json.update({
                        "x": crop_x or jl(smartedit.Keyframe(0.0).Json()),
                        "y": crop_y or jl(smartedit.Keyframe(0.0).Json()),
                        "right": crop_width or jl(smartedit.Keyframe(1.0).Json()),
                        "bottom": crop_height or jl(smartedit.Keyframe(1.0).Json()),
                    })

                    
                    for prop in ["right", "bottom"]:
                        for point in effect_json[prop].get("Points", []):
                            point["co"]["Y"] = 1.0 - point.get("co", {}).get("Y", 0.0)

                    
                    clip["effects"].append(effect_json)


        elif smartedit_version <= "3.1.1":

            
            log.debug("Scanning SmartEdit project for legacy TrackedObjectBBox (background_alpha, stroke_alpha)")

            for clip in self._data.get("clips", []):
                for effect in clip.get("effects", []):
                    if effect.get("name") in ["Tracker", "Object Detector"]:

                        
                        if "display_box_text" in effect:
                            log.info("Migrating legacy Object Detector display_box_text property "
                                     "for clip %s", clip.get("id", "<unknown>"))
                            display_box_text_points = effect.get("display_box_text", {}).get("Points", [])
                            for point in display_box_text_points:
                                if "co" in point:
                                    display_box_text = point.get("co", {}).get("Y", 1.0)
                                    point["co"]["Y"] = 1.0 - display_box_text
                            if not display_box_text_points:
                                
                                display_box_text_points.append(json.loads(smartedit.Point(1.0).Json()))

                        
                        objects = effect.get("objects", {})
                        for tracked_key, tracked_data in objects.items():
                            log.info("Migrating legacy TrackedObjectBBox alpha properties "
                                     "for clip %s and tracked object: %s", clip.get("id", "<unknown>"), tracked_key)

                            
                            child_clip_id = tracked_data.get("child_clip_id")
                            if child_clip_id:
                                for child_clip in self._data.get("clips", []):
                                    if child_clip.get("id") == child_clip_id:
                                        log.info(f"Migrating child_clip_id {child_clip_id} to parent property for tracked object {tracked_key}")
                                        child_clip["parentObjectId"] = tracked_key

                            
                            background_alpha_points = tracked_data.get("background_alpha", {}).get("Points", [])
                            for point in background_alpha_points:
                                if "co" in point:
                                    background_alpha = point.get("co", {}).get("Y", 1.0)
                                    point["co"]["Y"] = 1.0 - background_alpha

                            
                            stroke_alpha_points = tracked_data.get("stroke_alpha", {}).get("Points", [])
                            for point in stroke_alpha_points:
                                if "co" in point:
                                    stroke_alpha = point.get("co", {}).get("Y", 1.0)
                                    point["co"]["Y"] = 1.0 - stroke_alpha

        
        
        
        if (
            self._version_at_most(libsmartedit_version, "0.7.0")
            and self._version_at_most(smartedit_version, "3.5.1")
            and "-" not in smartedit_version
        ):
            self._migrate_legacy_crop_locations()

        
        
        
        
        if (
            self._numeric_version(smartedit_version) == (4, 0, 0)
            and "-" not in smartedit_version
        ):
            self._migrate_400_non_crop_locations()

        
        if self._data.get("id") == "T0":
            self._data["id"] = self.generate_id()

    @staticmethod
    def _numeric_version(value):
        """Return three numeric components from a release-like version."""
        numbers = [int(part) for part in re.findall(r"\d+", str(value))[:3]]
        return tuple((numbers + [0, 0, 0])[:3])

    @classmethod
    def _version_at_most(cls, version, cutoff):
        """Compare the numeric components of release-like version strings."""
        return cls._numeric_version(version) <= cls._numeric_version(cutoff)

    @staticmethod
    def _keyframe_value(keyframe_data, frame, default):
        """Evaluate serialized keyframe data, falling back safely if malformed."""
        if not isinstance(keyframe_data, dict):
            return default
        try:
            keyframe = smartedit.Keyframe()
            keyframe.SetJson(json.dumps(keyframe_data))
            return keyframe.GetValue(int(round(frame)))
        except (RuntimeError, TypeError, ValueError):
            return default

    @staticmethod
    def _legacy_location_factor(value, canvas_size, clip_size, alignment):
        """Return the old/new location-unit ratio for one clip axis."""
        if not value or canvas_size <= 0.0 or clip_size <= 0.0:
            return 1.0
        if alignment == "start":
            denominator = clip_size if value < 0.0 else canvas_size
        elif alignment == "end":
            denominator = canvas_size if value < 0.0 else clip_size
        else:
            denominator = (canvas_size + clip_size) / 2.0
        return canvas_size / denominator if denominator else 1.0

    def _migrate_legacy_crop_locations(self):
        """Preserve positions of SCALE_CROP clips saved by libsmartedit <= 0.7."""
        canvas_width = float(self._data.get("width") or 0.0)
        canvas_height = float(self._data.get("height") or 0.0)
        if canvas_width <= 0.0 or canvas_height <= 0.0:
            return

        files = {
            file_data.get("id"): file_data
            for file_data in self._data.get("files", [])
            if isinstance(file_data, dict)
        }
        horizontal_alignment = {
            smartedit.GRAVITY_TOP_LEFT: "start",
            smartedit.GRAVITY_LEFT: "start",
            smartedit.GRAVITY_BOTTOM_LEFT: "start",
            smartedit.GRAVITY_TOP_RIGHT: "end",
            smartedit.GRAVITY_RIGHT: "end",
            smartedit.GRAVITY_BOTTOM_RIGHT: "end",
        }
        vertical_alignment = {
            smartedit.GRAVITY_TOP_LEFT: "start",
            smartedit.GRAVITY_TOP: "start",
            smartedit.GRAVITY_TOP_RIGHT: "start",
            smartedit.GRAVITY_BOTTOM_LEFT: "end",
            smartedit.GRAVITY_BOTTOM: "end",
            smartedit.GRAVITY_BOTTOM_RIGHT: "end",
        }

        for clip in self._data.get("clips", []):
            if clip.get("scale") != smartedit.SCALE_CROP:
                continue

            reader = clip.get("reader") or files.get(clip.get("file_id"), {})
            source_width = float(reader.get("width") or 0.0)
            source_height = float(reader.get("height") or 0.0)
            if source_width <= 0.0 or source_height <= 0.0:
                continue

            crop_scale = max(
                canvas_width / source_width,
                canvas_height / source_height,
            )
            base_width = source_width * crop_scale
            base_height = source_height * crop_scale
            gravity = clip.get("gravity", smartedit.GRAVITY_CENTER)
            x_alignment = horizontal_alignment.get(gravity, "center")
            y_alignment = vertical_alignment.get(gravity, "center")
            migrated = False

            for property_name, canvas_size, base_size, alignment, scale_name in (
                ("location_x", canvas_width, base_width, x_alignment, "scale_x"),
                ("location_y", canvas_height, base_height, y_alignment, "scale_y"),
            ):
                for point in clip.get(property_name, {}).get("Points", []):
                    coordinate = point.get("co")
                    if not isinstance(coordinate, dict) or "Y" not in coordinate:
                        continue
                    frame = coordinate.get("X", 1.0)
                    value = coordinate["Y"]
                    scale_value = self._keyframe_value(
                        clip.get(scale_name), frame, 1.0
                    )
                    factor = self._legacy_location_factor(
                        value, canvas_size, base_size * scale_value, alignment
                    )
                    if factor != 1.0:
                        coordinate["Y"] = value * factor
                        migrated = True

            if migrated:
                log.info(
                    "Migrating legacy SCALE_CROP location keyframes for clip %s",
                    clip.get("id", "<unknown>"),
                )

    def _migrate_400_non_crop_locations(self):
        """Preserve non-Crop positions saved by the SmartEdit 4.0.0 release."""
        canvas_width = float(self._data.get("width") or 0.0)
        canvas_height = float(self._data.get("height") or 0.0)
        if canvas_width <= 0.0 or canvas_height <= 0.0:
            return

        files = {
            file_data.get("id"): file_data
            for file_data in self._data.get("files", [])
            if isinstance(file_data, dict)
        }
        horizontal_alignment = {
            smartedit.GRAVITY_TOP_LEFT: "start", smartedit.GRAVITY_LEFT: "start",
            smartedit.GRAVITY_BOTTOM_LEFT: "start", smartedit.GRAVITY_TOP_RIGHT: "end",
            smartedit.GRAVITY_RIGHT: "end", smartedit.GRAVITY_BOTTOM_RIGHT: "end",
        }
        vertical_alignment = {
            smartedit.GRAVITY_TOP_LEFT: "start", smartedit.GRAVITY_TOP: "start",
            smartedit.GRAVITY_TOP_RIGHT: "start", smartedit.GRAVITY_BOTTOM_LEFT: "end",
            smartedit.GRAVITY_BOTTOM: "end", smartedit.GRAVITY_BOTTOM_RIGHT: "end",
        }

        for clip in self._data.get("clips", []):
            scale_mode = clip.get("scale", smartedit.SCALE_FIT)
            if scale_mode == smartedit.SCALE_CROP:
                continue
            reader = clip.get("reader") or files.get(clip.get("file_id"), {})
            source_width = float(reader.get("width") or 0.0)
            source_height = float(reader.get("height") or 0.0)
            if source_width <= 0.0 or source_height <= 0.0:
                continue

            gravity = clip.get("gravity", smartedit.GRAVITY_CENTER)
            for property_name, canvas_size, source_size, alignment, scale_name in (
                ("location_x", canvas_width, source_width,
                 horizontal_alignment.get(gravity, "center"), "scale_x"),
                ("location_y", canvas_height, source_height,
                 vertical_alignment.get(gravity, "center"), "scale_y"),
            ):
                for point in clip.get(property_name, {}).get("Points", []):
                    coordinate = point.get("co")
                    if not isinstance(coordinate, dict) or "Y" not in coordinate:
                        continue
                    frame = coordinate.get("X", 1.0)
                    value = coordinate["Y"]
                    margin = self._keyframe_value(clip.get("margin"), frame, 0.0)
                    margin_pixels = max(0.0, min(0.5, margin)) * min(
                        canvas_width, canvas_height)
                    layout_size = max(1.0, canvas_size - (2.0 * margin_pixels))

                    if scale_mode == smartedit.SCALE_STRETCH:
                        base_size = layout_size
                    elif scale_mode == smartedit.SCALE_NONE:
                        base_size = source_size
                    else:
                        fit_scale = min(
                            (canvas_width - 2.0 * margin_pixels) / source_width,
                            (canvas_height - 2.0 * margin_pixels) / source_height,
                        )
                        base_size = source_size * fit_scale

                    clip_size = base_size * self._keyframe_value(
                        clip.get(scale_name), frame, 1.0)
                    factor = self._legacy_location_factor(
                        value, layout_size, clip_size, alignment)
                    if factor:
                        
                        
                        coordinate["Y"] = value * layout_size / (factor * canvas_size)

    def is_keyframe_valid(self, keyframe, default_value):
        """Check if a keyframe is not empty (i.e. > 1 point, or a non default_value)"""
        points = keyframe.get("Points", [])
        if not points or not isinstance(points, list):
            return False
        return any([
            len(points) > 1,
            points[0].get("co", {}).get("Y", default_value) != default_value,
        ])

    def save(self, file_path, backup_only=False):
        """ Save project file to disk """
        import smartedit

        log.info("Saving project file: %s", file_path)

        
        if not backup_only:
            self.move_temp_paths_to_project_folder(
                file_path, previous_path=self.current_filepath)

        
        self._data["version"] = {"smartedit-qt": info.VERSION,
                                 "libsmartedit": smartedit.SMARTEDIT_VERSION_FULL}

        
        self.write_to_file(
            file_path,
            self._data,
            path_mode="ignore" if backup_only else "relative",
            previous_path=self.current_filepath if not backup_only else None)

        if not backup_only:
            
            self.current_filepath = file_path

            
            info.THUMBNAIL_PATH = os.path.join(get_assets_path(self.current_filepath), "thumbnail")
            info.TITLE_PATH = os.path.join(get_assets_path(self.current_filepath), "title")
            info.BLENDER_PATH = os.path.join(get_assets_path(self.current_filepath), "blender")
            info.PROTOBUF_DATA_PATH = os.path.join(get_assets_path(self.current_filepath), "protobuf_data")
            info.CLIPBOARD_PATH = os.path.join(get_assets_path(self.current_filepath), "clipboard")
            info.COMFYUI_OUTPUT_PATH = os.path.join(get_assets_path(self.current_filepath), "comfyui-output")
            info.PROXY_PATH = os.path.join(get_assets_path(self.current_filepath), "optimized")

            self.add_to_recent_files(file_path)
            self.has_unsaved_changes = False

    @staticmethod
    def _paths_match(path_a, path_b):
        """Return True when both paths resolve to the same local filesystem path."""
        if not path_a or not path_b:
            return False
        return os.path.normcase(os.path.abspath(path_a)) == os.path.normcase(os.path.abspath(path_b))

    @staticmethod
    def _path_relative_to_root(path, root):
        """Return a safe relative path when path is contained by root."""
        if not path or not root:
            return None
        path_abs = os.path.normcase(os.path.abspath(path))
        root_abs = os.path.normcase(os.path.abspath(root))
        try:
            if os.path.commonpath([path_abs, root_abs]) != root_abs:
                return None
        except ValueError:
            return None
        return os.path.relpath(os.path.abspath(path), os.path.abspath(root))

    def _should_move_runtime_assets(self, source_root, default_name):
        """Return True when a source root is the active runtime temp directory."""
        default_root = info.get_default_path(default_name)
        return self._paths_match(source_root, default_root)

    def _sync_asset_entry(self, source_path, target_path, move=False, replace_existing=False):
        """Copy or move a file/folder into the target asset tree."""
        if not os.path.exists(source_path):
            return

        if os.path.isdir(source_path):
            if os.path.exists(target_path) and not os.path.isdir(target_path):
                os.remove(target_path)

            if replace_existing and os.path.isdir(target_path):
                shutil.rmtree(target_path, True)

            if not os.path.exists(target_path):
                parent_path = os.path.dirname(target_path)
                if parent_path:
                    os.makedirs(parent_path, exist_ok=True)
                if move:
                    shutil.move(source_path, target_path)
                else:
                    shutil.copytree(source_path, target_path)
                return

            for child_name in os.listdir(source_path):
                self._sync_asset_entry(
                    os.path.join(source_path, child_name),
                    os.path.join(target_path, child_name),
                    move=move,
                    replace_existing=replace_existing,
                )

            if move and os.path.isdir(source_path) and not os.listdir(source_path):
                os.rmdir(source_path)
            return

        if os.path.exists(target_path):
            if replace_existing:
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path, True)
                else:
                    os.remove(target_path)
            elif move:
                os.remove(source_path)
                return
            else:
                return

        parent_path = os.path.dirname(target_path)
        if parent_path:
            os.makedirs(parent_path, exist_ok=True)
        if move:
            shutil.move(source_path, target_path)
        else:
            shutil.copy2(source_path, target_path)

    def _sync_asset_root(self, source_root, target_root, move=False, replace_existing=False):
        """Copy or move all entries from a source asset root into a target root."""
        if not source_root or not os.path.exists(source_root):
            return
        if self._paths_match(source_root, target_root):
            return

        os.makedirs(target_root, exist_ok=True)
        for entry_name in os.listdir(source_root):
            self._sync_asset_entry(
                os.path.join(source_root, entry_name),
                os.path.join(target_root, entry_name),
                move=move,
                replace_existing=replace_existing,
            )

    def move_temp_paths_to_project_folder(self, file_path, previous_path=None):
        """ Move all temp files (such as Thumbnails, Titles, and Blender animations) to the project asset folder. """
        try:
            
            asset_path = get_assets_path(file_path)
            target_thumb_path = os.path.join(asset_path, "thumbnail")
            target_title_path = os.path.join(asset_path, "title")
            target_blender_path = os.path.join(asset_path, "blender")
            target_protobuf_path = os.path.join(asset_path, "protobuf_data")
            target_clipboard_path = os.path.join(asset_path, "clipboard")
            target_comfy_output_path = os.path.join(asset_path, "comfyui-output")
            target_proxy_path = os.path.join(asset_path, "optimized")
            target_recording_path = os.path.join(asset_path, "recordings")

            
            try:
                for target_dir in [asset_path, target_thumb_path, target_title_path,
                                   target_blender_path, target_protobuf_path,
                                   target_clipboard_path, target_comfy_output_path,
                                   target_proxy_path, target_recording_path]:
                    if not os.path.exists(target_dir):
                        os.mkdir(target_dir)
            except OSError:
                pass

            
            
            if previous_path:
                previous_asset_path = get_assets_path(previous_path)
                info.THUMBNAIL_PATH = os.path.join(previous_asset_path, "thumbnail")
                info.TITLE_PATH = os.path.join(previous_asset_path, "title")
                info.BLENDER_PATH = os.path.join(previous_asset_path, "blender")
                info.PROTOBUF_DATA_PATH = os.path.join(previous_asset_path, "protobuf_data")
                info.CLIPBOARD_PATH = os.path.join(previous_asset_path, "clipboard")
                info.COMFYUI_OUTPUT_PATH = os.path.join(previous_asset_path, "comfyui-output")
                info.PROXY_PATH = os.path.join(previous_asset_path, "optimized")

            
            copied_assets = {
                "blender": set(),
                "title": set(),
                "clipboard": set(),
                "comfyui_output": set(),
                "proxy": set(),
            }
            reader_paths = {}
            recording_roots = [
                (os.path.join(info.USER_PATH, "recordings"), True),
            ]
            if previous_path:
                previous_recording_path = os.path.join(
                    get_assets_path(previous_path), "recordings")
                if not self._paths_match(previous_recording_path, recording_roots[0][0]):
                    recording_roots.append((previous_recording_path, False))

            def relocate_effect_protobuf(effect):
                if not isinstance(effect, dict) or "protobuf_data_path" not in effect:
                    return
                old_protobuf_path = effect["protobuf_data_path"]
                old_protobuf_dir, protobuf_name = os.path.split(old_protobuf_path)
                if not protobuf_name:
                    return
                new_protobuf_path = os.path.join(target_protobuf_path, protobuf_name)
                if os.path.abspath(old_protobuf_dir) != os.path.abspath(target_protobuf_path):
                    self._sync_asset_entry(old_protobuf_path, new_protobuf_path)
                    effect["protobuf_data_path"] = new_protobuf_path
                    log.info("Copied protobuf %s to %s", old_protobuf_path, target_protobuf_path)

            self._sync_asset_root(
                info.THUMBNAIL_PATH,
                target_thumb_path,
                move=self._should_move_runtime_assets(info.THUMBNAIL_PATH, "THUMBNAIL_PATH"),
            )
            self._sync_asset_root(
                info.TITLE_PATH,
                target_title_path,
                move=self._should_move_runtime_assets(info.TITLE_PATH, "TITLE_PATH"),
            )
            self._sync_asset_root(
                info.BLENDER_PATH,
                target_blender_path,
                move=self._should_move_runtime_assets(info.BLENDER_PATH, "BLENDER_PATH"),
            )
            self._sync_asset_root(
                info.CLIPBOARD_PATH,
                target_clipboard_path,
                move=self._should_move_runtime_assets(info.CLIPBOARD_PATH, "CLIPBOARD_PATH"),
            )
            self._sync_asset_root(
                info.COMFYUI_OUTPUT_PATH,
                target_comfy_output_path,
                move=self._should_move_runtime_assets(info.COMFYUI_OUTPUT_PATH, "COMFYUI_OUTPUT_PATH"),
                replace_existing=True,
            )
            self._sync_asset_root(
                info.PROTOBUF_DATA_PATH,
                target_protobuf_path,
                move=self._should_move_runtime_assets(info.PROTOBUF_DATA_PATH, "PROTOBUF_DATA_PATH"),
            )
            self._sync_asset_root(
                info.PROXY_PATH,
                target_proxy_path,
                move=self._should_move_runtime_assets(info.PROXY_PATH, "PROXY_PATH"),
            )

            
            for file in self._data["files"]:
                path = file["path"]
                file_id = file["id"]

                
                file["image"] = os.path.join(target_thumb_path, f"{file_id}.png")

                
                new_asset_path = None
                for recording_root, move_recording in recording_roots:
                    relative_recording_path = self._path_relative_to_root(path, recording_root)
                    if relative_recording_path is None:
                        continue
                    recording_asset_path = os.path.join(
                        target_recording_path, relative_recording_path)
                    relocated_recording = not self._paths_match(path, recording_asset_path)
                    if relocated_recording:
                        self._sync_asset_entry(
                            path, recording_asset_path, move=move_recording)
                    if os.path.exists(recording_asset_path):
                        new_asset_path = recording_asset_path
                        if relocated_recording:
                            log.info(
                                "%s recording %s to %s",
                                "Moved" if move_recording else "Copied",
                                path,
                                recording_asset_path,
                            )
                    break

                if info.BLENDER_PATH in path:
                    path_abs = os.path.abspath(path)
                    blender_root_abs = os.path.abspath(info.BLENDER_PATH)
                    if path_abs.startswith(blender_root_abs + os.sep):
                        relative_blender_path = os.path.relpath(path_abs, blender_root_abs)
                        blender_root_name = relative_blender_path.split(os.sep, 1)[0]
                        if blender_root_name and blender_root_name not in copied_assets["blender"]:
                            source_blender_dir = os.path.join(info.BLENDER_PATH, blender_root_name)
                            if os.path.abspath(source_blender_dir) != os.path.abspath(target_blender_path):
                                copied_assets["blender"].add(blender_root_name)
                                log.info("Copied dir %s to %s", blender_root_name, target_blender_path)
                        new_asset_path = os.path.join(target_blender_path, relative_blender_path)

                if info.TITLE_PATH in path:
                    
                    old_dir, asset_name = os.path.split(path)
                    if asset_name not in copied_assets["title"]:
                        
                        if os.path.abspath(old_dir) != os.path.abspath(target_title_path):
                            copied_assets["title"].add(asset_name)
                            log.info("Copied title %s to %s", asset_name, target_title_path)
                    new_asset_path = os.path.join(target_title_path, asset_name)

                if info.CLIPBOARD_PATH in path:
                    old_dir, asset_name = os.path.split(path)
                    if asset_name not in copied_assets["clipboard"]:
                        if os.path.abspath(old_dir) != os.path.abspath(target_clipboard_path):
                            copied_assets["clipboard"].add(asset_name)
                            log.info("Copied clipboard %s to %s", asset_name, target_clipboard_path)
                    new_asset_path = os.path.join(target_clipboard_path, asset_name)

                comfy_output_abs = os.path.abspath(info.COMFYUI_OUTPUT_PATH)
                path_abs = os.path.abspath(path)
                if path_abs.startswith(comfy_output_abs + os.sep):
                    if os.path.abspath(os.path.dirname(path)) != os.path.abspath(target_comfy_output_path):
                        relative_output_path = os.path.relpath(path_abs, comfy_output_abs)
                        if relative_output_path not in copied_assets["comfyui_output"]:
                            copied_assets["comfyui_output"].add(relative_output_path)
                            log.info("Copied ComfyUI output %s to %s", relative_output_path, target_comfy_output_path)
                        new_asset_path = os.path.join(target_comfy_output_path, relative_output_path)

                
                if new_asset_path:
                    file["path"] = new_asset_path
                    reader_paths[file_id] = new_asset_path
                    log.info("Set file %s path to %s", file_id, new_asset_path)

                proxy_reader = file.get("proxy_reader")
                proxy_path = proxy_reader.get("path") if isinstance(proxy_reader, dict) else ""
                if proxy_path and info.PROXY_PATH in proxy_path:
                    proxy_dir, proxy_name = os.path.split(proxy_path)
                    if proxy_name not in copied_assets["proxy"]:
                        if os.path.abspath(proxy_dir) != os.path.abspath(target_proxy_path):
                            copied_assets["proxy"].add(proxy_name)
                            source_proxy = os.path.join(proxy_dir, proxy_name)
                            target_proxy = os.path.join(target_proxy_path, proxy_name)
                            if os.path.isdir(source_proxy):
                                if os.path.exists(target_proxy):
                                    shutil.rmtree(target_proxy, True)
                                shutil.copytree(source_proxy, target_proxy)
                            elif os.path.exists(source_proxy):
                                shutil.copy2(source_proxy, target_proxy)
                            log.info("Copied proxy %s to %s", proxy_name, target_proxy_path)
                    proxy_reader["path"] = os.path.join(target_proxy_path, proxy_name)

            
            for effect in self._data.get("effects", []):
                relocate_effect_protobuf(effect)

            
            for clip in self._data["clips"]:
                file_id = clip["file_id"]
                clip_id = clip["id"]

                
                clip["image"] = os.path.join(target_thumb_path, f"{file_id}.png")

                log.info("Checking clip %s path for file %s", clip_id, file_id)
                
                
                if file_id and file_id in reader_paths:
                    clip["reader"]["path"] = reader_paths[file_id]
                    log.info("Updated clip %s path for file %s", clip_id, file_id)

                log.info("Checking effects in clip %s path for protobuf files" % clip_id)
                for effect in clip.get("effects", []):
                    relocate_effect_protobuf(effect)

        except Exception:
            log.error(
                "Error while moving temp paths to project assets folder %s",
                asset_path, exc_info=1)

    def add_to_recent_files(self, file_path):
        """ Add this project to the recent files list """
        if not file_path or file_path is info.BACKUP_FILE:
            
            return

        s = get_app().get_settings()
        recent_projects = s.get("recent_projects")

        normalized_path = normalized_local_path(file_path)
        normalized_key = comparable_local_path(normalized_path)

        
        recent_projects = [
            normalized_local_path(existing_path)
            for existing_path in recent_projects
            if comparable_local_path(existing_path) != normalized_key
        ]

        
        if len(recent_projects) >= 10:
            del recent_projects[0]

        
        recent_projects.append(normalized_path)

        
        s.set("recent_projects", recent_projects)
        s.save()

    def check_if_paths_are_valid(self):
        """Check if all paths are valid, and prompt to update them if needed"""
        app = get_app()
        settings = app.get_settings()
        
        _ = app._tr

        log.info("checking project files...")
        prompt_state = {"cancelled": False, "missing_path_decisions": {}}

        def _path_is_missing(path):
            return bool(path) and "%" not in path and not os.path.exists(path)

        def _resolve_missing_path(path):
            """Prompt to locate a missing path, returning resolved path or empty when skipped."""
            if not _path_is_missing(path):
                return path, False

            
            
            
            missing_path_decisions = prompt_state.setdefault("missing_path_decisions", {})
            if path in missing_path_decisions:
                cached_path = missing_path_decisions[path]
                if cached_path:
                    return cached_path, False
                return "", True

            found_path, is_modified, is_skipped = find_missing_file(path, prompt_state)
            if found_path and is_modified and not is_skipped:
                settings.setDefaultPath(settings.actionType.IMPORT, found_path)
                missing_path_decisions[path] = found_path
                return found_path, False
            if is_skipped:
                missing_path_decisions[path] = ""
                skip_mode = prompt_state.get("last_skip")
                if skip_mode == "all":
                    skip_detail = " (user selected Skip All)"
                else:
                    skip_detail = " (user selected Skip File)"
                
                log.warning(
                    "Missing path skipped during project load%s: %s",
                    skip_detail,
                    path,
                )
            return "", True

        def _collect_effect_path_refs(effect):
            """Collect mutable refs to path-like fields used by effects."""
            refs = []
            seen = set()

            self._drop_obsolete_effect_resource(effect)

            def _add_ref(container, key):
                if not isinstance(container, dict):
                    return
                value = container.get(key, "")
                if not isinstance(value, str) or not value:
                    return
                ref_id = (id(container), key)
                if ref_id in seen:
                    return
                seen.add(ref_id)
                refs.append((container, key, value))

            def _walk(obj, parent_key=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, dict):
                            if isinstance(value.get("path"), str) and "reader" in key.lower():
                                _add_ref(value, "path")
                            _walk(value, key)
                        elif isinstance(value, list):
                            _walk(value, key)
                        elif isinstance(value, str):
                            if key in {"resource", "protobuf_data_path", "lut_path", "image"}:
                                _add_ref(obj, key)
                            elif key == "path" and "reader" in parent_key.lower():
                                _add_ref(obj, key)
                elif isinstance(obj, list):
                    for item in obj:
                        _walk(item, parent_key)

            _walk(effect)
            return refs

        def _first_missing_effect_path(effect):
            for _, _, path in _collect_effect_path_refs(effect):
                if _path_is_missing(path):
                    return path
            return ""

        def _repair_effect_paths(effect):
            """Prompt for missing paths on an effect-like dict."""
            if not isinstance(effect, dict):
                return False

            path_refs = _collect_effect_path_refs(effect)
            missing_paths = []
            for _, _, path in path_refs:
                if _path_is_missing(path) and path not in missing_paths:
                    missing_paths.append(path)

            for missing_path in missing_paths:
                resolved_path, should_remove = _resolve_missing_path(missing_path)
                if should_remove:
                    log.warning(
                        "Removing effect with unresolved path. effect_id=%s missing_path=%s",
                        effect.get("id", ""),
                        missing_path,
                    )
                    return False
                for container, key, current_path in path_refs:
                    if current_path == missing_path:
                        container[key] = resolved_path

            return True

        
        files_sorted = sorted(
            self._data["files"],
            key=lambda f: os.path.basename(f.get("path", "")).lower()
        )
        for file in files_sorted:
            path = file["path"]
            parent_path, file_name_with_ext = os.path.split(path)

            log.info("checking file %s", path)
            if not os.path.exists(path) and "%" not in path:
                
                resolved_path, should_remove = _resolve_missing_path(path)
                if should_remove:
                    log.info('Removed missing file: %s', file_name_with_ext)
                    self._data["files"].remove(file)
                elif resolved_path and resolved_path != path:
                    file["path"] = resolved_path
                    settings.setDefaultPath(settings.actionType.IMPORT, resolved_path)
                    log.info("Auto-updated missing file: %s", resolved_path)

        
        file_paths_by_id = {file.get("id"): file.get("path") for file in self._data["files"]}

        
        for clip in reversed(self._data["clips"]):
            file_id = clip.get("file_id") or clip.get("reader", {}).get("id")
            if file_id and file_id in file_paths_by_id:
                
                reader = clip.get("reader")
                if not isinstance(reader, dict):
                    reader = {}
                    clip["reader"] = reader
                reader["path"] = file_paths_by_id[file_id]

            path = clip.get("reader", {}).get("path", "")

            if file_id and file_id not in file_paths_by_id:
                
                file_name_with_ext = os.path.basename(path) if path else ""
                log.info('Removed missing clip: %s', file_name_with_ext)
                self._data["clips"].remove(clip)
                continue

            if path and not os.path.exists(path) and "%" not in path:
                
                file_name_with_ext = os.path.basename(path)
                log.info('Removed missing clip: %s', file_name_with_ext)
                self._data["clips"].remove(clip)

        
        for effect in reversed(self._data["effects"]):
            self._drop_obsolete_effect_resource(effect)
            if not _repair_effect_paths(effect):
                missing_path = _first_missing_effect_path(effect)
                effect_name = os.path.basename(missing_path) if missing_path else effect.get("id", "")
                log.info("Removed missing effect: %s", effect_name)
                self._data["effects"].remove(effect)

        
        for clip in self._data["clips"]:
            effects = clip.get("effects")
            if not isinstance(effects, list):
                continue
            for effect in reversed(effects):
                self._drop_obsolete_effect_resource(effect)
                if not _repair_effect_paths(effect):
                    missing_path = _first_missing_effect_path(effect)
                    effect_name = os.path.basename(missing_path) if missing_path else effect.get("id", "")
                    log.info("Removed missing clip effect on %s: %s", clip.get("id", ""), effect_name)
                    effects.remove(effect)

    def changed(self, action):
        """ This method is invoked by the UpdateManager each time a change happens (i.e UpdateInterface) """
        updates = get_app().updates

        def mark_dirty():
            if not self.has_unsaved_changes:
                log.debug(
                    "Project dirty flag set: action=%s key=%s ignore_history=%s values=%s",
                    action.type,
                    action.key,
                    updates.ignore_history,
                    action.values,
                )
            self.has_unsaved_changes = True

        if action.type == "insert":
            
            old_vals = self._set(action.key, action.values, add=True)
            action.set_old_values(old_vals)  
            mark_dirty()

        elif action.type == "update":
            
            old_vals = self._set(action.key, action.values)
            action.set_old_values(old_vals)  
            mark_dirty()

            if len(action.key) == 1 and action.key[0] in ["fps"]:
                
                profile_key = self._data.get("profile")
                profile = self.get_profile(profile_key)
                if profile:
                    
                    new_fps = self._data.get("fps")
                    new_fps_float = float(new_fps["num"]) / float(new_fps["den"])
                    old_fps_float = float(old_vals["num"]) / float(old_vals["den"])
                    fps_factor = float(new_fps_float / old_fps_float)

                    if fps_factor != 1.0:
                        log.info(f"Convert {old_fps_float} FPS to {new_fps_float} FPS (profile: {profile.ShortName()})")
                        
                        change_profile(self._data["clips"] + self._data["effects"], profile)

                        
                        self.rescale_keyframes(fps_factor)

                    
                    for file in self._data.get("files", []):
                        
                        if file.get("has_audio") and not file.get("has_video"):
                            
                            file["width"] = profile.info.width
                            file["height"] = profile.info.height
                            file["display_ratio"]["num"] = profile.info.display_ratio.num
                            file["display_ratio"]["den"] = profile.info.display_ratio.den

                            
                            for clip in self._data.get("clips", []):
                                if clip.get("reader", {}).get("id") == file.get("id"):
                                    clip["reader"] = file

                    
                    get_app().updates.load(self._data, reset_history=False)
                else:
                    log.warning(f"No profile found for {profile_key}")

        elif action.type == "delete":
            
            old_vals = self._set(action.key, remove=True)
            action.set_old_values(old_vals)  
            mark_dirty()

        elif action.type == "load":
            
            pass

    
    def generate_id(self, digits=10):
        """ Generate random alphanumeric ids """

        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        id = ""
        for i in range(digits):
            c_index = random.randint(0, len(chars) - 1)
            id += (chars[c_index])
        return id

    def apply_default_audio_settings(self):
        """Apply the default preferences for sampleRate and channels to
        the current project data, to force playback at a specific rate and for
        a specific # of audio channels and channel layout."""
        s = get_app().get_settings()

        
        default_sample_rate = int(s.get("default-samplerate"))
        default_channel_layout = s.get("default-channellayout")

        channels = 2
        channel_layout = smartedit.LAYOUT_STEREO
        if default_channel_layout == "LAYOUT_MONO":
            channels = 1
            channel_layout = smartedit.LAYOUT_MONO
        elif default_channel_layout == "LAYOUT_STEREO":
            channels = 2
            channel_layout = smartedit.LAYOUT_STEREO
        elif default_channel_layout == "LAYOUT_SURROUND":
            channels = 3
            channel_layout = smartedit.LAYOUT_SURROUND
        elif default_channel_layout == "LAYOUT_5POINT1":
            channels = 6
            channel_layout = smartedit.LAYOUT_5POINT1
        elif default_channel_layout == "LAYOUT_7POINT1":
            channels = 8
            channel_layout = smartedit.LAYOUT_7POINT1

        
        self._data["sample_rate"] = default_sample_rate
        self._data["channels"] = channels
        self._data["channel_layout"] = channel_layout

        log.info("Apply default audio playback settings: %s, %s channels" % (self._data["sample_rate"], self._data["channels"]))
