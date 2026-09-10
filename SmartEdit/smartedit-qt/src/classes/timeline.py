"""
 @file
 @brief This file contains a timeline object, which listens for updates and syncs a libsmartedit timeline object
 @author Jonathan Thomas <jonathan@smartedit.org>

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

import smartedit  
from qt_api import QTimer

from classes.updates import UpdateInterface
from classes.logger import log
from classes.app import get_app


class TimelineSync(UpdateInterface):
    """ This class syncs changes from the timeline to libsmartedit """

    def __init__(self, window):
        self.app = get_app()
        self.window = window
        project = self.app.project

        
        fps = project.get("fps")
        width = project.get("width")
        height = project.get("height")
        sample_rate = project.get("sample_rate")
        channels = project.get("channels")
        channel_layout = project.get("channel_layout")

        
        self.timeline = smartedit.Timeline(width, height, smartedit.Fraction(fps["num"], fps["den"]),
                                          sample_rate, channels, channel_layout)
        self.timeline.info.channel_layout = channel_layout
        self.timeline.info.has_audio = True
        self.timeline.info.has_video = True
        self.timeline.info.video_length = 99999
        self.timeline.info.duration = 999.99
        self.timeline.info.sample_rate = sample_rate
        self.timeline.info.channels = channels

        
        self.timeline.Open()

        
        
        self.app.updates.add_listener(self, 0)

        
        self.window.MaxSizeChanged.connect(self.MaxSizeChangedCB)

    def changed(self, action):
        """ This method is invoked by the UpdateManager each time a change happens (i.e UpdateInterface) """

        
        if action and len(action.key) >= 1 and action.key[0].lower() in ["files", "history", "markers", "layers", "scale", "profile", "export_settings"]:
            return

        
        
        
        
        if action and action.type == "update":
            try:
                is_playing = self.window.preview_thread.player.Mode() == smartedit.PLAYBACK_PLAY
            except Exception:
                is_playing = False
            if not is_playing:
                smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = False

        try:
            proxy_service = getattr(self.window, "proxy_service", None)
            if action.type == "load":
                
                self.window.clearSelections()

                
                self.timeline.Close()
                self.timeline.Clear()

                
                payload = action.json(only_value=True)
                if proxy_service:
                    payload = proxy_service.rewrite_json_for_preview(payload)
                self.timeline.SetJson(payload)
                self.timeline.Open()  

                
                self.timeline.ApplyMapperToClips()

                
                self.window.SeekSignal.emit(1, True)

                
                if getattr(self.window, "_project_loading", False):
                    self.window._pending_project_open_refresh = True
                else:
                    self.window.refreshFrameSignal.emit()

            else:
                
                payload = action.json(is_array=True)
                if proxy_service:
                    payload = proxy_service.rewrite_json_for_preview(payload)
                self.timeline.ApplyJsonDiff(payload)

        except Exception as e:
            log.error("Error applying JSON to timeline object in libsmartedit: %s. %s" %
                     (e, action.json(is_array=True)))

        

    def MaxSizeChangedCB(self, new_size):
        """Callback for max sized change (i.e. max size of video widget)"""
        if not self.window.initialized:
            log.info('Deferring SetMaxSize until main window initialization completes')
            self.window._pending_preview_size = new_size
            QTimer.singleShot(0, self.window._finish_pending_preview_resize)
            return

        if getattr(self.window, "_dock_interaction_active", False):
            self.window._pending_preview_size = new_size
            return

        
        device_pixel_ratio = self.window.devicePixelRatioF()
        scaled_width = round(new_size.width() * device_pixel_ratio)
        scaled_height = round(new_size.height() * device_pixel_ratio)

        if scaled_width < 1 or scaled_height < 1:
            log.info(
                "Skipping preview max size update for invalid size: %sx%s",
                scaled_width,
                scaled_height,
            )
            return

        log.info(f"Adjusting max size of preview image: {scaled_width}x{scaled_height}")

        
        previous_preview_width = self.timeline.preview_width
        previous_preview_height = self.timeline.preview_height

        self.timeline.SetMaxSize(scaled_width, scaled_height)

        if (
            previous_preview_width != self.timeline.preview_width
            or previous_preview_height != self.timeline.preview_height
        ):
            
            self.timeline.ClearAllCache(True)

            if getattr(self.window, "_project_loading", False):
                self.window._pending_project_open_refresh = True
                return

            
            self.window.refreshFrameSignal.emit()

    def GetLastFrame(self):
        """Return the last seekable/playable frame on the timeline."""
        try:
            max_frame = max(1, int(self.timeline.GetMaxFrame()))
        except Exception:
            return 1
        return max(1, max_frame - 1)
