"""
 @file
 @brief This file loads the File Properties dialog
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

import os
import json

from qt_api import (
    QDialog, QFileDialog, QDialogButtonBox, QPushButton,
    )


import smartedit

from uuid import uuid4
from classes import info, time_parts, ui_util
from classes.app import get_app
from classes.image_types import get_media_type
from classes.logger import log
from classes.metrics import track_metric_screen
from classes.query import Clip

MAX_FPS_SPINBOX_VALUE = 2147483647


class FileProperties(QDialog):
    """ File Properties Dialog """

    
    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'file-properties.ui')

    def __init__(self, file):
        self.file = file

        
        super().__init__()

        
        ui_util.load_ui(self, self.ui_path)

        
        ui_util.init_ui(self)

        
        app = get_app()
        _ = app._tr

        
        self.s = app.get_settings()

        
        track_metric_screen("file-properties-screen")

        
        self.update_button = QPushButton(_('Update'))
        self.buttonBox.addButton(self.update_button, QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton(QPushButton(_('Cancel')), QDialogButtonBox.RejectRole)

        
        self.settings_data = self.s.get_all_settings()

        
        self.channel_layout_choices = []
        self.initialize()
        self.txtFrameRateNum.valueChanged.connect(self.update_frame_rate_display)
        self.txtFrameRateDen.valueChanged.connect(self.update_frame_rate_display)
        self.txtFrameRateNum.valueChanged.connect(self.update_duration_display)
        self.txtFrameRateDen.valueChanged.connect(self.update_duration_display)

    def initialize(self):
        """Init all form elements / textboxes / etc..."""
        
        app = get_app()
        _ = app._tr

        
        filename = os.path.basename(self.file.data["path"])
        file_extension = os.path.splitext(filename)[1]

        tags = self.file.data.get("tags", "")
        name = self.file.data.get("name", filename)

        
        self.txtFileName.setText(name)
        self.txtTags.setText(tags)
        self.txtFilePath.setText(self.file.data["path"])
        self.btnBrowse.clicked.connect(self.browsePath)

        
        self.txtFrameRateNum.setMaximum(MAX_FPS_SPINBOX_VALUE)
        self.txtFrameRateDen.setMaximum(MAX_FPS_SPINBOX_VALUE)
        self.txtWidth.setValue(self.file.data["width"])
        self.txtHeight.setValue(self.file.data["height"])
        self.txtFrameRateNum.setValue(self.file.data["fps"]["num"])
        self.txtFrameRateDen.setValue(self.file.data["fps"]["den"])
        self.update_frame_rate_display()
        self.update_duration_display()
        self.txtAspectRatioNum.setValue(self.file.data["display_ratio"]["num"])
        self.txtAspectRatioDen.setValue(self.file.data["display_ratio"]["den"])
        self.txtPixelRatioNum.setValue(self.file.data["pixel_ratio"]["num"])
        self.txtPixelRatioDen.setValue(self.file.data["pixel_ratio"]["den"])

        
        fps_editable = "%" in str(self.file.data.get("path") or "")
        self.txtFrameRateNum.setEnabled(fps_editable)
        self.txtFrameRateDen.setEnabled(fps_editable)

        
        self.init_start_end_textboxes(self.file.data)

        
        self.txtVideoFormat.setText(file_extension.replace(".", ""))
        self.txtVideoCodec.setText(self.file.data["vcodec"])
        self.txtAudioCodec.setText(self.file.data["acodec"])
        self.txtSampleRate.setValue(int(self.file.data["sample_rate"]))
        self.txtChannels.setValue(int(self.file.data["channels"]))
        self.txtVideoBitRate.setValue(int(self.file.data["video_bit_rate"]))
        self.txtAudioBitRate.setValue(int(self.file.data["audio_bit_rate"]))

        
        self.txtOutput.setText(json.dumps(self.file.data, sort_keys=True, indent=2))

        
        selected_channel_layout_index = 0
        current_channel_layout = 0
        if self.file.data["has_audio"]:
            current_channel_layout = int(self.file.data["channel_layout"])
        self.channel_layout_choices = []
        layouts = [(0, _("Unknown")),
                   (smartedit.LAYOUT_MONO, _("Mono (1 Channel)")),
                   (smartedit.LAYOUT_STEREO, _("Stereo (2 Channel)")),
                   (smartedit.LAYOUT_SURROUND, _("Surround (3 Channel)")),
                   (smartedit.LAYOUT_5POINT1, _("Surround (5.1 Channel)")),
                   (smartedit.LAYOUT_7POINT1, _("Surround (7.1 Channel)"))]
        for channel_layout_index, layout in enumerate(layouts):
            log.info(layout)
            self.channel_layout_choices.append(layout[0])
            self.cboChannelLayout.addItem(layout[1], layout[0])
            if current_channel_layout == layout[0]:
                selected_channel_layout_index = channel_layout_index

        
        self.cboChannelLayout.setCurrentIndex(selected_channel_layout_index)

        
        self.cboInterlaced.clear()
        self.cboInterlaced.addItem(_("Yes"), "Yes")
        self.cboInterlaced.addItem(_("No"), "No")
        if self.file.data["interlaced_frame"]:
            self.cboInterlaced.setCurrentIndex(0)
        else:
            self.cboInterlaced.setCurrentIndex(1)

        
        self.toolBox.setCurrentIndex(0)

    def update_frame_rate_display(self):
        """Show the current FPS fraction as a calculated float."""
        fps_den = self.txtFrameRateDen.value() or 1
        fps_float = self.txtFrameRateNum.value() / fps_den
        self.lblFrameRateValueDisplay.setText(f"= {fps_float:.2f}")

    def update_duration_display(self):
        """Show the duration adjusted to the currently entered FPS."""
        current_fps_den = self.txtFrameRateDen.value() or 1
        current_fps = self.txtFrameRateNum.value() / current_fps_den

        original_fps_meta = self.file.data.get("fps", {})
        original_fps_num = float(original_fps_meta.get("num") or 0.0)
        original_fps_den = float(original_fps_meta.get("den") or 1.0)
        original_fps = (
            original_fps_num / original_fps_den
            if original_fps_num > 0.0 and original_fps_den > 0.0
            else 0.0
        )

        duration_seconds = float(self.file.data.get("duration") or 0.0)
        if current_fps > 0.0 and original_fps > 0.0:
            duration_seconds *= original_fps / current_fps

        duration_parts = time_parts.secondsToTime(duration_seconds)
        self.txtDuration.setText(
            f"{duration_parts['hour']}:{duration_parts['min']}:{duration_parts['sec']}.{duration_parts['milli']}"
        )

    def init_start_end_textboxes(self, file_object):
        """Initialize the start and end textboxes based on a file object"""
        fps_float = float(file_object["fps"]["num"]) / float(file_object["fps"]["den"])

        self.txtStartFrame.setMaximum(int(file_object["video_length"]))
        if 'start' not in file_object.keys():
            self.txtStartFrame.setValue(1)
        else:
            self.txtStartFrame.setValue(round(float(file_object["start"]) * fps_float) + 1)

        self.txtEndFrame.setMaximum(int(file_object["video_length"]))
        if 'end' not in file_object.keys():
            self.txtEndFrame.setValue(int(file_object["video_length"]))
        else:
            
            
            self.txtEndFrame.setValue(round(float(file_object["end"]) * fps_float))

    def verifyPath(self, new_path):
        """If the path has changed, verify that path is valid, and
        update duration, video_length, media_type, etc..."""

        
        seq_info = get_app().window.files_model.get_image_sequence_details(new_path)
        get_app().window.files_model.ignore_image_sequence_paths = []

        
        if seq_info:
            
            new_path = seq_info.get("path")
            self.file.data["media_type"] = "video"

        
        clip = smartedit.Clip(new_path)
        if clip and clip.info.duration > 0.0:
            
            self.txtFilePath.setText(new_path)
            self.txtFileName.setText(os.path.basename(new_path))
            self.file.data = json.loads(clip.Reader().Json())
            if not seq_info:
                self.file.data["media_type"] = get_media_type(self.file.data)

            
            self.init_start_end_textboxes(self.file.data)
        else:
            log.info(f"Given path '{new_path}' was not a valid path... ignoring")

    def browsePath(self):
        
        app = get_app()
        _ = app._tr

        starting_folder, filename = os.path.split(self.file.data["path"])
        new_path = QFileDialog.getOpenFileName(None, _("Locate media file: %s") % filename, starting_folder)[0]

        
        if new_path:
            
            self.verifyPath(new_path)

            
            self.initialize()

    def accept(self):
        new_path = self.txtFilePath.text()
        if new_path and self.file.data.get("path") != new_path:
            
            self.verifyPath(new_path)

        
        self.file.data["name"] = self.txtFileName.text()
        self.file.data["tags"] = self.txtTags.text()
        
        
        fps_float = self.txtFrameRateNum.value() / self.txtFrameRateDen.value()
        if self.file.data["fps"]["num"] != self.txtFrameRateNum.value() or \
                self.file.data["fps"]["den"] != self.txtFrameRateDen.value():
            original_fps_float = float(self.file.data["fps"]["num"]) / float(self.file.data["fps"]["den"])
            
            self.file.data["fps"]["num"] = self.txtFrameRateNum.value()
            self.file.data["fps"]["den"] = self.txtFrameRateDen.value()
            self.file.data["video_timebase"]["num"] = self.txtFrameRateDen.value()
            self.file.data["video_timebase"]["den"] = self.txtFrameRateNum.value()

            
            fps_diff = original_fps_float / fps_float
            self.file.data["duration"] *= fps_diff
            if "start" in self.file.data:
                self.file.data["start"] *= fps_diff
            if "end" in self.file.data:
                self.file.data["end"] *= fps_diff

        
        elif self.txtStartFrame.value() != 1 or self.txtEndFrame.value() != int(self.file.data["video_length"]):
            
            self.file.data["start"] = (self.txtStartFrame.value() - 1) / fps_float
            
            self.file.data["end"] = self.txtEndFrame.value() / fps_float

        
        tid = str(uuid4())
        get_app().updates.transaction_id = tid

        
        self.file.save()

        
        get_app().window.FileUpdated.emit(self.file.id)

        
        for clip in Clip.filter(file_id=self.file.id):
            clip.data["reader"] = self.file.data
            clip.data["duration"] = self.file.data["duration"]
            if clip.data["end"] > clip.data["duration"]:
                clip.data["end"] = clip.data["duration"]
            clip.save()

            
            thumbnail_frame = (clip.data["start"] * fps_float) + 1
            get_app().window.ThumbnailUpdated.emit(clip.id, thumbnail_frame)

        
        get_app().updates.transaction_id = None

        
        super(FileProperties, self).accept()

    def reject(self):

        
        super(FileProperties, self).reject()
