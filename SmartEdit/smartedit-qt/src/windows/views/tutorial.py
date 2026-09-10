"""
 @file
 @brief This file contains the tutorial dialogs, which are used to explain certain features to new users
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

import functools

from qt_api import Qt, QPoint, QPointF, QRectF, QTimer, QObject, QRect
from qt_api import (
    QColor, QPalette, QPen, QPainter, QPainterPath, QKeySequence,
)
from qt_api import (
    QAction, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QToolButton, QCheckBox,
)
from classes.logger import log
from classes.app import get_app
from classes.metrics import track_metric_screen
from classes import sentry


class TutorialDialog(QWidget):
    """ A customized QWidget used to instruct a user how to use a certain feature """

    def paintEvent(self, event):
        """ Custom paint event """
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            
            arrow_width = 15
            if not self.draw_arrow_on_right:
                self.vbox.setContentsMargins(45, 10, 20, 10)
            else:
                self.vbox.setContentsMargins(20, 10, 45, 10)

            
            corner_radius = 10
            if self.draw_arrow_on_right:
                
                rounded_rect = QRectF(0, 0, self.width() - arrow_width, self.height())
            else:
                
                rounded_rect = QRectF(arrow_width, 0, self.width() - arrow_width, self.height())

            
            path = QPainterPath()
            path.addRoundedRect(rounded_rect, corner_radius, corner_radius)
            painter.setClipPath(path)

            
            frameColor = QColor("#53a0ed")
            painter.setPen(QPen(frameColor, 1.2))
            painter.setBrush(self.palette().color(QPalette.Window))
            painter.drawRoundedRect(rounded_rect, corner_radius, corner_radius)

            
            painter.setClipping(False)

            
            if self.arrow:
                arrow_height = 15
                arrow_offset = 35

                if self.draw_arrow_on_right:
                    
                    base_point = rounded_rect.topRight()
                    arrow_point = QPointF(base_point.x() + arrow_width, base_point.y() + arrow_offset)
                    arrow_top_corner = QPointF(base_point.x() - 1, base_point.y() + arrow_offset - arrow_height)
                    arrow_bottom_corner = QPointF(base_point.x() - 1, base_point.y() + arrow_offset + arrow_height)
                else:
                    
                    base_point = rounded_rect.topLeft()
                    arrow_point = QPointF(base_point.x() - arrow_width, base_point.y() + arrow_offset)
                    arrow_top_corner = QPointF(base_point.x() + 1, base_point.y() + arrow_offset - arrow_height)
                    arrow_bottom_corner = QPointF(base_point.x() + 1, base_point.y() + arrow_offset + arrow_height)

                
                path = QPainterPath()
                path.moveTo(arrow_point)  
                path.lineTo(arrow_top_corner)  
                path.lineTo(arrow_bottom_corner)  
                path.closeSubpath()
                painter.fillPath(path, self.palette().color(QPalette.Window))

                
                border_pen = QPen(frameColor, 1)
                painter.setPen(border_pen)
                painter.drawLine(arrow_point, arrow_top_corner)  
                painter.drawLine(arrow_point, arrow_bottom_corner)  
        finally:
            painter.end()

    def checkbox_metrics_callback(self, state):
        """ Callback for error and anonymous usage checkbox"""
        s = get_app().get_settings()
        if state == Qt.Checked:
            
            s.set("send_metrics", True)
            sentry.init_tracing()

            
            track_metric_screen("metrics-opt-in")
        else:
            
            track_metric_screen("metrics-opt-out")
            sentry.disable_tracing()

            
            s.set("send_metrics", False)

    def mouseReleaseEvent(self, event):
        """Process click events on tutorial. Especially useful when tutorial messages are partially
        obscured or offscreen (i.e. on small screens). Just click any part of the tutorial, and it will
        move on to the next one."""
        self.manager.next_tip(self.widget_id)

    def __init__(self, widget_id, text, arrow, manager, *args):
        super().__init__(*args)

        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        if hasattr(Qt, "WA_ShowWithoutActivating"):
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if hasattr(Qt, "WA_AlwaysStackOnTop"):
            self.setAttribute(Qt.WA_AlwaysStackOnTop, True)

        
        app = get_app()
        _ = app._tr

        
        self.widget_id = widget_id
        self.arrow = arrow
        self.manager = manager
        self.draw_arrow_on_right = False

        
        self.vbox = QVBoxLayout()

        
        self.label = QLabel(self)
        self.label.setObjectName("lblTutorialText")
        self.label.setText(text)
        self.label.setTextFormat(Qt.RichText)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.vbox.addWidget(self.label)

        
        
        
        if self.widget_id == "0":
            
            s = get_app().get_settings()

            
            checkbox_metrics = QCheckBox()
            checkbox_metrics.setObjectName("checkboxMetrics")
            checkbox_metrics.setText(_("Yes, I would like to improve SmartEdit!"))
            if s.get("send_metrics"):
                checkbox_metrics.setCheckState(Qt.Checked)
            else:
                checkbox_metrics.setCheckState(Qt.Unchecked)
            checkbox_metrics.stateChanged.connect(functools.partial(self.checkbox_metrics_callback))
            self.vbox.addWidget(checkbox_metrics)

        
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 5, 0, 5)

        
        self.close_action = QAction(_("Hide Tutorial"), self)
        self.close_action.setShortcut(QKeySequence(Qt.Key_Escape))
        self.close_action.setShortcutContext(Qt.ApplicationShortcut)

        
        self.btn_close_tips = QPushButton(self)
        self.btn_close_tips.setText(_("Hide Tutorial"))
        self.btn_close_tips.setObjectName("HideTutorial")
        self.btn_close_tips.addAction(self.close_action)

        self.btn_next_tip = QPushButton(self)
        self.btn_next_tip.setObjectName("NextTip")
        self.btn_next_tip.setText(_("Next"))
        self.btn_next_tip.setStyleSheet("font-weight:bold;")

        hbox.addWidget(self.btn_close_tips)
        hbox.addWidget(self.btn_next_tip)
        self.vbox.addLayout(hbox)

        
        self.setLayout(self.vbox)
        self.setCursor(Qt.ArrowCursor)
        self.setMinimumWidth(350)
        self.setMinimumHeight(100)
        self.setFocusPolicy(Qt.ClickFocus)

        
        self.close_action.triggered.connect(
            functools.partial(self.manager.hide_tips, self.widget_id, True))


class TutorialManager(QObject):
    """ Manage and present a list of tutorial dialogs """

    def process(self):
        """ Process and show the first non-completed tutorial """

        
        if self.current_dialog:
            
            self.re_position_dialog()
            return

        
        for tutorial_details in self.tutorial_objects:
            
            tutorial_id = tutorial_details["id"]

            
            tutorial_object = self.get_object(tutorial_details["object_id"])

            
            if (not self.tutorial_enabled
                    or tutorial_id in self.tutorial_ids
                    or tutorial_object is None
                    or tutorial_object.visibleRegion().isEmpty()):
                continue

            
            self.position_widget = tutorial_object
            self.offset = QPoint(
                int(tutorial_details["x"]),
                int(tutorial_details["y"]))
            tutorial_dialog = TutorialDialog(tutorial_id, tutorial_details["text"], tutorial_details["arrow"], self, self.win)
            tutorial_dialog.setObjectName("tutorial")

            
            tutorial_dialog.btn_next_tip.clicked.connect(functools.partial(self.next_tip, tutorial_id))
            tutorial_dialog.btn_close_tips.clicked.connect(functools.partial(self.hide_tips, tutorial_id, True))

            self.current_dialog = tutorial_dialog

            
            self.current_dialog.adjustSize()
            self.current_dialog.setEnabled(True)
            self.re_show_dialog()
            
            QTimer.singleShot(0, self.re_position_dialog)

            break

    def _get_associated_widgets(self, action):
        """Get associated widgets from a QAction (Qt5/Qt6 compatible)."""
        
        if hasattr(action, 'associatedWidgets'):
            return action.associatedWidgets()
        if hasattr(action, 'associatedObjects'):
            
            return [obj for obj in action.associatedObjects() if isinstance(obj, QWidget)]
        return []

    def get_object(self, object_id):
        """Get an object from the main window by object id"""
        if object_id == "filesView":
            return self.win.filesView
        elif object_id == "timeline":
            return self.win.timeline
        elif object_id == "dockVideo":
            return self.win.dockVideo
        elif object_id == "propertyTableView":
            return self.win.propertyTableView
        elif object_id == "transitionsView":
            return self.win.transitionsView
        elif object_id == "effectsView":
            return self.win.effectsView
        elif object_id == "emojisView":
            return self.win.emojiListView
        elif object_id == "actionPlay":
            
            
            
            for action_name in ("actionPlay", "actionPause"):
                action = getattr(self.win, action_name, None)
                if action is None:
                    continue
                for w in self._get_associated_widgets(action):
                    if isinstance(w, QToolButton) and w.isVisible():
                        return w
        elif object_id == "export_button":
            
            for w in reversed(self._get_associated_widgets(self.win.actionExportVideo)):
                if isinstance(w, QToolButton) and w.isVisible() and w.parent() == self.win.toolBar:
                    return w

    def next_tip(self, tid):
        """ Mark the current tip completed, and show the next one """
        
        self.hide_tips(tid)

        
        self.process()

    def hide_tips(self, tid, user_clicked=False):
        """ Hide the current tip, and don't show anymore """
        s = get_app().get_settings()

        
        for tutorial_object in self.tutorial_objects:
            
            tutorial_id = tutorial_object["id"]
            if tutorial_id == tid:
                
                self.close_dialogs()
                
                if tid not in self.tutorial_ids:
                    self.tutorial_ids.append(str(tid))
                    s.set("tutorial_ids", ",".join(self.tutorial_ids))

        
        if user_clicked:
            
            self.tutorial_enabled = False
            s.set("tutorial_enabled", False)

        
        self.current_dialog = None

    def close_dialogs(self):
        """ Close any open tutorial dialogs """
        if self.current_dialog:
            self.current_dialog.hide()
            self.current_dialog.setEnabled(False)
            self.current_dialog = None

    def exit_manager(self):
        """ Disconnect from all signals, and shutdown tutorial manager """
        try:
            self.win.dockFiles.visibilityChanged.disconnect()
            self.win.dockTransitions.visibilityChanged.disconnect()
            self.win.dockEffects.visibilityChanged.disconnect()
            self.win.dockProperties.visibilityChanged.disconnect()
            self.win.dockVideo.visibilityChanged.disconnect()
            self.tutorial_timer.timeout.disconnect()
        except Exception:
            log.debug('Failed to properly disconnect from dock signals', exc_info=1)

        
        self.close_dialogs()

    def re_show_dialog(self):
        """ Re show an active dialog """
        if self.current_dialog:
            self.current_dialog.update()
            self.current_dialog.show()
            self.current_dialog.raise_()

    def hide_dialog(self):
        """ Hide an active dialog """
        if self.current_dialog:
            self.current_dialog.hide()

    def re_position_dialog(self):
        """ Reposition the tutorial dialog next to self.position_widget. """
        
        if not self.current_dialog:
            return
        if self.position_widget.isHidden() or self.position_widget.visibleRegion().isEmpty():
            self.hide_dialog()
            return

        
        pos_rect = self.position_widget.rect()
        
        pos_rect.setSize(pos_rect.size() / 4)
        pos_rect.translate(self.offset)

        
        
        position_arrow_left = self.position_widget.mapTo(self.win, pos_rect.bottomRight())
        position_arrow_right = self.position_widget.mapTo(self.win, pos_rect.bottomLeft()) - QPoint(
            self.current_dialog.width(), 0)

        
        
        parent_rect = self.win.rect()
        right_edge = parent_rect.right()
        left_edge = parent_rect.left()

        
        would_exceed_right_edge = (position_arrow_left.x() + self.current_dialog.width()) > right_edge
        if would_exceed_right_edge:
            final_position = position_arrow_right
            arrow_on_right = True
        else:
            final_position = position_arrow_left
            arrow_on_right = False

        
        if arrow_on_right and final_position.x() < left_edge:
            final_position = position_arrow_left
            arrow_on_right = False

        
        self.current_dialog.draw_arrow_on_right = arrow_on_right

        
        if arrow_on_right:
            self.current_dialog.vbox.setContentsMargins(20, 10, 45, 10)
        else:
            self.current_dialog.vbox.setContentsMargins(45, 10, 20, 10)

        
        final_parent_position = final_position
        
        parent_rect = self.win.rect()
        max_x = max(parent_rect.left(), parent_rect.right() - self.current_dialog.width())
        max_y = max(parent_rect.top(), parent_rect.bottom() - self.current_dialog.height())
        clamped_x = min(max(final_parent_position.x(), parent_rect.left()), max_x)
        clamped_y = min(max(final_parent_position.y(), parent_rect.top()), max_y)
        final_parent_position = QPoint(clamped_x, clamped_y)
        self.current_dialog.move(final_parent_position)
        self.re_show_dialog()

    def process_visibility(self):
        """Handle callbacks when widget visibility changes"""
        if self.tutorial_enabled:
            self.tutorial_timer.start()

    def __init__(self, win, *args):
        
        super().__init__(*args)

        """ Constructor """
        self.win = win
        self.dock = win.dockTutorial
        self.current_dialog = None

        
        app = get_app()
        _ = app._tr

        
        s = app.get_settings()
        self.tutorial_enabled = s.get("tutorial_enabled")
        self.tutorial_ids = s.get("tutorial_ids").split(",")

        
        self.tutorial_objects = [
            {"id": "0",
             "x": 0,
             "y": 0,
             "object_id": "dockVideo",
             "text": _("<b>Welcome!</b> SmartEdit Video Editor is an award-winning, open-source video editing application! This tutorial will walk you through the basics.<br><br>Would you like to automatically send errors and metrics to help improve SmartEdit?"),
             "arrow": False
             },
            {"id": "1",
             "x": 0,
             "y": 0,
             "object_id": "filesView",
             "text": _("<b>Project Files:</b> Get started with your project by adding video, audio, and image files here. Drag and drop files from your file system."),
             "arrow": True
             },
            {"id": "2",
             "x": 0,
             "y": 0,
             "object_id": "timeline",
             "text": _("<b>Timeline:</b> Arrange your clips on the timeline here. Overlap clips to create automatic transitions. Access lots of fun presets and options by right-clicking on clips."),
             "arrow": True
             },
            {"id": "3",
             "x": 10,
             "y": -42,
             "object_id": "actionPlay",
             "text": _("<b>Video Preview:</b> Watch your timeline video preview here. Use the buttons (play, rewind, fast-forward) to control the video playback."),
             "arrow": True},
            {"id": "4",
             "x": 0,
             "y": 0,
             "object_id": "propertyTableView",
             "text": _("<b>Properties:</b> View and change advanced properties of clips and effects here. Right-clicking on clips is usually faster than manually changing properties."),
             "arrow": True
             },
            {"id": "5",
             "x": 0,
             "y": 0,
             "object_id": "transitionsView",
             "text": _("<b>Transitions:</b> Create a gradual fade from one clip to another. Drag and drop a transition onto the timeline and position it on top of a clip (usually at the beginning or ending)."),
             "arrow": True
             },
            {"id": "6",
             "x": 0,
             "y": 0,
             "object_id": "effectsView",
             "text": _("<b>Effects:</b> Adjust brightness, contrast, saturation, and add exciting special effects. Drag and drop an effect onto the timeline and position it on top of a clip (or track)"),
             "arrow": True
             },
            {"id": "8",
             "x": 0,
             "y": 0,
             "object_id": "emojisView",
             "text": _("<b>Emojis:</b> Add exciting and colorful emojis to your project! Drag and drop an emoji onto the timeline. The emoji will become a new Clip when dropped on the Timeline."),
             "arrow": True
             },
            {"id": "7",
             "x": 10,
             "y": -27,
             "object_id": "export_button",
             "text": _("<b>Export Video:</b> When you are ready to create your finished video, click this button to export your timeline as a single video file."),
             "arrow": True
             }
        ]

        
        self.dock.setTitleBarWidget(QWidget())  
        self.dock.setAttribute(Qt.WA_NoSystemBackground, True)
        self.dock.setAttribute(Qt.WA_TranslucentBackground, True)
        self.dock.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.dock.setFloating(True)
        self.dock.hide()
        self.dock.setEnabled(False)

        
        self.tutorial_timer = QTimer(self)
        self.tutorial_timer.setInterval(200)
        self.tutorial_timer.setSingleShot(True)
        self.tutorial_timer.timeout.connect(self.process)

        
        self.win.dockFiles.visibilityChanged.connect(self.process_visibility)
        self.win.dockTransitions.visibilityChanged.connect(self.process_visibility)
        self.win.dockEffects.visibilityChanged.connect(self.process_visibility)
        self.win.dockProperties.visibilityChanged.connect(self.process_visibility)
        self.win.dockVideo.visibilityChanged.connect(self.process_visibility)
        self.win.dockEmojis.visibilityChanged.connect(self.process_visibility)
