"""
 @file
 @brief This file loads the Preferences dialog (i.e where is all preferences)
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author Olivier Girard <olivier@smartedit.org>

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
import operator
import functools
import platform

from qt_api import Qt, QSize, QDir
from qt_api import (
    QWidget, QDialog, QMessageBox, QFileDialog, QDialogButtonBox,
    QVBoxLayout, QHBoxLayout, QSizePolicy,
    QScrollArea, QLabel, QLineEdit, QPushButton,
    QDoubleSpinBox, QComboBox, QCheckBox, QSpinBox, QStyle,
)
from qt_api import QKeySequence, QIcon

from classes import info, ui_util, tabstops
from classes import smartedit_rc  
from classes.app import get_app
from classes.language import get_all_languages
from classes.logger import log
from classes.metrics import track_metric_screen

import smartedit


class Preferences(QDialog):
    """ Preferences Dialog """

    
    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'preferences.ui')

    def __init__(self):

        
        super().__init__()

        
        ui_util.load_ui(self, self.ui_path)

        
        ui_util.init_ui(self)

        self.custom_order = ["General", "Timeline", "Preview", "Autosave", "Cache", "Performance", "Keyboard", "Location"]

        
        self.s = get_app().get_settings()

        
        self.settings_data = self.s.get_all_settings()

        
        track_metric_screen("preferences-screen")

        
        smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = False

        
        self.params = {}
        for item in self.settings_data:
            if "setting" in item and "value" in item:
                self.params[item["setting"]] = item

        
        self.setting_widgets = {}
        self.dependency_map = {}

        
        self.txtSearch.textChanged.connect(self.txtSearch_changed)
        self.btnRestoreDefaults.clicked.connect(self.confirm_restore_defaults)
        self.tabCategories.currentChanged.connect(self.category_tab_changed)

        
        self.btnRestoreDefaults.setAutoDefault(False)
        self.btnRestoreDefaults.setDefault(False)

        
        close_button = self.buttonBox.button(QDialogButtonBox.Close)
        if close_button:
            close_button.setDefault(True)

        self.requires_restart = False
        self.category_names = {}
        self.category_tabs = {}
        self.category_sort = {}
        self.visible_category_names = {}

        
        self.hardware_tests_cards = {0: [0, ]}

        
        self.Populate()

        
        self.check_shortcut_validity()

    def category_tab_changed(self, index):
        """Update the Restore Defaults button label based on the selected tab."""
        
        current_widget = self.tabCategories.widget(index)
        if not current_widget:
            return

        
        non_translated_category = current_widget.objectName()

        
        if non_translated_category:
            self.btnRestoreDefaults.setText(f"Restore Defaults: {non_translated_category}")

        self._apply_tab_order()

    def txtSearch_changed(self, *_args):
        """textChanged event handler for search box"""
        log.info("Search for %s", self.txtSearch.text())

        
        self.Populate(filter=self.txtSearch.text())

    def DeleteAllTabs(self, onlyInVisible=False):
        """Delete all tabs and ensure they are fully removed from memory."""
        for name, widget in dict(self.category_tabs).items():
            
            if (onlyInVisible and name not in self.visible_category_names) or not onlyInVisible:
                
                parent_widget = widget.parent().parent()
                parent_widget.setParent(None)
                parent_widget.deleteLater()

                
                if name in self.category_names:
                    self.category_names.pop(name)
                if name in self.visible_category_names:
                    self.visible_category_names.pop(name)
                if name in self.category_tabs:
                    self.category_tabs.pop(name)

    def Populate(self, filter=""):
        """Populate all preferences and tabs"""
        
        app = get_app()
        _ = app._tr

        
        self.DeleteAllTabs()

        self.category_names = {}
        self.category_tabs = {}
        self.visible_category_names = {}

        
        self.setting_widgets = {}
        self.dependency_map = {}

        
        for item in self.settings_data:
            category = item.get("category")
            setting_type = item.get("type")
            sort_type = item.get("sort")

            if setting_type != "hidden":
                
                if category not in self.category_names:
                    self.category_names[category] = []
                if sort_type:
                    self.category_sort[category] = sort_type

                
                self.category_names[category].append(item)

        
        for category in self.custom_order:
            if category in self.category_names:
                
                scroll_area = QScrollArea(self)
                scroll_area.setWidgetResizable(True)
                scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                scroll_area.setMinimumSize(675, 100)

                
                layout = QVBoxLayout()
                tabWidget = QWidget(self)
                tabWidget.setObjectName("PreferencePanel")
                tabWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                tabWidget.setLayout(layout)
                scroll_area.setWidget(tabWidget)
                scroll_area.setObjectName(category)

                
                self.tabCategories.addTab(scroll_area, _(category))
                self.category_tabs[category] = tabWidget

        
        for category in self.custom_order:
            tabWidget = self.category_tabs[category]
            filterFound = False

            
            params = self.category_names[category]
            if self.category_sort.get(category):
                
                params.sort(key=lambda setting: _(setting.get("title")))

            
            for param in params:
                
                if filter and (filter.lower() in _(param["title"]).lower() or filter.lower() in _(category).lower()):
                    filterFound = True
                elif not filter:
                    filterFound = True
                else:
                    filterFound = False

                
                if filterFound:
                    self.visible_category_names[category] = tabWidget

                
                widget = None
                extraWidget = None
                label = QLabel()
                label.setText(_(param["title"]))
                label.setToolTip(_(param["title"]))

                if param["type"] == "spinner":
                    
                    widget = QDoubleSpinBox()
                    widget.setMinimum(float(param["min"]))
                    widget.setMaximum(float(param["max"]))
                    widget.setValue(float(param["value"]))
                    widget.setSingleStep(param.get("step", 1.0))
                    widget.setToolTip(param["title"])
                    widget.valueChanged.connect(functools.partial(self.spinner_value_changed, param))

                if param["type"] == "spinner-int":
                    
                    widget = QSpinBox()
                    min_value = int(param["min"])
                    max_value = int(param["max"])
                    current_value = int(param["value"])
                    thread_limits = self._get_thread_spinner_limits(param.get("setting"))
                    if thread_limits:
                        min_value, max_value = thread_limits
                        clamped_value = max(min_value, min(current_value, max_value))
                        if clamped_value != current_value:
                            self.s.set(param["setting"], clamped_value)
                            param["value"] = clamped_value
                            current_value = clamped_value
                    widget.setMinimum(min_value)
                    widget.setMaximum(max_value)
                    widget.setValue(current_value)
                    widget.setSingleStep(param.get("step", 1))
                    widget.setToolTip(param["title"])
                    widget.valueChanged.connect(functools.partial(self.spinner_value_changed, param))

                elif param["type"] == "text" or param["type"] == "browse":
                    
                    widget = QLineEdit()
                    widget.setText(_(param["value"]))
                    widget.setObjectName(param["setting"])
                    widget.textChanged.connect(functools.partial(self.text_value_changed, widget, param))

                    if param["type"] == "browse":
                        
                        extraWidget = QPushButton(_("Browse..."))
                        extraWidget.clicked.connect(functools.partial(self.selectExecutable, widget, param))
                    elif param.get("setting") == "comfy-ui-url":
                        
                        extraWidget = QPushButton(_("Check"))
                        extraWidget.clicked.connect(
                            functools.partial(self.check_comfy_ui_url, widget, param, extraWidget)
                        )

                elif param["type"] == "bool":
                    
                    widget = QCheckBox()
                    widget.setMinimumHeight(24)
                    if param["value"] is True:
                        widget.setCheckState(Qt.Checked)
                    else:
                        widget.setCheckState(Qt.Unchecked)
                    widget.stateChanged.connect(functools.partial(self.bool_value_changed, widget, param))

                elif param["type"] == "dropdown":

                    
                    widget = QComboBox()
                    if param.get("setting") == "hw-decoder":
                        
                        widget.setMinimumHeight(34)
                    else:
                        widget.setFixedHeight(28)
                    widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)

                    
                    value_list = param["values"]
                    
                    if param["setting"] == "default-profile":
                        value_list = []
                        
                        for profile_folder in [info.USER_PROFILES_PATH, info.PROFILES_PATH]:
                            for file in reversed(sorted(os.listdir(profile_folder))):
                                
                                profile_path = os.path.join(profile_folder, file)
                                if os.path.isdir(profile_path):
                                    continue
                                profile = smartedit.Profile(profile_path)
                                profile_lbl = f"{profile.info.description} ({profile.info.width}x{profile.info.height})"
                                value_list.append({
                                    "name": profile_lbl,
                                    "value": profile.info.description
                                    })

                        
                        extraWidget = QPushButton()
                        extraWidget.setToolTip(_("Search Profiles"))
                        extraWidget.setIcon(QIcon(":/icons/Humanity/mimes/16/video-x-generic.svg"))
                        extraWidget.clicked.connect(functools.partial(self.btnBrowseProfiles_clicked, widget))

                    
                    if param["setting"] == "playback-audio-device":
                        value_list = []
                        
                        value_list.append({"name": "Default", "value": ""})
                        for audio_device in get_app().window.preview_thread.player.GetAudioDeviceNames():
                            
                            
                            value_list.append({
                                "name": "%s: %s" % (audio_device[1], audio_device[0]),
                                "value": "%s||%s" % (audio_device[0], audio_device[1])
                            })

                    
                    if param["setting"] == "theme":
                        from themes.manager import ThemeName
                        value_list = []
                        for theme_name in ThemeName.get_sorted_theme_names():
                            value_list.append({
                                "name": _(theme_name), "value": theme_name
                            })

                    if param["setting"] == "ui-scale":
                        current_scale = float(param["value"])
                        has_current_value = any(
                            abs(float(item.get("value", 0.0)) - current_scale) < 0.001
                            for item in value_list
                        )
                        if not has_current_value:
                            value_list.append({
                                "name": _("%d%% (Custom)") % int(round(current_scale * 100)),
                                "value": current_scale,
                            })
                            value_list.sort(key=lambda item: float(item.get("value", 0.0)))

                    
                    if param["setting"] == "default-language":
                        value_list = []
                        
                        for locale, language, country in get_all_languages():
                            
                            if language:
                                lang_name = "%s (%s)" % (language, locale)
                                value_list.append({
                                    "name": lang_name,
                                    "value": locale
                                    })
                        
                        value_list.sort(key=operator.itemgetter("name"))
                        
                        value_list.insert(0, {
                            "name": _("Default"),
                            "value": "Default"
                            })

                    
                    os_platform = platform.system()
                    if param["setting"] == "hw-decoder":
                        popup_view = widget.view()
                        if hasattr(popup_view, "setSpacing"):
                            popup_view.setSpacing(1)
                        for value_item in list(value_list):
                            v = value_item["value"]
                            
                            if os_platform == "Darwin" and v not in ("0", "5", "2"):
                                value_list.remove(value_item)
                            elif os_platform == "Windows" and v not in ("0", "3", "4"):
                                value_list.remove(value_item)
                            elif os_platform == "Linux" and v not in ("0", "1", "2", "6"):
                                value_list.remove(value_item)

                            
                            extraWidget = QPushButton(_("Test"))
                            extraWidget.clicked.connect(functools.partial(self.testHardwareDecode, widget,
                                                                          param, extraWidget))

                    
                    if param["setting"] in ("graca_number_en", "graca_number_de"):
                        value_list = []
                        for card_index in range(0, 3):
                            
                            value_list.append({
                                "value": card_index,
                                "name": _("Graphics Card %s") % card_index
                            })

                    
                    box_index = 0
                    for value_item in value_list:
                        k = value_item.get("name")
                        v = value_item.get("value")
                        i = value_item.get("icon", None)

                        
                        if param.get("translate_values"):
                            k = _(value_item["name"])

                        
                        
                        icon = None
                        if k == "Linux VA-API" or i == 1:
                            icon = QIcon(":/hw/hw-accel-vaapi.svg")
                        elif k == "Nvidia NVDEC" or i == 2:
                            icon = QIcon(":/hw/hw-accel-nvdec.svg")
                        elif k == "Linux VDPAU" or i == 6:
                            icon = QIcon(":/hw/hw-accel-vdpau.svg")
                        elif k == "Windows D3D9" or i == 3:
                            icon = QIcon(":/hw/hw-accel-dx.svg")
                        elif k == "Windows D3D11" or i == 4:
                            icon = QIcon(":/hw/hw-accel-dx.svg")
                        elif k == "MacOS" or i == 5:
                            icon = QIcon(":/hw/hw-accel-vtb.svg")
                        elif k == "Intel QSV" or i == 7:
                            icon = QIcon(":/hw/hw-accel-qsv.svg")
                        elif k == "No acceleration" or i == 0:
                            icon = QIcon(":/hw/hw-accel-none.svg")

                        
                        if icon:
                            widget.setIconSize(QSize(60, 18))
                            widget.addItem(icon, _(k), v)
                        else:
                            widget.addItem(_(k), v)

                        
                        if (
                            param["setting"] == "ui-scale"
                            and abs(float(v) - float(param["value"])) < 0.001
                        ) or v == param["value"]:
                            widget.setCurrentIndex(box_index)
                        box_index = box_index + 1

                    widget.currentIndexChanged.connect(functools.partial(self.dropdown_index_changed, widget, param))

                
                if (widget and label and filterFound):
                    
                    label.setMinimumWidth(180)
                    label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

                    
                    layout_hbox = QHBoxLayout()
                    layout_hbox.addWidget(label)
                    layout_hbox.addWidget(widget)

                    if (extraWidget):
                        layout_hbox.addWidget(extraWidget)

                    
                    tabWidget.layout().addLayout(layout_hbox)
                    self.register_setting_widget(param, widget, label)
                elif (label and filterFound):
                    
                    tabWidget.layout().addWidget(label)

            
            tabWidget.layout().addStretch()

        self.apply_all_dependencies()

        
        self.DeleteAllTabs(onlyInVisible=True)

        self._apply_tab_order()

    def register_setting_widget(self, param, widget, label=None):
        """Store widget references and register dependency relationships."""
        setting_name = param.get("setting")
        if not setting_name or not widget:
            return

        self.setting_widgets[setting_name] = widget
        widget.setObjectName(setting_name)

        dependency = param.get("dependency")
        if dependency:
            self.dependency_map.setdefault(dependency, []).append((widget, label))

    def _apply_tab_order(self):
        """Apply a stable tab order for the currently visible preferences tab."""
        current_tab = self.tabCategories.currentWidget()
        if not current_tab:
            tabstops.apply_auto_tab_order_later(self)
            return

        content_widget = current_tab.widget()
        if not content_widget:
            tabstops.apply_auto_tab_order_later(self)
            return

        
        if current_tab.focusProxy() is None and content_widget is not None:
            current_tab.setFocusProxy(content_widget)

        ordered = [self.txtSearch, self.tabCategories, current_tab]
        ordered.extend(
            tabstops.collect_focusable_from_layout(
                content_widget.layout(), self, include_hidden=True
            )
        )
        ordered.extend([self.btnRestoreDefaults, self.buttonBox])

        tabstops.apply_explicit_tab_order_later(
            ordered, root=self, include_hidden=True
        )

    def apply_all_dependencies(self):
        """Apply dependency state to all registered widgets."""
        for setting_name in list(self.dependency_map.keys()):
            self.apply_dependency_state(setting_name)

    def apply_dependencies_for_controller(self, controller_setting):
        """Apply dependency states linked to a specific controller setting."""
        if not controller_setting:
            return
        for dependency_key in list(self.dependency_map.keys()):
            setting_name = dependency_key[1:] if dependency_key.startswith("!") else dependency_key
            if setting_name == controller_setting:
                self.apply_dependency_state(dependency_key)

    def apply_dependency_state(self, dependency_key):
        """Enable/disable dependent widgets based on controller state.

        A dependency key can be prefixed with "!" to invert the controller value.
        """
        controlled_widgets = self.dependency_map.get(dependency_key, [])
        if not controlled_widgets:
            return

        invert = False
        setting_name = dependency_key
        if isinstance(dependency_key, str) and dependency_key.startswith("!"):
            invert = True
            setting_name = dependency_key[1:]

        enabled = bool(self.s.get(setting_name))
        if invert:
            enabled = not enabled
        for widget, label in controlled_widgets:
            if widget:
                widget.setEnabled(enabled)

    def selectExecutable(self, widget, param):
        _ = get_app()._tr

        
        startpath = QDir.rootPath()

        
        
        if "setting" in param and param["setting"]:
            prev_val = self.s.get(param["setting"])
            while prev_val and not os.path.exists(prev_val):
                prev_val = os.path.dirname(prev_val)
            if prev_val and os.path.exists(prev_val):
                startpath = prev_val

        fileName = QFileDialog.getOpenFileName(
            self,
            _("Select executable file"),
            startpath)[0]
        if fileName:
            if platform.system() == "Darwin":
                
                appBundlePath = os.path.join(fileName, 'Contents', 'MacOS')
                if os.path.exists(os.path.join(appBundlePath, 'blender')):
                    fileName = os.path.join(appBundlePath, 'blender')
                elif os.path.exists(os.path.join(appBundlePath, 'Blender')):
                    fileName = os.path.join(appBundlePath, 'Blender')
                elif os.path.exists(os.path.join(appBundlePath, 'Inkscape')):
                    fileName = os.path.join(appBundlePath, 'Inkscape')

            self.s.set(param["setting"], fileName)
            widget.setText(fileName)

    def check_for_restart(self, param):
        """Check if the app needs to restart"""
        if "restart" in param and param["restart"]:
            self.requires_restart = True

    def _apply_timeline_thumbnail_style(self):
        """Push the current thumbnail preference to the QWidget timeline."""
        timeline_widget = getattr(get_app().window, "timeline", None)
        if not hasattr(timeline_widget, "set_thumbnail_style"):
            return
        try:
            timeline_widget.set_thumbnail_style(self.s.get("timeline-thumbnail-style"))
        except Exception:
            log.warning("Failed to apply timeline thumbnail style live", exc_info=1)

    def _get_thread_spinner_limits(self, setting_name):
        """Return UI bounds for thread-related preference spinners."""
        lib_settings = smartedit.Settings.Instance()
        if setting_name == "omp_threads_number":
            default_value = int(lib_settings.DefaultOMPThreads())
            min_value = 2
        elif setting_name == "ff_threads_number":
            default_value = int(lib_settings.DefaultFFThreads())
            min_value = 2
        else:
            return None

        max_value = max(min_value, default_value * 3)
        return min_value, max_value

    def _apply_thread_settings(self):
        """Apply current thread preference values to libsmartedit."""
        lib_settings = smartedit.Settings.Instance()
        omp_value = int(str(self.s.get("omp_threads_number")))
        ff_value = int(str(self.s.get("ff_threads_number")))
        omp_min, omp_max = self._get_thread_spinner_limits("omp_threads_number")
        ff_min, ff_max = self._get_thread_spinner_limits("ff_threads_number")
        lib_settings.OMP_THREADS = max(omp_min, min(omp_value, omp_max))
        lib_settings.ApplyOpenMPSettings()
        lib_settings.FF_THREADS = max(ff_min, min(ff_value, ff_max))

    def _apply_cache_settings(self):
        """Apply current cache preference values to the active session."""
        get_app().window.InitCacheSettings()

    def bool_value_changed(self, widget, param, state):
        
        if state == Qt.Checked:
            self.s.set(param["setting"], True)
        else:
            self.s.set(param["setting"], False)

        
        if param["setting"] == "debug-mode":
            
            log.info("Setting debug-mode to %s", state == Qt.Checked)
            debug_enabled = (state == Qt.Checked)

            
            smartedit.ZmqLogger.Instance().Enable(debug_enabled)

        elif param["setting"] == "enable-auto-save":
            
            if (state == Qt.Checked):
                
                get_app().window.auto_save_timer.start()
            else:
                
                get_app().window.auto_save_timer.stop()

        
        self.check_for_restart(param)

        
        if param.get("setting"):
            self.apply_dependencies_for_controller(param["setting"])

    def spinner_value_changed(self, param, value):
        
        self.s.set(param["setting"], value)
        log.info(value)

        if param["setting"] == "autosave-interval":
            
            get_app().window.auto_save_timer.setInterval(int(value * 1000 * 60))

        elif param["setting"] == "omp_threads_number":
            lib_settings = smartedit.Settings.Instance()
            value = int(str(value))
            min_value, max_value = self._get_thread_spinner_limits("omp_threads_number")
            lib_settings.OMP_THREADS = max(min_value, min(value, max_value))
            lib_settings.ApplyOpenMPSettings()

        elif param["setting"] == "ff_threads_number":
            lib_settings = smartedit.Settings.Instance()
            value = int(str(value))
            min_value, max_value = self._get_thread_spinner_limits("ff_threads_number")
            lib_settings.FF_THREADS = max(min_value, min(value, max_value))

        elif param["setting"] == "decode_hw_max_width":
            smartedit.Settings.Instance().DE_LIMIT_WIDTH_MAX = int(str(value))

        elif param["setting"] == "decode_hw_max_height":
            smartedit.Settings.Instance().DE_LIMIT_HEIGHT_MAX = int(str(value))

        
        if param["setting"] in ["cache-limit-mb", "cache-scale", "cache-quality",
                                "cache-ahead-percent", "cache-preroll-min-frames",
                                "cache-preroll-max-frames", "cache-max-frames"]:
            get_app().window.InitCacheSettings()

        
        self.check_for_restart(param)

    def text_value_changed(self, widget, param, value=None):
        try:
            
            if not value:
                value = widget.toPlainText()
        except Exception:
            log.debug('Failed to get plain text from widget')

        
        if param.get("category") == "Keyboard":
            previous_value = value

            
            key_sequences = value.split('|')

            
            parsed_sequences = [QKeySequence(seq).toString() for seq in key_sequences]

            
            value = ' | '.join(parsed_sequences)
            log.info("Parsing keyboard mapping via QKeySequence from %s to %s", previous_value, value)

        
        self.s.set(param["setting"], value)
        log.info(value)

        
        if param.get("category") == "Keyboard":
            get_app().window.initShortcuts()

            
            self.check_shortcut_validity()

        
        self.check_for_restart(param)

    def check_comfy_ui_url(self, widget, param, btn=None):
        _ = get_app()._tr
        if btn and btn.property("comfy_check_pending"):
            return
        url = str(widget.text() or "").strip().rstrip("/")
        if not url:
            log.info("ComfyUI URL check failed: empty URL")
            self._update_comfy_ui_check_button(
                btn,
                available=False,
                tooltip=_("ComfyUI URL is empty."),
                enabled=True,
            )
            return

        
        self.s.set(param["setting"], url)
        widget.setText(url)
        self._update_comfy_ui_check_button(
            btn,
            available=False,
            tooltip=_("Checking ComfyUI connection..."),
            enabled=True,
            clear_icon=True,
            pending=True,
        )

        window = getattr(get_app(), "window", None)
        if not window:
            self._update_comfy_ui_check_button(
                btn,
                available=False,
                tooltip=_("Connection failed."),
                enabled=True,
                pending=False,
            )
            return

        def _handle_result(available, error_text, checked_url):
            try:
                current_url = str(widget.text() or "").strip().rstrip("/")
                if checked_url != current_url:
                    self._update_comfy_ui_check_button(
                        btn,
                        available=False,
                        tooltip=_("ComfyUI URL changed. Click Check to validate the new value."),
                        enabled=True,
                        clear_icon=True,
                        pending=False,
                    )
                    return
                if available:
                    self._update_comfy_ui_check_button(
                        btn,
                        available=True,
                        tooltip=_("Connection successful. AI menus are enabled."),
                        enabled=True,
                        pending=False,
                    )
                    return

                message = _("Connection failed: {}").format(error_text) if error_text else _("Connection failed.")
                self._update_comfy_ui_check_button(
                    btn,
                    available=False,
                    tooltip="{} {}".format(
                        message,
                        _("AI menus are disabled until ComfyUI is reachable."),
                    ),
                    enabled=True,
                    pending=False,
                )
            except RuntimeError:
                return

        window.refresh_comfy_availability_async(timeout=2.0, callback=_handle_result)

    def _update_comfy_ui_check_button(self, btn, available, tooltip, enabled, clear_icon=False, pending=None):
        if not btn:
            return
        if clear_icon:
            btn.setIcon(QIcon())
        else:
            icon = self.style().standardIcon(
                QStyle.SP_DialogApplyButton if available else QStyle.SP_DialogCancelButton
            )
            btn.setIcon(icon)
        btn.setToolTip(str(tooltip or ""))
        btn.setEnabled(bool(enabled))
        if pending is not None:
            btn.setProperty("comfy_check_pending", bool(pending))

    def dropdown_index_changed(self, widget, param, index):
        
        value = widget.itemData(index)
        self.s.set(param["setting"], value)
        log.info(value)

        
        if param["setting"] in ["cache-mode", "cache-image-format"]:
            get_app().window.InitCacheSettings()

        if param["setting"] == "hw-decoder":
            
            smartedit.Settings.Instance().HARDWARE_DECODER = int(value)

        if param["setting"] == "graca_number_de":
            smartedit.Settings.Instance().HW_DE_DEVICE_SET = int(value)

        if param["setting"] == "graca_number_en":
            smartedit.Settings.Instance().HW_EN_DEVICE_SET = int(value)

        if param["setting"] == "theme":
            
            if get_app().theme_manager:
                get_app().theme_manager.apply_theme(value)

        if param["setting"] == "timeline-thumbnail-style":
            self._apply_timeline_thumbnail_style()

        
        self.check_for_restart(param)

    def btnBrowseProfiles_clicked(self, widget):
        """Search profile button clicked"""
        
        profile_description = widget.currentData()

        
        matching_profile_path = None
        for profile_folder in [info.USER_PROFILES_PATH, info.PROFILES_PATH]:
            for file in reversed(sorted(os.listdir(profile_folder))):
                
                matching_profile_path = os.path.join(profile_folder, file)
                if os.path.isdir(matching_profile_path):
                    continue
                profile = smartedit.Profile(matching_profile_path)
                if profile.info.description == profile_description:
                    break

        
        current_profile = smartedit.Profile(matching_profile_path)

        
        from windows.profile import Profile
        log.debug("Showing profile dialog")
        win = Profile(current_profile.Key())
        
        result = win.exec_()

        profile = win.selected_profile
        if result == QDialog.Accepted and profile:

            
            profile_index = self.getVideoProfileIndex(widget, profile)
            if profile_index != -1:
                
                widget.setCurrentIndex(profile_index)
            else:
                
                
                widget.setCurrentIndex(0)

    def getVideoProfileIndex(self, widget, profile):
        """Get the index of a profile name or profile key (-1 if not found)"""
        for index in range(widget.count()):
            combo_profile_description = widget.itemData(index)
            if profile.info.description == combo_profile_description:
                return index
        return -1

    def testHardwareDecode(self, widget, param, btn):
        """Test specific settings for hardware decode"""
        all_decoders = param.get("values", [])
        is_supported = False

        
        current_decoder = smartedit.Settings.Instance().HARDWARE_DECODER
        current_decoder_card = smartedit.Settings.Instance().HW_DE_DEVICE_SET
        current_decoder_name = next(item for item in all_decoders
                                    if item["value"] == str(current_decoder)).get("name", "Unknown")
        log.debug("Testing hardware decoder: %s (Decoder Type: %s, Graphics Card: %s)",
            current_decoder_name, current_decoder, current_decoder_card)

        try:
            
            example_media = os.path.join(info.RESOURCES_PATH, "hardware-example.mp4")
            clip = smartedit.Clip(example_media)
            reader = clip.Reader()

            
            reader.Open()

            
            
            
            pixel_ok = reader.GetFrame(1).CheckPixel(0, 0, 2, 133, 255, 255, 5)
            hardware_ok = current_decoder == 0 or reader.HardwareDecodeSuccessful()
            if pixel_ok and hardware_ok:
                is_supported = True
                log.debug("Successful test of hardware decoder: %s (Decoder Type: %s, Graphics Card: %s)",
                          current_decoder_name, current_decoder, current_decoder_card)
            else:
                log.debug("Failed test of hardware decoder (incorrect pixel color or software fallback used): "
                          "%s (Decoder Type: %s, Graphics Card: %s)",
                          current_decoder_name, current_decoder, current_decoder_card)

            reader.Close()
            clip.Close()

        except Exception as ex:
            log.debug("Exception testing hardware decoder: %s (Decoder Type: %s, Graphics Card: %s) %s",
                      current_decoder_name, current_decoder, current_decoder_card, str(ex))

        
        icon_name = "SP_DialogApplyButton"
        if not is_supported:
            icon_name = "SP_DialogCancelButton"
        pixmapi = getattr(QStyle, icon_name)
        icon = self.style().standardIcon(pixmapi)
        btn.setIcon(icon)

        return is_supported

    def confirm_restore_defaults(self):
        """Prompt the user for confirmation before restoring defaults for the current tab."""
        
        current_index = self.tabCategories.currentIndex()
        current_widget = self.tabCategories.widget(current_index)

        
        category = current_widget.objectName()

        
        _ = get_app()._tr
        reply = QMessageBox.question(
            self,
            _('Restore Defaults').format(category=category),
            _('Restore default values for {category}?').format(category=category),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        
        if reply == QMessageBox.Yes:
            
            self.requires_restart = self.s.restore(category_filter=category)
            self.settings_data = self.s.get_all_settings()

            if category == "Performance":
                self._apply_thread_settings()
                self._apply_cache_settings()
            elif category == "Cache":
                self._apply_cache_settings()

            
            self._apply_timeline_thumbnail_style()

            
            self.Populate()
            self.tabCategories.setCurrentIndex(current_index)

            
            get_app().window.initShortcuts()

            
            self.check_shortcut_validity()

    def check_shortcut_validity(self):
        """Check all keyboard settings for duplicate or invalid shortcuts and update the UI."""

        
        used_shortcuts = {}

        
        for shortcut in get_app().window.getAllKeyboardShortcuts():
            method_name = shortcut.get('setting')

            
            shortcut_sequences = get_app().window.getShortcutByName(method_name)

            
            key_sequences = [QKeySequence(seq).toString() for seq in shortcut_sequences if seq]

            for key_sequence in key_sequences:
                if key_sequence in used_shortcuts:
                    
                    used_shortcuts[key_sequence]['is_duplicate'] = True
                    used_shortcuts[key_sequence]['params'].append(method_name)
                else:
                    used_shortcuts[key_sequence] = {'is_duplicate': False, 'params': [method_name]}

        
        self.update_shortcut_visual_feedback(used_shortcuts)

    def update_shortcut_visual_feedback(self, shortcut_map):
        """Update the UI to provide feedback for duplicated/invalid shortcuts."""

        for key_sequence, info in shortcut_map.items():
            for param_name in info['params']:
                
                widget = self.findChild(QLineEdit, param_name)

                if widget:
                    if info['is_duplicate']:
                        
                        widget.setStyleSheet("color: red;")

    def closeEvent(self, event):
        """Signal for closing Preferences window"""
        
        self.reject()

    def reject(self):
        
        smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = True

        
        if self.requires_restart:
            msg = QMessageBox()
            _ = get_app()._tr
            msg.setWindowTitle(_("Restart Required"))
            msg.setText(_("Please restart SmartEdit for all preferences to take effect."))
            msg.exec_()

        
        super(Preferences, self).reject()
