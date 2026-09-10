"""
 @file
 @brief This file loads the Video Export dialog (i.e where is all preferences)
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
import copy
import functools
import locale
import os
import time
import tempfile
import math

import smartedit


try:
    from defusedxml import minidom as xml
except ImportError:
    from xml.dom import minidom as xml

from xml.parsers.expat import ExpatError

from qt_api import Qt, QCoreApplication, QTimer, QSize, QPoint, pyqtSignal, pyqtSlot
from qt_api import (
    QMessageBox, QDialog, QFileDialog, QDialogButtonBox, QPushButton, QWidget, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    location_file_dialog_options,
)
from qt_api import QIcon
from functools import partial
from classes import info, tabstops
from classes import ui_util
from classes import smartedit_rc  
from classes.logger import log
from classes.app import get_app
from classes.metrics import track_metric_screen, track_metric_error
from classes.query import File

import json

MAX_FPS_SPINBOX_VALUE = 2147483647


class Export(QDialog):
    """ Export Dialog """

    
    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'export.ui')

    ExportStarted = pyqtSignal(str, int, int)
    ExportFrame = pyqtSignal(str, int, int, int, str)
    ExportEnded = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
        ui_util.load_ui(self, self.ui_path)
        ui_util.init_ui(self)
        self._setup_toolbox_tab_order()
        self.exportTabs.tabBar().setFocusPolicy(Qt.StrongFocus)

        
        _ = get_app()._tr
        self.s = get_app().get_settings()

        track_metric_screen("export-screen")

        
        self.settings_data = self.s.get_all_settings()

        
        self.cancel_button = QPushButton(_('Cancel'))
        self.cancel_button.setObjectName("cancelButton")
        self.export_button = QPushButton(_('Export Video'))
        self.export_button.setObjectName("acceptButton")
        self.close_button = QPushButton(_('Done'))
        self.restoring_defaults = False
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

        self.buttonBox.addButton(self.close_button, QDialogButtonBox.RejectRole)
        self.buttonBox.addButton(self.export_button, QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.close_button.setVisible(False)
        self.exporting = False
        self.vbr = {}
        self.abr = {}

        
        get_app().window.PauseSignal.emit()

        
        self.lblChannels.setVisible(False)
        self.txtChannels.setVisible(False)

        
        smartedit.Settings.Instance().HIGH_QUALITY_SCALING = True

        
        self.project = copy.deepcopy(get_app().project)

        
        self.old_cache_object = None
        project_timeline = get_app().window.timeline_sync.timeline
        if get_app().window.cache_object:
            self.old_cache_object = get_app().window.cache_object
            get_app().window.cache_object = smartedit.CacheMemory(1 * 1024 * 1024) 
            project_timeline.SetCache(get_app().window.cache_object)
            self.old_cache_object.Clear()

        
        self.cache_thread = smartedit.VideoCacheThread()

        
        width = int(project_timeline.info.width)
        height = int(project_timeline.info.height)
        fps = project_timeline.info.fps
        sample_rate = int(project_timeline.info.sample_rate)
        channels = int(project_timeline.info.channels)
        channel_layout = int(project_timeline.info.channel_layout)

        
        self.timeline = smartedit.Timeline(
            width, height, smartedit.Fraction(fps.num, fps.den),
            sample_rate, channels, channel_layout)
        
        self.timeline.info.sample_rate = sample_rate
        self.timeline.info.channels = channels
        self.timeline.info.channel_layout = channel_layout
        self.timeline.info.has_audio = project_timeline.info.has_audio
        self.timeline.info.has_video = project_timeline.info.has_video
        self.timeline.info.video_length = project_timeline.info.video_length
        self.timeline.info.duration = project_timeline.info.duration

        
        try:
            json_timeline = json.dumps(self.project._data)
            self.timeline.SetJson(json_timeline)
        except Exception as ex:
            msg = QMessageBox()
            msg.setWindowTitle(_("Project Data Error"))
            msg.setText(_("Sorry, an error was encountered while parsing your project data: \n'%(error)s'.\n\n"
                          "Please save your project and inspect in a JSON editor to repair." %
                          {"error": str(ex)}))
            msg.exec_()
            return

        
        self.timeline.Open()

        
        recommended_path = self.s.getDefaultPath(self.s.actionType.EXPORT)
        self.txtExportFolder.setText(recommended_path)

        
        if not get_app().project.current_filepath:
            
            self.txtFileName.setText(_("Untitled Project"))
        else:
            
            
            filename = os.path.basename(get_app().project.current_filepath)
            filename = os.path.splitext(filename)[0]
            self.txtFileName.setText(filename)

        
        self.txtImageFormat.setText("-%05d.png")

        
        export_options = [_("Video & Audio"), _("Video Only"), _("Audio Only"), _("Image Sequence")]
        for option in export_options:
            
            self.cboExportTo.addItem(option)

        
        self.channel_layout_choices = []
        for layout in [(smartedit.LAYOUT_MONO, _("Mono (1 Channel)")),
                       (smartedit.LAYOUT_STEREO, _("Stereo (2 Channel)")),
                       (smartedit.LAYOUT_SURROUND, _("Surround (3 Channel)")),
                       (smartedit.LAYOUT_5POINT1, _("Surround (5.1 Channel)")),
                       (smartedit.LAYOUT_7POINT1, _("Surround (7.1 Channel)"))]:
            log.info(layout)
            self.channel_layout_choices.append(layout[0])
            self.cboChannelLayout.addItem(layout[1], layout[0])

        self.txtFrameRateNum.setMaximum(MAX_FPS_SPINBOX_VALUE)
        self.txtFrameRateDen.setMaximum(MAX_FPS_SPINBOX_VALUE)

        
        self.btnBrowse.clicked.connect(functools.partial(self.btnBrowse_clicked))
        self.cboSimpleProjectType.currentIndexChanged.connect(
            functools.partial(self.cboSimpleProjectType_index_changed, self.cboSimpleProjectType))
        self.cboProfile.currentIndexChanged.connect(functools.partial(self.cboProfile_index_changed, self.cboProfile))
        self.cboSimpleTarget.currentIndexChanged.connect(
            functools.partial(self.cboSimpleTarget_index_changed, self.cboSimpleTarget))
        self.cboSimpleVideoProfile.currentIndexChanged.connect(
            functools.partial(self.cboSimpleVideoProfile_index_changed, self.cboSimpleVideoProfile))
        self.cboSimpleQuality.currentIndexChanged.connect(
            functools.partial(self.cboSimpleQuality_index_changed, self.cboSimpleQuality))
        self.cboChannelLayout.currentIndexChanged.connect(self.updateChannels)
        self.ExportFrame.connect(self.updateProgressBar)
        self.btnBrowseProfiles.clicked.connect(self.btnBrowseProfiles_clicked)
        self.checkStartFirstClip.toggled.connect(partial(self.updateFrameRate, True))
        self.checkEndLastClip.toggled.connect(partial(self.updateFrameRate, True))

        
        
        self.profile_names = []
        self.profile_paths = {}
        self.current_project_profile = get_app().project.get(['profile'])
        self.selected_profile = None
        for profile_folder in [info.USER_PROFILES_PATH, info.PROFILES_PATH]:
            for file in reversed(sorted(os.listdir(profile_folder))):
                profile_path = os.path.join(profile_folder, file)
                if os.path.isdir(profile_path):
                    continue
                try:
                    
                    profile = smartedit.Profile(profile_path)

                    
                    profile_name = f"{profile.info.description} ({profile.info.width}x{profile.info.height})"
                    self.profile_names.append(profile_name)
                    self.profile_paths[profile_name] = profile_path

                    
                    self.cboProfile.addItem(
                        self.getProfileName(self.getProfilePath(profile_name)), self.getProfilePath(profile_name))

                    
                    if self.current_project_profile == profile.info.description:
                        self.selected_profile = profile_name

                except RuntimeError as e:
                    
                    log.error("Failed to parse file '%s' as a profile: %s" % (profile_path, e))

        
        
        presets = []

        for preset_folder in [info.EXPORT_PRESETS_PATH, info.USER_PRESETS_PATH]:
            for file in os.listdir(preset_folder):
                preset_path = os.path.join(preset_folder, file)
                try:
                    xmldoc = xml.parse(preset_path)
                    type = xmldoc.getElementsByTagName("type")
                    presets.append(_(type[0].childNodes[0].data))

                except ExpatError as e:
                    
                    log.error("Failed to parse file '%s' as a preset: %s" % (preset_path, e))

        
        all_formats_text = _("All Formats")
        self.cboSimpleProjectType.addItem(all_formats_text, all_formats_text)

        
        presets = list(set(presets))
        for item in sorted(presets):
            if item != all_formats_text:
                self.cboSimpleProjectType.addItem(item, item)

        
        self.cboSimpleProjectType.setCurrentIndex(0)

        
        self.populateAllProfiles(get_app().project.get(['profile']))

        
        self.txtFrameRateNum.valueChanged.connect(self.updateFrameRate)
        self.txtFrameRateDen.valueChanged.connect(self.updateFrameRate)
        self.txtWidth.valueChanged.connect(self.updateFrameRate)
        self.txtHeight.valueChanged.connect(self.updateFrameRate)
        self.txtSampleRate.valueChanged.connect(self.updateFrameRate)
        self.txtChannels.valueChanged.connect(self.updateFrameRate)
        self.cboChannelLayout.currentIndexChanged.connect(self.updateFrameRate)

        
        self.updateFrameRate()

        
        self.load_settings()

        self.exportTabs.currentChanged.connect(self._apply_tab_order)
        self.toolBox.currentChanged.connect(self._apply_tab_order)
        self._apply_tab_order()
        self.txtFileName.setFocus()

    def _apply_tab_order(self):
        current_tab = self.exportTabs.currentWidget()
        if current_tab is None:
            current_tab = self.exportTabs.widget(self.exportTabs.currentIndex())
        if current_tab is None:
            return

        ordered = [
            self.txtFileName,
            self.txtExportFolder,
            self.btnBrowse,
            self.exportTabs,
        ]

        if current_tab is self.Advanced:
            tab_widgets = self._collect_toolbox_tab_order(self.toolBox)
        else:
            tab_widgets = tabstops.collect_focusable_from_layout(
                current_tab.layout(), self, include_hidden=True
            )

        ordered.extend(tab_widgets)

        ordered.extend(
            [
                self.restore_defaults_button,
                self.cancel_button,
                self.export_button,
                self.close_button,
            ]
        )

        def _apply_and_wrap():
            ordered_unique = []
            seen = set()
            for widget in ordered:
                if widget is None or widget in seen:
                    continue
                ordered_unique.append(widget)
                seen.add(widget)

            for first, second in zip(ordered_unique, ordered_unique[1:]):
                tabstops.safe_set_tab_order(first, second)

            
            first_visible = ordered_unique[0] if ordered_unique else None
            for last_visible in reversed(ordered_unique):
                if last_visible.isVisibleTo(self) and last_visible.isEnabled():
                    break
            else:
                last_visible = None

            if first_visible and last_visible:
                tabstops.safe_set_tab_order(last_visible, first_visible)

            self._tab_order_list = [
                w for w in ordered_unique
                if w.isVisibleTo(self) and w.isEnabled() and w.focusPolicy() != Qt.NoFocus
            ]

        QTimer.singleShot(0, _apply_and_wrap)

    def restore_defaults(self):
        """
        Restore defaults by closing and reopening the dialog.
        """
        
        get_app().updates.ignore_history = True
        get_app().updates.update(["export_settings"], None)
        get_app().updates.ignore_history = False

        log.info("Cleared last-export_settings.")

        
        self.restoring_defaults = True
        self.close()

        
        QTimer.singleShot(0, get_app().window.actionExportVideo.trigger)

    def getProfilePath(self, profile_name):
        """Get the profile path that matches the name"""
        for profile, path in self.profile_paths.items():
            if profile_name in profile:
                return path

    def getProfileName(self, profile_path):
        """Get the profile name that matches the name"""
        for profile, path in self.profile_paths.items():
            if profile_path == path:
                return profile

    @pyqtSlot(str, int, int, int, str)
    def updateProgressBar(self, title_message, start_frame, end_frame, current_frame, format_of_progress_string):
        """Update progress bar during exporting"""
        if end_frame - start_frame > 0:
            percentage_string = format_of_progress_string % (( current_frame - start_frame ) / ( end_frame - start_frame ) * 100)
        else:
            percentage_string = "100%"
        self.progressExportVideo.setValue(int(current_frame))
        self.progressExportVideo.setFormat(percentage_string)
        self.setWindowTitle("%s %s" % (percentage_string, title_message))

    def updateChannels(self, *_args):
        """Update the # of channels to match the channel layout"""
        log.info("updateChannels")
        channels = self.txtChannels.value()
        channel_layout = self.cboChannelLayout.currentData()

        if channel_layout == smartedit.LAYOUT_MONO:
            channels = 1
        elif channel_layout == smartedit.LAYOUT_STEREO:
            channels = 2
        elif channel_layout == smartedit.LAYOUT_SURROUND:
            channels = 3
        elif channel_layout == smartedit.LAYOUT_5POINT1:
            channels = 6
        elif channel_layout == smartedit.LAYOUT_7POINT1:
            channels = 8

        
        self.txtChannels.setValue(channels)

    def updateFrameRate(self, *args, set_limits=True):
        """Callback for changing the frame rate"""
        
        
        if args and isinstance(args[0], bool):
            set_limits = args[0]
            args = args[1:]
        elif not isinstance(set_limits, bool):
            set_limits = True

        self.update_frame_rate_display()

        
        self.timeline.info.width = self.txtWidth.value()
        self.timeline.info.height = self.txtHeight.value()
        self.timeline.info.fps.num = self.txtFrameRateNum.value()
        self.timeline.info.fps.den = self.txtFrameRateDen.value()
        self.timeline.info.sample_rate = self.txtSampleRate.value()
        self.timeline.info.channels = self.txtChannels.value()
        self.timeline.info.channel_layout = self.cboChannelLayout.currentData()

        
        if self.timeline.info.sample_rate == 0 or self.timeline.info.channels == 0:
            self.timeline.info.has_audio = False
        else:
            self.timeline.info.has_audio = True

        if set_limits:
            if self.checkEndLastClip.isChecked():
                
                timeline_length_int = self.timeline.GetMaxFrame()
            else:
                
                timeline_length_int = self.timeline.info.video_length

            if self.checkStartFirstClip.isChecked():
                
                timeline_start_int = self.timeline.GetMinFrame()
            else:
                
                timeline_start_int = 1

            
            self.txtStartFrame.setValue(timeline_start_int)
            self.txtEndFrame.setValue(timeline_length_int)

        
        current_fps = get_app().project.get("fps")
        current_fps_float = float(current_fps["num"]) / float(current_fps["den"])
        new_fps_float = float(self.txtFrameRateNum.value()) / float(self.txtFrameRateDen.value())
        self.export_fps_factor = new_fps_float / current_fps_float
        self.original_fps_factor = current_fps_float / new_fps_float

    def update_frame_rate_display(self):
        """Show the current FPS fraction as a calculated float."""
        fps_den = self.txtFrameRateDen.value() or 1
        fps_float = self.txtFrameRateNum.value() / fps_den
        self.lblFrameRateValueDisplay.setText(f"= {fps_float:.2f}")

    def cboSimpleProjectType_index_changed(self, widget, index):
        selected_project = widget.itemData(index)

        
        
        self.cboSimpleTarget.clear()

        
        _ = get_app()._tr

        
        project_types = []
        acceleration_types = {}
        for preset_folder in [info.EXPORT_PRESETS_PATH, info.USER_PRESETS_PATH]:
            for file in os.listdir(preset_folder):
                preset_path = os.path.join(preset_folder, file)
                try:
                    xmldoc = xml.parse(preset_path)
                    type = xmldoc.getElementsByTagName("type")

                    if _(type[0].childNodes[0].data) == selected_project:
                        titles = xmldoc.getElementsByTagName("title")
                        videocodecs = xmldoc.getElementsByTagName("videocodec")
                        for title in titles:
                            project_types.append(_(title.childNodes[0].data))
                        for codec in videocodecs:
                            codec_text = ""
                            if codec.childNodes:
                                codec_text = codec.childNodes[0].data
                            if "vaapi" in codec_text and smartedit.FFmpegWriter.IsValidCodec(codec_text):
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-vaapi.svg")
                            elif "nvenc" in codec_text and smartedit.FFmpegWriter.IsValidCodec(codec_text):
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-nvenc.svg")
                            elif "dxva2" in codec_text and smartedit.FFmpegWriter.IsValidCodec(codec_text):
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-dx.svg")
                            elif "videotoolbox" in codec_text and smartedit.FFmpegWriter.IsValidCodec(codec_text):
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-vtb.svg")
                            elif "qsv" in codec_text and smartedit.FFmpegWriter.IsValidCodec(codec_text):
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-qsv.svg")
                            elif smartedit.FFmpegWriter.IsValidCodec(codec_text) or codec_text == "":
                                acceleration_types[_(title.childNodes[0].data)] = QIcon(":/hw/hw-accel-none.svg")

                except ExpatError as e:
                    
                    log.error("Failed to parse file '%s' as a preset: %s" % (preset_path, e))

                
                xmldoc.unlink()

        
        preset_index = 0
        selected_preset = 0
        for item in sorted(project_types):
            icon = acceleration_types.get(item)
            if icon:
                self.cboSimpleTarget.setIconSize(QSize(60, 18))
                self.cboSimpleTarget.addItem(icon, item, item)
            else:
                continue

            
            if item == _("MP4 (h.264)"):
                selected_preset = preset_index

            preset_index += 1

        
        self.cboSimpleTarget.setCurrentIndex(selected_preset)

    def cboProfile_index_changed(self, widget, index):
        selected_profile_path = widget.itemData(index)
        log.info(selected_profile_path)

        
        _ = get_app()._tr

        
        profile = smartedit.Profile(selected_profile_path)

        
        self.txtWidth.setValue(profile.info.width)
        self.txtHeight.setValue(profile.info.height)
        self.txtFrameRateDen.setValue(profile.info.fps.den)
        self.txtFrameRateNum.setValue(profile.info.fps.num)
        self.txtAspectRatioNum.setValue(profile.info.display_ratio.num)
        self.txtAspectRatioDen.setValue(profile.info.display_ratio.den)
        self.txtPixelRatioNum.setValue(profile.info.pixel_ratio.num)
        self.txtPixelRatioDen.setValue(profile.info.pixel_ratio.den)

        
        self.cboInterlaced.clear()
        self.cboInterlaced.addItem(_("No"), "No")
        self.cboInterlaced.addItem(_("Yes Top field first"), "Yes")
        self.cboInterlaced.addItem(_("Yes Bottom field first"), "Yes")
        if profile.info.interlaced_frame:
            self.cboInterlaced.setCurrentIndex(1)
        else:
            self.cboInterlaced.setCurrentIndex(0)

        
        self.cboSpherical.clear()
        self.cboSpherical.addItem(_("No"), 0)
        self.cboSpherical.addItem(_("Yes"), 1)
        if hasattr(profile.info, "spherical") and profile.info.spherical:
            self.cboSpherical.setCurrentIndex(1)
        else:
            self.cboSpherical.setCurrentIndex(0)

        self.update_all_formats_bitrates()

    def cboSimpleTarget_index_changed(self, widget, index):
        selected_target = widget.itemData(index)
        log.info(selected_target)

        
        _ = get_app()._tr

        
        if selected_target:
            profiles_list = []
            v_l = v_m = v_h = a_l = a_m = a_h = None

            
            previous_quality = self.cboSimpleQuality.currentIndex()
            if previous_quality < 0:
                previous_quality = self.cboSimpleQuality.count() - 1
            previous_profile = self.cboSimpleVideoProfile.currentText()
            if previous_profile:
                self.selected_profile = previous_profile
            self.cboSimpleVideoProfile.clear()
            self.cboSimpleQuality.clear()

            
            profile_index = 0
            all_profiles = False
            for preset_folder in [info.EXPORT_PRESETS_PATH, info.USER_PRESETS_PATH]:
                for file in os.listdir(preset_folder):
                    preset_path = os.path.join(preset_folder, file)
                    try:
                        xmldoc = xml.parse(preset_path)
                        title = xmldoc.getElementsByTagName("title")
                        if _(title[0].childNodes[0].data) == selected_target:
                            profiles = xmldoc.getElementsByTagName("projectprofile")

                            
                            all_profiles = False
                            if profiles:
                                
                                self.btnBrowseProfiles.setEnabled(False)

                                
                                for profile in profiles:
                                    profiles_list.append(_(profile.childNodes[0].data))
                                profiles_list = sorted(profiles_list)
                            else:
                                
                                all_profiles = True

                                
                                self.btnBrowseProfiles.setEnabled(True)
                                for profile_name in self.profile_names:
                                    profiles_list.append(profile_name)

                            
                            
                            
                            export_to_options = [_("Video & Audio"), _("Video Only"),
                                                 _("Audio Only"), _("Image Sequence")]
                            export_to = export_to_options[0]
                            if xmldoc.getElementsByTagName("export-to"):
                                export_to = _(xmldoc.getElementsByTagName("export-to")[0].childNodes[0].data)
                            if export_to in export_to_options:
                                self.cboExportTo.setCurrentIndex(export_to_options.index(export_to))

                            
                            videobitrate = xmldoc.getElementsByTagName("videobitrate")
                            for rate in videobitrate:
                                v_l = rate.attributes["low"].value
                                v_m = rate.attributes["med"].value
                                v_h = rate.attributes["high"].value
                                self.vbr = {_("Low"): v_l, _("Med"): v_m, _("High"): v_h}

                            
                            audiobitrate = xmldoc.getElementsByTagName("audiobitrate")
                            for audiorate in audiobitrate:
                                a_l = audiorate.attributes["low"].value
                                a_m = audiorate.attributes["med"].value
                                a_h = audiorate.attributes["high"].value
                                self.abr = {_("Low"): a_l, _("Med"): a_m, _("High"): a_h}

                            
                            vf = xmldoc.getElementsByTagName("videoformat")
                            self.txtVideoFormat.setText(vf[0].childNodes[0].data)
                            vc = xmldoc.getElementsByTagName("videocodec")
                            if vc[0].childNodes:
                                self.txtVideoCodec.setText(vc[0].childNodes[0].data)
                            else:
                                self.txtVideoCodec.setText("")
                            sr = xmldoc.getElementsByTagName("samplerate")
                            self.txtSampleRate.setValue(int(sr[0].childNodes[0].data))
                            c = xmldoc.getElementsByTagName("audiochannels")
                            self.txtChannels.setValue(int(c[0].childNodes[0].data))
                            c = xmldoc.getElementsByTagName("audiochannellayout")

                            
                            ac = xmldoc.getElementsByTagName("audiocodec")
                            if ac[0].childNodes:
                                audio_codec_name = ac[0].childNodes[0].data
                                if audio_codec_name == "aac":
                                    
                                    if smartedit.FFmpegWriter.IsValidCodec("libfaac"):
                                        self.txtAudioCodec.setText("libfaac")
                                    elif smartedit.FFmpegWriter.IsValidCodec("libvo_aacenc"):
                                        self.txtAudioCodec.setText("libvo_aacenc")
                                    elif smartedit.FFmpegWriter.IsValidCodec("aac"):
                                        self.txtAudioCodec.setText("aac")
                                    else:
                                        
                                        self.txtAudioCodec.setText("ac3")
                                else:
                                    
                                    self.txtAudioCodec.setText(audio_codec_name)
                            else:
                                
                                self.txtAudioCodec.setText("")

                            for layout_index, layout in enumerate(self.channel_layout_choices):
                                if layout == int(c[0].childNodes[0].data):
                                    self.cboChannelLayout.setCurrentIndex(layout_index)
                                    break

                        
                        xmldoc.unlink()

                    except ExpatError as e:
                        
                        log.error("Failed to parse file '%s' as a preset: %s" % (preset_path, e))

            
            for item in profiles_list:
                self.cboSimpleVideoProfile.addItem(
                    self.getProfileName(self.getProfilePath(item)), self.getProfilePath(item))

            
            profile_index = self.getVideoProfileIndex(self.selected_profile)
            if profile_index != -1:
                
                self.cboSimpleVideoProfile.setCurrentIndex(profile_index)
            else:
                
                
                self.cboSimpleVideoProfile.setCurrentIndex(0)

            
            
            if v_l or a_l:
                self.cboSimpleQuality.addItem(_("Low"), "Low")
            if v_m or a_m:
                self.cboSimpleQuality.addItem(_("Med"), "Med")
            if v_h or a_h:
                self.cboSimpleQuality.addItem(_("High"), "High")

            
            self.update_all_formats_bitrates()

            
            if previous_quality <= self.cboSimpleQuality.count() - 1:
                self.cboSimpleQuality.setCurrentIndex(previous_quality)
            else:
                self.cboSimpleQuality.setCurrentIndex(self.cboSimpleQuality.count() - 1)

    def getVideoProfileIndex(self, profile_name=None, profile_key=None):
        """Get the index of a profile name or profile key (-1 if not found)"""
        if profile_name:
            for index in range(self.cboSimpleVideoProfile.count()):
                combo_profile = self.cboSimpleVideoProfile.itemText(index)
                if combo_profile == profile_name:
                    return index
            return -1
        if profile_key:
            for index in range(self.cboSimpleVideoProfile.count()):
                combo_profile_path = self.cboSimpleVideoProfile.itemData(index)
                combo_profile = smartedit.Profile(combo_profile_path)
                if combo_profile.Key() == profile_key:
                    return index
            return -1

    def cboSimpleVideoProfile_index_changed(self, widget, index):
        selected_profile_path = widget.itemData(index)
        log.info(selected_profile_path)

        
        self.populateAllProfiles(selected_profile_path)
        self.update_all_formats_bitrates()

    def populateAllProfiles(self, selected_profile_path):
        """Populate the full list of profiles"""
        
        for profile_index, profile_name in enumerate(self.profile_names):
            
            if self.getProfilePath(profile_name) == selected_profile_path:
                
                self.cboProfile.setCurrentIndex(profile_index)
                break

    def cboSimpleQuality_index_changed(self, widget, index):
        selected_quality = widget.itemData(index)
        log.info(selected_quality)

        
        _ = get_app()._tr

        
        self.update_all_formats_bitrates()

        
        if selected_quality:
            self.txtVideoBitRate.setText(_(self.vbr[_(selected_quality)]))
            self.txtAudioBitrate.setText(_(self.abr[_(selected_quality)]))

    def btnBrowse_clicked(self):
        log.info("btnBrowse_clicked")

        
        _ = get_app()._tr
        default_path = self.s.getDefaultPath(self.s.actionType.EXPORT)

        
        options = location_file_dialog_options()
        if options is None:
            file_path = QFileDialog.getExistingDirectory(
                self, _("Choose a Folder..."), default_path)
        else:
            file_path = QFileDialog.getExistingDirectory(
                self, _("Choose a Folder..."), default_path, options=options)

        
        if os.path.exists(file_path):
            self.s.setDefaultPath(self.s.actionType.EXPORT, file_path)
            self.txtExportFolder.setText(file_path)

    def btnBrowseProfiles_clicked(self):
        """Search profile button clicked"""
        
        current_profile = smartedit.Profile(self.cboSimpleVideoProfile.currentData())

        
        from windows.profile import Profile
        log.debug("Showing profile dialog")
        win = Profile(current_profile.Key())
        
        result = win.exec_()

        profile = win.selected_profile
        if result == QDialog.Accepted and profile:

            
            profile_index = self.getVideoProfileIndex(profile_key=profile.Key())
            if profile_index != -1:
                
                self.cboSimpleVideoProfile.setCurrentIndex(profile_index)
            else:
                
                
                self.cboSimpleVideoProfile.setCurrentIndex(0)

    def convert_to_bytes(self, BitRateString):
        bit_rate_bytes = 0

        
        s = BitRateString.lower().split(" ")
        measurement = "kb"

        try:
            
            if len(s) >= 2:
                raw_number_string = s[0]
                raw_measurement = s[1]

                
                raw_number = locale.atof(raw_number_string)

                if "kb" in raw_measurement:
                    
                    bit_rate_bytes = raw_number * 1000.0

                elif "mb" in raw_measurement:
                    
                    bit_rate_bytes = raw_number * 1000.0 * 1000.0

                elif ("crf" in raw_measurement) or ("cqp" in raw_measurement):
                    
                    if raw_number > 63:
                        raw_number = 63
                    if raw_number < 0:
                        raw_number = 0
                    bit_rate_bytes = raw_number

                elif "qp" in raw_measurement:
                    
                    if raw_number > 255:
                        raw_number = 255
                    if raw_number < 0:
                        raw_number = 0
                    bit_rate_bytes = raw_number

        except:
            log.warning('Failed to convert bitrate string to bytes: %s' % BitRateString)

        
        return str(int(bit_rate_bytes))

    def disableControls(self):
        """Disable all controls"""
        self.lblFileName.setEnabled(False)
        self.txtFileName.setEnabled(False)
        self.lblFolderPath.setEnabled(False)
        self.txtExportFolder.setEnabled(False)
        self.exportTabs.setEnabled(False)
        self.export_button.setEnabled(False)
        self.btnBrowse.setEnabled(False)

    def enableControls(self):
        """Enable all controls"""
        self.lblFileName.setEnabled(True)
        self.txtFileName.setEnabled(True)
        self.lblFolderPath.setEnabled(True)
        self.txtExportFolder.setEnabled(True)
        self.exportTabs.setEnabled(True)
        self.export_button.setEnabled(True)
        self.btnBrowse.setEnabled(True)

    def _setup_toolbox_tab_order(self):
        toolbox = self.toolBox
        toolbox.setFocusPolicy(Qt.NoFocus)

        for child in toolbox.findChildren(QWidget):
            if child.metaObject().className() == "QToolBoxButton":
                child.setFocusPolicy(Qt.TabFocus)

    def focusNextPrevChild(self, forward):
        tab_list = getattr(self, "_tab_order_list", None)
        if not tab_list:
            return super().focusNextPrevChild(forward)

        current = self.focusWidget()
        if current is self.exportTabs.tabBar():
            current = self.exportTabs

        if current not in tab_list:
            target = tab_list[0] if forward else tab_list[-1]
            if target is self.exportTabs:
                self.exportTabs.tabBar().setFocus()
            else:
                target.setFocus()
            return True

        index = tab_list.index(current)
        if forward:
            index = (index + 1) % len(tab_list)
        else:
            index = (index - 1) % len(tab_list)
        target = tab_list[index]
        if target is self.exportTabs:
            self.exportTabs.tabBar().setFocus()
        else:
            target.setFocus()
        return True

    def _collect_toolbox_tab_order(self, toolbox):
        if toolbox is None:
            return []

        buttons = []
        for child in toolbox.findChildren(QWidget):
            if child.metaObject().className() == "QToolBoxButton":
                buttons.append(child)

        if not buttons:
            return []

        buttons.sort(key=lambda button: button.pos().y())
        ordered = []
        current_index = toolbox.currentIndex()

        for index, button in enumerate(buttons):
            ordered.append(button)
            if index != current_index:
                continue
            page = toolbox.widget(index)
            page_widgets = tabstops.collect_focusable_from_layout(
                page.layout(), self, include_hidden=True
            )
            ordered.extend(self._sort_widgets_by_position(page_widgets))

        return ordered

    def _sort_widgets_by_position(self, widgets):
        if not widgets:
            return []

        def _pos_key(widget):
            try:
                pos = widget.mapTo(self, QPoint(0, 0))
                return (pos.y(), pos.x())
            except Exception:
                return (0, 0)

        return sorted(widgets, key=_pos_key)

    def accept(self):
        """ Start exporting video """
        
        self.save_settings()

        
        def titlestring(sec, fps, mess):
            formatstr = "%(hours)d:%(minutes)02d:%(seconds)02d " + mess + " (%(fps)5.2f FPS)"
            title_mes = _(formatstr) % {
                'hours': sec / 3600,
                'minutes': (sec / 60) % 60,
                'seconds': sec % 60,
                'fps': fps}
            return title_mes

        
        _ = get_app()._tr

        
        seconds_run = 0
        fps_encode = 0

        
        self.progressExportVideo.setMinimum(int(self.txtStartFrame.value()))
        self.progressExportVideo.setMaximum(int(self.txtEndFrame.value()))
        self.progressExportVideo.setValue(int(self.txtStartFrame.value()))

        
        if self.txtStartFrame.value() == self.txtEndFrame.value():
            msg = QMessageBox()
            msg.setWindowTitle(_("Export Error"))
            msg.setText(_("Sorry, please select a valid range of frames to export"))
            msg.exec_()

            
            self.enableControls()
            self.exporting = False
            return

        
        self.disableControls()
        self.exporting = True

        
        
        export_type = self.cboExportTo.currentText()

        
        default_filename = "Untitled Project"
        default_folder = os.path.join(info.HOME_PATH)
        if export_type == _("Image Sequence"):
            file_name_with_ext = "%s%s" % (self.txtFileName.text().strip() or default_filename, self.txtImageFormat.text().strip())
        else:
            file_ext = self.txtVideoFormat.text().strip()
            file_name_with_ext = self.txtFileName.text().strip() or default_filename
            
            if not file_name_with_ext.endswith(file_ext):
                file_name_with_ext = '{}.{}'.format(file_name_with_ext, file_ext)

        
        folder_path = self.txtExportFolder.text().lstrip()
        if folder_path and not os.path.isdir(folder_path):
            log.debug("Folder path does not exist. Removing trailing whitespace.")
            if os.path.isdir(folder_path.rstrip()):
                log.debug("Directory %s does exist. Using it instead." % folder_path)
                folder_path = folder_path.rstrip()

        export_file_path = os.path.join(folder_path or default_folder, file_name_with_ext)
        log.info("Export path: %s" % export_file_path)

        
        try:
            open(os.path.join(tempfile.gettempdir(), file_name_with_ext), 'w')
        except OSError:
            
            file_name_with_ext = "%s.%s" % (default_filename, self.txtVideoFormat.text().strip())
            export_file_path = os.path.join(self.txtExportFolder.text().strip() or default_folder, file_name_with_ext)
            log.info("Invalid export path detected, changing to: %s" % export_file_path)

        file = File.get(path=export_file_path)
        if file:
            ret = QMessageBox.question(self,
                _("Export Video"),
                _("%s is an input file.\nPlease choose a different name.") % file_name_with_ext,
                QMessageBox.Ok)
            self.enableControls()
            self.exporting = False
            return

        
        if os.path.exists(export_file_path) and export_type in [_("Video & Audio"), _("Video Only"), _("Audio Only")]:
            
            ret = QMessageBox.question(self,
                _("Export Video"),
                _("%s already exists.\nDo you want to replace it?") % file_name_with_ext,
                QMessageBox.No | QMessageBox.Yes)
            if ret == QMessageBox.No:
                
                
                self.enableControls()
                self.exporting = False
                return

        
        interlacedIndex = self.cboInterlaced.currentIndex()
        sphericalIndex = self.cboSpherical.currentIndex()
        video_settings = {  "vformat": self.txtVideoFormat.text(),
                            "vcodec": self.txtVideoCodec.text(),
                            "fps": { "num" : self.txtFrameRateNum.value(), "den": self.txtFrameRateDen.value()},
                            "width": self.txtWidth.value(),
                            "height": self.txtHeight.value(),
                            "pixel_ratio": {"num": self.txtPixelRatioNum.value(), "den": self.txtPixelRatioDen.value()},
                            "video_bitrate": int(self.convert_to_bytes(self.txtVideoBitRate.text())),
                            "start_frame": self.txtStartFrame.value(),
                            "end_frame": self.txtEndFrame.value(),
                            "interlace": interlacedIndex in [1, 2],
                            "topfirst": interlacedIndex == 1,
                            "spherical": sphericalIndex == 1
                          }

        audio_settings = {"acodec": self.txtAudioCodec.text(),
                          "sample_rate": self.txtSampleRate.value(),
                          "channels": self.txtChannels.value(),
                          "channel_layout": self.cboChannelLayout.currentData(),
                          "audio_bitrate": int(self.convert_to_bytes(self.txtAudioBitrate.text()))
                          }

        
        if export_type == _("Image Sequence"):
            image_ext = os.path.splitext(self.txtImageFormat.text().strip())[1].replace(".", "")
            video_settings["vformat"] = image_ext
            if image_ext in ["jpg", "jpeg"]:
                video_settings["vcodec"] = "mjpeg"
            else:
                video_settings["vcodec"] = image_ext

        
        settings = get_app().get_settings()
        settings.setDefaultPath(settings.actionType.EXPORT, export_file_path)
        
        get_app().project.has_unsaved_changes = True

        
        export_cache_object = smartedit.CacheMemory(250 * 1024 * 1024)
        self.timeline.SetCache(export_cache_object)

        
        if self.export_fps_factor != 1.0:
            
            self.project.rescale_keyframes(self.export_fps_factor)

            
            profile = smartedit.Profile(self.cboSimpleVideoProfile.currentData())
            self.project.apply_profile(profile)

            
            self.timeline.SetJson(json.dumps(self.project._data))

        
        self.updateFrameRate(set_limits=False)

        
        self.timeline.SetMaxSize(video_settings.get("width"), video_settings.get("height"))

        
        self.timeline.ApplyMapperToClips()

        
        max_frame = 0

        
        format_of_progress_string = "%4.1f%% "

        
        self.cache_thread.Reader(self.timeline)
        self.cache_thread.setSpeed(1)
        self.cache_thread.StartThread()

        
        try:
            w = smartedit.FFmpegWriter(export_file_path)

            
            if export_type in [_("Video & Audio"), _("Video Only"), _("Image Sequence")]:
                w.SetVideoOptions(True,
                                  video_settings.get("vcodec"),
                                  smartedit.Fraction(video_settings.get("fps").get("num"),
                                                    video_settings.get("fps").get("den")),
                                  video_settings.get("width"),
                                  video_settings.get("height"),
                                  smartedit.Fraction(video_settings.get("pixel_ratio").get("num"),
                                                    video_settings.get("pixel_ratio").get("den")),
                                  video_settings.get("interlace"),
                                  video_settings.get("topfirst"),
                                  video_settings.get("video_bitrate"))

            
            if export_type in [_("Video & Audio"), _("Audio Only")]:
                w.SetAudioOptions(True,
                                  audio_settings.get("acodec"),
                                  audio_settings.get("sample_rate"),
                                  audio_settings.get("channels"),
                                  audio_settings.get("channel_layout"),
                                  audio_settings.get("audio_bitrate"))

            
            w.PrepareStreams()

            
            if video_settings.get("spherical"):
                yaw = 0.0
                pitch = 0.0
                roll = 0.0
                w.AddSphericalMetadata("equirectangular", yaw, pitch, roll)

            
            
            
            if export_type in [_("Audio Only")]:
                
                w.SetOption(smartedit.AUDIO_STREAM, "muxing_preset", "mp4_faststart")
            else:
                
                w.SetOption(smartedit.VIDEO_STREAM, "muxing_preset", "mp4_faststart")
                
                if "crf" in self.txtVideoBitRate.text():
                    w.SetOption(smartedit.VIDEO_STREAM, "crf", str(int(video_settings.get("video_bitrate"))) )
                elif "cqp" in self.txtVideoBitRate.text():
                    w.SetOption(smartedit.VIDEO_STREAM, "cqp", str(int(video_settings.get("video_bitrate"))) )
                elif "qp" in self.txtVideoBitRate.text():
                    w.SetOption(smartedit.VIDEO_STREAM, "qp", str(int(video_settings.get("video_bitrate"))) )

                
                
                
                
                vcodec = (video_settings.get("vcodec") or "").lower()
                if vcodec in {"libx264", "libx265", "libvpx-vp9"}:
                    w.SetOption(smartedit.VIDEO_STREAM, "g", "48")
                    w.SetOption(smartedit.VIDEO_STREAM, "allow_b_frames", "1")
                    w.SetOption(smartedit.VIDEO_STREAM, "max_b_frames", "3")


            
            w.Open()

            
            title_message = ""
            self.ExportStarted.emit(export_file_path, video_settings.get("start_frame"), video_settings.get("end_frame"))

            progressstep = max(1 , round(( video_settings.get("end_frame") - video_settings.get("start_frame") ) / 1000))
            start_time_export = time.time()
            start_frame_export = video_settings.get("start_frame")
            end_frame_export = video_settings.get("end_frame")
            last_exported_time = time.time()
            last_displayed_exported_portion = 0.0

            
            for frame in range(video_settings.get("start_frame"), video_settings.get("end_frame") + 1):
                
                end_time_export = time.time()
                if ((frame % progressstep) == 0) or ((end_time_export - last_exported_time) > 1):
                    current_exported_portion = (frame - start_frame_export) * 1.0  / (end_frame_export - start_frame_export)
                    if ((current_exported_portion - last_displayed_exported_portion) > 0.0):
                        
                        
                        digits_after_decimalpoint = math.ceil( -2.0 - math.log10( current_exported_portion - last_displayed_exported_portion ))
                    else:
                        digits_after_decimalpoint = 1
                    if digits_after_decimalpoint < 1:
                        
                        digits_after_decimalpoint = 1
                    if digits_after_decimalpoint > 5:
                        
                        digits_after_decimalpoint = 5
                    last_displayed_exported_portion = current_exported_portion
                    format_of_progress_string = "%4." + str(digits_after_decimalpoint) + "f%% "
                    last_exported_time = time.time()
                    if ((frame - start_frame_export) != 0) & ((end_time_export - start_time_export) != 0):
                        seconds_left = round(( start_time_export - end_time_export )*( frame - end_frame_export )/( frame - start_frame_export ))
                        fps_encode = ((frame - start_frame_export)/(end_time_export-start_time_export))
                        if frame == end_frame_export:
                            title_message = _("Finalizing video export, please wait...")
                        else:
                            title_message = titlestring(seconds_left, fps_encode, "Remaining")

                    
                    self.ExportFrame.emit(
                        title_message,
                        video_settings.get("start_frame"),
                        video_settings.get("end_frame"),
                        frame,
                        format_of_progress_string
                    )

                    
                    QCoreApplication.processEvents()

                
                max_frame = frame

                
                w.WriteFrame(self.timeline.GetFrame(frame))
                if self.cache_thread:
                    self.cache_thread.Seek(frame)

                
                if not self.exporting:
                    break

            
            w.Close()

            
            seconds_run = round((end_time_export - start_time_export))
            title_message = titlestring(seconds_run, fps_encode, "Elapsed")

            self.ExportFrame.emit(
                title_message,
                video_settings.get("start_frame"),
                video_settings.get("end_frame"),
                max_frame,
                format_of_progress_string
            )

        except Exception as e:
            
            
            error_type_str = str(e)
            log.info("Error type string: %s" % error_type_str)

            if "InvalidChannels" in error_type_str:
                log.info("Error setting invalid # of channels (%s)" % (audio_settings.get("channels")))
                track_metric_error("invalid-channels-%s-%s-%s-%s" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec"), audio_settings.get("channels")))

            elif "InvalidSampleRate" in error_type_str:
                log.info("Error setting invalid sample rate (%s)" % (audio_settings.get("sample_rate")))
                track_metric_error("invalid-sample-rate-%s-%s-%s-%s" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec"), audio_settings.get("sample_rate")))

            elif "InvalidFormat" in error_type_str:
                log.info("Error setting invalid format (%s)" % (video_settings.get("vformat")))
                track_metric_error("invalid-format-%s" % (video_settings.get("vformat")))

            elif "InvalidCodec" in error_type_str:
                log.info("Error setting invalid codec (%s/%s/%s)" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))
                track_metric_error("invalid-codec-%s-%s-%s" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))

            elif "ErrorEncodingVideo" in error_type_str:
                log.info("Error encoding video frame (%s/%s/%s)" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))
                track_metric_error("video-encode-%s-%s-%s" % (video_settings.get("vformat"), video_settings.get("vcodec"), audio_settings.get("acodec")))

            
            friendly_error = error_type_str.split("> ")[0].replace("<", "")

            
            msg = QMessageBox()
            msg.setWindowTitle(_("Export Error"))
            msg.setText(_("Sorry, there was an error exporting your video: \n%s") % friendly_error)
            msg.exec_()

        
        self.ExportEnded.emit(export_file_path)

        
        self.timeline.Close()

        
        self.timeline.ClearAllCache()

        
        smartedit.Settings.Instance().HIGH_QUALITY_SCALING = False

        
        if self.cache_thread:
            self.cache_thread.StopThread(10000)
            self.cache_thread.Reader(None)
            self.cache_thread = None
        get_app().window.timeline_sync.timeline.SetCache(self.old_cache_object)
        get_app().window.cache_object = self.old_cache_object

        
        if self.s.get("show_finished_window") and self.exporting:
            
            self.cancel_button.setVisible(False)
            self.export_button.setVisible(False)

            
            self.close_button.setVisible(True)

            
            from qt_api import QPalette
            p = QPalette()
            p.setColor(QPalette.Highlight, Qt.green)
            self.progressExportVideo.setPalette(p)

            
            self.show()
        else:
            
            super(Export, self).accept()

    def save_settings(self):
        if self.restoring_defaults:
            return  

        
        settings = []

        
        for child in self.findChildren(QWidget):
            if child.objectName().startswith("qt_"):
                continue
            setting = {}
            if isinstance(child, QLineEdit):
                setting['name'] = child.objectName()
                setting['type'] = 'QLineEdit'
                setting['value'] = child.text()
            elif isinstance(child, QComboBox):
                setting['name'] = child.objectName()
                setting['type'] = 'QComboBox'
                setting['value'] = child.currentIndex()
            elif isinstance(child, QSpinBox):
                setting['name'] = child.objectName()
                setting['type'] = 'QSpinBox'
                setting['value'] = child.value()
            elif isinstance(child, QCheckBox):
                setting['name'] = child.objectName()
                setting['type'] = 'QCheckBox'
                setting['value'] = child.isChecked()
            
            if setting:
                settings.append(setting)

        
        get_app().updates.ignore_history = True
        get_app().updates.update(["export_settings"], settings)
        get_app().updates.ignore_history = False

        log.info("Export settings saved: %s", settings)

    def load_settings(self):
        
        settings = get_app().project.get("export_settings")

        if not settings:
            log.info("No saved settings found.")
            return

        
        for setting in settings:
            widget = self.findChild(QWidget, setting['name'])
            if widget:
                if setting['type'] == 'QLineEdit':
                    widget.setText(setting.get('value', ''))
                elif setting['type'] == 'QComboBox':
                    widget.setCurrentIndex(setting.get('value', 0))
                elif setting['type'] in ['QSpinBox', 'QDoubleSpinBox']:
                    widget.setValue(setting.get('value', widget.minimum()))
                elif setting['type'] == 'QCheckBox':
                    widget.setChecked(setting.get('value', False))

        
        if self.checkStartFirstClip.isChecked():
            self.updateFrameRate(True)
        if self.checkEndLastClip.isChecked():
            self.updateFrameRate(True)

        log.info("Export settings loaded: %s", settings)

    def reject(self):
        self.save_settings()

        if self.exporting and not self.close_button.isVisible():
            
            _ = get_app()._tr
            result = QMessageBox.question(
                self,
                _("Export Video"),
                _("Are you sure you want to cancel the export?"),
                QMessageBox.No | QMessageBox.Yes)
            if result == QMessageBox.No:
                
                return

        
        smartedit.Settings.Instance().HIGH_QUALITY_SCALING = False

        
        if self.cache_thread:
            self.cache_thread.StopThread(10000)
            self.cache_thread.Reader(None)
            self.cache_thread = None
        get_app().window.timeline_sync.timeline.SetCache(self.old_cache_object)
        get_app().window.cache_object = self.old_cache_object

        
        self.exporting = False
        super(Export, self).reject()

    def calculate_all_formats_bitrate(self, quality_key):
        """Calculate a bitrate using bits-per-pixel guidance for All Formats presets."""
        quality_bpp = {
            "Low": 0.055,    
            "Med": 0.08,     
            "High": 0.12     
        }
        target_bpp = quality_bpp.get(quality_key)
        if target_bpp is None:
            return None

        width = self.txtWidth.value()
        height = self.txtHeight.value()
        fps_den = self.txtFrameRateDen.value() or 1
        fps = self.txtFrameRateNum.value() / fps_den

        if not width or not height or not fps:
            return None

        bitrate_bits_per_sec = width * height * fps * target_bpp
        bitrate_mbps = bitrate_bits_per_sec / 1_000_000.0
        return f"{bitrate_mbps:.2f} Mb/s"

    @staticmethod
    def _is_quality_mode_rate(rate_text):
        """Return True if a preset rate uses quality-mode units (crf/cqp/qp)."""
        text = (rate_text or "").strip().lower()
        return (" crf" in text) or (" cqp" in text) or (" qp" in text)

    def update_all_formats_bitrates(self):
        """Refresh dynamic video bitrates when using All Formats presets."""
        _ = get_app()._tr
        if self.cboSimpleProjectType.currentData() != _("All Formats"):
            return

        
        
        if any(self._is_quality_mode_rate(v) for v in getattr(self, "vbr", {}).values()):
            return
        if self._is_quality_mode_rate(self.txtVideoBitRate.text()):
            return

        dynamic_vbr = {}
        for key, translated in [("Low", _("Low")), ("Med", _("Med")), ("High", _("High"))]:
            bitrate = self.calculate_all_formats_bitrate(key)
            if bitrate:
                dynamic_vbr[translated] = bitrate

        if not dynamic_vbr:
            return

        self.vbr = dynamic_vbr
        selected_quality = self.cboSimpleQuality.itemData(self.cboSimpleQuality.currentIndex())
        if selected_quality:
            translated_quality = _(selected_quality)
            if translated_quality in self.vbr:
                self.txtVideoBitRate.setText(self.vbr[translated_quality])
