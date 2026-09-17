"""
 @file
 @brief This file contains the zoom slider QWidget (for interactive zooming/panning on the timeline)
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public  as published by
 the Free Software Foundation, either version 3 of the , or
 (at your option) any later version.

 SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public  for more details.

 You should have received a copy of the GNU General Public 
 along with SmartEdit Library.  If not, see <http://www.gnu.org/s/>.
 """
import copy
import math

from qt_api import (
    Qt, QCoreApplication, QRectF, QTimer, QSize, QPointF
)
from qt_api import modifiers_has
from qt_api import (
    QPainter, QColor, QPen, QBrush, QCursor, QPainterPath, QIcon, QPalette
)
from qt_api import QSizePolicy, QWidget

import smartedit  

from classes import updates


def _event_posf(event):
    if hasattr(event, "position"):
        return event.position()
    return QPointF(event.pos())
from classes.app import get_app
from classes.query import Clip, Track, Transition, Marker
from classes.logger import log


class ZoomSlider(QWidget, updates.UpdateInterface):
    """ A QWidget used to zoom and pan around a Timeline"""

    def sizeHint(self):
        """Preferred size for layouts that host the slider."""
        return QSize(200, 20)

    def minimumSizeHint(self):
        """Allow the slider to shrink horizontally when space is limited."""
        return QSize(0, 20)

    
    def changed(self, action):
        from qt_api import isdeleted
        if isdeleted(self):
            return
        
        if (action and len(action.key) >= 1 and action.key[0].lower() in ["files", "history", "profile"]) or self.ignore_updates:
            return

        
        self.clip_rects.clear()
        self.clip_rects_selected.clear()
        self.marker_rects.clear()

        
        layers = {}
        for count, layer in enumerate(reversed(sorted(Track.filter()))):
            layers[layer.data.get('number')] = count

        
        
        if hasattr(get_app().window, "timeline"):  
            
            project_duration = get_app().project.get("duration")
            pixels_per_second = self.width() / project_duration

            
            vertical_factor = self.height() / len(layers.keys())

            for clip in Clip.filter():
                
                clip_x = (clip.data.get('position', 0.0) * pixels_per_second)
                clip_y = layers.get(clip.data.get('layer', 0), 0) * vertical_factor
                clip_width = ((clip.data.get('end', 0.0) - clip.data.get('start', 0.0))
                              * pixels_per_second)
                clip_rect = QRectF(clip_x, clip_y, clip_width, 1.0 * vertical_factor)
                if clip.id in get_app().window.selected_clips:
                    
                    self.clip_rects_selected.append(clip_rect)
                else:
                    
                    self.clip_rects.append(clip_rect)

            for clip in Transition.filter():
                
                clip_x = (clip.data.get('position', 0.0) * pixels_per_second)
                clip_y = layers.get(clip.data.get('layer', 0), 0) * vertical_factor
                clip_width = ((clip.data.get('end', 0.0) - clip.data.get('start', 0.0))
                              * pixels_per_second)
                clip_rect = QRectF(clip_x, clip_y, clip_width, 1.0 * vertical_factor)
                if clip.id in get_app().window.selected_transitions:
                    
                    self.clip_rects_selected.append(clip_rect)
                else:
                    
                    self.clip_rects.append(clip_rect)

            for marker in Marker.filter():
                
                marker_x = (marker.data.get('position', 0.0) * pixels_per_second)
                marker_rect = QRectF(marker_x, 0, 0.5, len(layers) * vertical_factor)
                self.marker_rects.append(marker_rect)

        
        self.update()

    def paintEvent(self, event, *args):
        """ Custom paint event """
        event.accept()

        
        if get_app().theme_manager:
            theme = get_app().theme_manager.get_current_theme()
            if not theme:
                log.warning("No theme loaded yet. Skip rendering zoom slider widget.")
                return
            playhead_color = theme.get_color(".zoom_slider_playhead", "background-color")
        else:
            log.warning("No ThemeManager loaded yet. Skip rendering zoom slider widget.")

        
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing, True)

        
        base_role = getattr(QPalette, "Base", None)
        if base_role is None:
            base_role = QPalette.ColorRole.Base
        background_color = self.palette().color(base_role)
        painter.fillRect(event.rect(), background_color)

        
        clip_pen = QPen(QBrush(QColor("#53a0ed")), 1.5)
        clip_pen.setCosmetic(True)
        painter.setPen(clip_pen)

        selected_clip_pen = QPen(QBrush(QColor("Red")), 1.5)
        selected_clip_pen.setCosmetic(True)

        scroll_color = QColor("#4053a0ed")
        scroll_pen = QPen(QBrush(scroll_color), 2.0)
        scroll_pen.setCosmetic(True)

        marker_color = QColor("#4053a0ed")
        marker_pen = QPen(QBrush(marker_color), 1.0)
        marker_pen.setCosmetic(True)

        playhead_color = playhead_color
        playhead_pen = QPen(QBrush(playhead_color), 1.0)
        playhead_pen.setCosmetic(True)

        handle_color = QColor("#a653a0ed")
        handle_pen = QPen(QBrush(handle_color), 1.5)
        handle_pen.setCosmetic(True)

        
        layers = Track.filter()

        
        if get_app().window.timeline:
            
            project_duration = get_app().project.get("duration")
            pixels_per_second = event.rect().width() / project_duration
            scroll_width = (self.scrollbar_position[1] - self.scrollbar_position[0]) * event.rect().width()

            
            fps_num = get_app().project.get("fps").get("num", 24)
            fps_den = get_app().project.get("fps").get("den", 1) or 1
            fps_float = float(fps_num / fps_den)

            
            vertical_factor = event.rect().height() / len(layers)

            
            painter.setPen(clip_pen)
            for clip_rect in self.clip_rects:
                painter.drawRect(clip_rect)

            painter.setPen(selected_clip_pen)
            for clip_rect in self.clip_rects_selected:
                painter.drawRect(clip_rect)

            painter.setPen(marker_pen)
            for marker_rect in self.marker_rects:
                painter.drawRect(marker_rect)

            painter.setPen(playhead_pen)
            playhead_x = ((self.current_frame / fps_float) * pixels_per_second)
            playhead_rect = QRectF(playhead_x, 0, 0.5, len(layers) * vertical_factor)
            painter.drawRect(playhead_rect)

            
            if self.scrollbar_position:
                painter.setPen(scroll_pen)

                
                scroll_x = self.scrollbar_position[0] * event.rect().width()
                self.scroll_bar_rect = QRectF(scroll_x, 0.0, scroll_width, event.rect().height())
                scroll_path = QPainterPath()
                scroll_path.addRoundedRect(self.scroll_bar_rect, 6, 6)

                
                painter.fillPath(scroll_path, scroll_color)
                painter.drawPath(scroll_path)

                
                painter.setPen(handle_pen)
                handle_width = 12.0

                
                left_handle_x = (self.scrollbar_position[0] * event.rect().width()) - (handle_width/2.0)
                self.left_handle_rect = QRectF(left_handle_x, event.rect().height() / 4.0, handle_width, event.rect().height() / 2.0)
                left_handle_path = QPainterPath()
                left_handle_path.addRoundedRect(self.left_handle_rect, handle_width, handle_width)
                painter.fillPath(left_handle_path, handle_color)

                
                right_handle_x = self.scroll_bar_rect.right() - (handle_width/2.0)
                right_handle_x = min(right_handle_x, event.rect().width() - (handle_width/2.0))
                self.right_handle_rect = QRectF(right_handle_x, event.rect().height() / 4.0, handle_width, event.rect().height() / 2.0)
                right_handle_path = QPainterPath()
                right_handle_path.addRoundedRect(self.right_handle_rect, handle_width, handle_width)
                painter.fillPath(right_handle_path, handle_color)

            
            if get_app().window.preview_thread.player.Mode() == smartedit.PLAYBACK_PLAY and self.is_auto_center:
                if not self.scroll_bar_rect.contains(playhead_rect):
                    get_app().window.TimelineCenter.emit()

        
        painter.end()

    def zoomToTimeline(self):
        """Toggle between zooming to the entire timeline and the previous zoom"""
        
        if math.isclose(self.scrollbar_position[0], 0.0, abs_tol=1e-9) and math.isclose(self.scrollbar_position[1], 1.0, abs_tol=1e-9):
            
            self.scrollbar_position[0] = self.scrollbar_zoom_previous[0]
            self.scrollbar_position[1] = self.scrollbar_zoom_previous[1]
        else:
            
            self.scrollbar_zoom_previous = copy.deepcopy(self.scrollbar_position)
            self.scrollbar_position[0] = 0.0
            self.scrollbar_position[1] = 1.0
        self.delayed_resize_callback()

    def mouseDoubleClickEvent(self, event):
        self.zoomToTimeline()
        self.mouse_dragging = True  
        event.accept()

    def mousePressEvent(self, event):
        """Capture mouse press event"""
        event.accept()
        self.mouse_pressed = True
        self.mouse_dragging = False
        self.mouse_position = _event_posf(event).x()
        self.scrollbar_position_previous = list(self.scrollbar_position)  

    def mouseReleaseEvent(self, event):
        """Capture mouse release event"""
        event.accept()
        posf = _event_posf(event)

        
        if not self.mouse_dragging and not self.scroll_bar_rect.contains(posf):
            
            click_pos = posf.x() / self.width()
            selection_width = self.scrollbar_position[1] - self.scrollbar_position[0]
            half_width = selection_width / 2

            
            new_left_pos = click_pos - half_width
            new_right_pos = click_pos + half_width

            
            if new_left_pos < 0.0:
                diff = -new_left_pos
                new_left_pos = 0.0
                new_right_pos = min(1.0, new_right_pos + diff)

            
            if new_right_pos > 1.0:
                diff = new_right_pos - 1.0
                new_right_pos = 1.0
                new_left_pos = max(0.0, new_left_pos - diff)

            
            self.scrollbar_position = [new_left_pos, new_right_pos, self.scrollbar_position[2], self.scrollbar_position[3]]

            
            self.delayed_resize_callback()
            self.update()

        
        self.mouse_pressed = False
        self.mouse_dragging = False
        self.left_handle_dragging = False
        self.right_handle_dragging = False
        self.scroll_bar_dragging = False
        self.create_bar_dragging = False
        self._emit_pending_zoom()
        self.update()

    def set_handle_limits(self, left_handle, right_handle, is_left=False):
        """Set min/max limits on the bounds of the handles (to prevent invalid values)"""
        if left_handle < 0.0:
            left_handle = 0.0
            right_handle = self.scroll_bar_rect.width() / self.width()
        if right_handle > 1.0:
            left_handle = 1.0 - (self.scroll_bar_rect.width() / self.width())
            right_handle = 1.0

        
        diff = right_handle - left_handle

        
        if is_left and diff < self.min_distance:
            left_handle = right_handle - self.min_distance
        elif not is_left and diff < self.min_distance:
            right_handle = left_handle + self.min_distance

        return left_handle, right_handle

    def mouseMoveEvent(self, event):
        """Capture mouse events"""
        event.accept()
        posf = _event_posf(event)

        
        mouse_pos = posf.x()
        if mouse_pos < 0:
            mouse_pos = 0
        elif mouse_pos > self.width():
            mouse_pos = self.width()

        
        drag_threshold = 5
        if not self.mouse_dragging:
            if self.left_handle_rect.contains(posf):
                self.setCursor(self.cursors.get('resize_x'))
            elif self.right_handle_rect.contains(posf):
                self.setCursor(self.cursors.get('resize_x'))
            elif self.scroll_bar_rect.contains(posf):
                self.setCursor(self.cursors.get('move'))
            else:
                self.setCursor(Qt.ArrowCursor)

        
        if self.mouse_pressed and not self.mouse_dragging:
            self.mouse_dragging = True
            if self.left_handle_rect.contains(posf):
                self.left_handle_dragging = True
            elif self.right_handle_rect.contains(posf):
                self.right_handle_dragging = True
            elif self.scroll_bar_rect.contains(posf):
                self.scroll_bar_dragging = True
            elif abs(self.mouse_position - mouse_pos) > drag_threshold:
                
                self.create_bar_dragging = True
            else:
                self.mouse_dragging = False

        
        if self.mouse_dragging:
            if self.left_handle_dragging:
                
                delta = (self.mouse_position - mouse_pos) / self.width()
                new_left_pos = self.scrollbar_position_previous[0] - delta
                is_left = True

                if modifiers_has(QCoreApplication.instance().keyboardModifiers(), Qt.ShiftModifier):
                    
                    if (self.scrollbar_position_previous[1] + delta) - new_left_pos > self.min_distance:
                        new_right_pos = self.scrollbar_position_previous[1] + delta
                    else:
                        midpoint = (self.scrollbar_position_previous[1] + self.scrollbar_position_previous[0]) / 2
                        new_right_pos = midpoint + (self.min_distance / 2)
                        new_left_pos = midpoint - (self.min_distance / 2)
                else:
                    new_right_pos = self.scrollbar_position_previous[1]

                
                new_left_pos, new_right_pos = self.set_handle_limits(new_left_pos, new_right_pos, is_left)

                self.scrollbar_position = [new_left_pos, new_right_pos, self.scrollbar_position[2], self.scrollbar_position[3]]
                self.delayed_resize_callback()

            elif self.right_handle_dragging:
                
                delta = (self.mouse_position - mouse_pos) / self.width()
                new_right_pos = self.scrollbar_position_previous[1] - delta
                is_left = False

                if modifiers_has(QCoreApplication.instance().keyboardModifiers(), Qt.ShiftModifier):
                    
                    if new_right_pos - (self.scrollbar_position_previous[0] + delta) > self.min_distance:
                        new_left_pos = self.scrollbar_position_previous[0] + delta
                    else:
                        midpoint = (self.scrollbar_position_previous[1] + self.scrollbar_position_previous[0]) / 2
                        new_right_pos = midpoint + (self.min_distance / 2)
                        new_left_pos = midpoint - (self.min_distance / 2)
                else:
                    new_left_pos = self.scrollbar_position_previous[0]

                
                new_left_pos, new_right_pos = self.set_handle_limits(new_left_pos, new_right_pos, is_left)

                self.scrollbar_position = [new_left_pos, new_right_pos, self.scrollbar_position[2], self.scrollbar_position[3]]
                self.delayed_resize_callback()

            elif self.scroll_bar_dragging:
                
                delta = (self.mouse_position - mouse_pos) / self.width()
                new_left_pos = self.scrollbar_position_previous[0] - delta
                new_right_pos = self.scrollbar_position_previous[1] - delta

                
                new_left_pos, new_right_pos = self.set_handle_limits(new_left_pos, new_right_pos)

                self.scrollbar_position = [new_left_pos, new_right_pos, self.scrollbar_position[2], self.scrollbar_position[3]]
                get_app().window.TimelineScroll.emit(new_left_pos)

            elif self.create_bar_dragging:
                
                new_pos = mouse_pos / self.width()

                if self.mouse_position < mouse_pos:
                    
                    
                    new_left_pos = self.mouse_position / self.width()
                    new_right_pos = new_pos
                else:
                    
                    
                    new_right_pos = self.mouse_position / self.width()
                    new_left_pos = new_pos

                
                new_left_pos, new_right_pos = self.set_handle_limits(new_left_pos, new_right_pos)
                self.scrollbar_position = [new_left_pos, new_right_pos, self.scrollbar_position[2], self.scrollbar_position[3]]
                self.delayed_resize_callback()

            
            self.update()

    def resizeEvent(self, event):
        """Widget resize event"""
        event.accept()
        self.delayed_size = self.size()
        self.delayed_resize_timer.start()

    def get_scroll_width(self):
        """Calculate the width of the scrollbar handle (i.e. selection width)"""
        
        project_duration = get_app().project.get("duration")

        
        timeline_pixels_per_second = 100.0 / get_app().project.get("scale")
        timeline_project_width = project_duration * timeline_pixels_per_second
        scroll_ratio = self.scrollbar_position[3] / timeline_project_width
        scroll_width = scroll_ratio * self.width()
        scroll_width = min(scroll_width, self.width())
        return scroll_width, scroll_ratio

    def delayed_resize_callback(self):
        """Callback for resize event timer (to delay the resize event, and prevent lots of similar resize events)"""
        
        project_duration = get_app().project.get("duration")
        normalized_scroll_width = self.scrollbar_position[1] - self.scrollbar_position[0]
        scroll_width_seconds = normalized_scroll_width * project_duration
        tick_pixels = 100
        if self.scrollbar_position[3] > 0.0:
            
            zoom_factor = scroll_width_seconds / (self.scrollbar_position[3] / tick_pixels)

            
            if zoom_factor > 0.0:
                self.setZoomFactor(zoom_factor)

    
    def wheelEvent(self, event):
        event.accept()

        
        self.update()

    def setZoomFactor(self, zoom_factor, center=False, emit=True):
        """Set the current zoom factor (do not clamp width here — backend owns authoritative geometry)."""
        self.zoom_factor = zoom_factor
        if emit:
            if not self._apply_zoom_to_backend(self.zoom_factor):
                get_app().window.TimelineZoom.emit(self.zoom_factor)
            else:
                self._pending_zoom_emit = self.zoom_factor
                self._pending_scroll_emit = list(self.scrollbar_position)
                if self.mouse_dragging:
                    self._zoom_emit_timer.stop()
                else:
                    self._zoom_emit_timer.start()
        if center:
            get_app().window.TimelineCenter.emit()

        
        self.update()

    def _apply_zoom_to_backend(self, zoom_factor):
        """Apply zoom directly to the QWidget timeline during slider drags."""
        timeline = getattr(self.win, "timeline", None)
        if not timeline or not hasattr(timeline, "_apply_external_zoom"):
            return False

        self._syncing_backend = True
        try:
            timeline._apply_external_zoom(zoom_factor)
        finally:
            self._syncing_backend = False
        return True

    def _emit_pending_zoom(self):
        """Persist slider-driven zoom once the gesture settles."""
        if self._pending_zoom_emit is None and self._pending_scroll_emit is None:
            return

        zoom_factor = (
            float(self._pending_zoom_emit)
            if self._pending_zoom_emit is not None
            else None
        )
        self._pending_zoom_emit = None
        self._pending_scroll_emit = None

        if zoom_factor is not None:
            current_scale = float(get_app().project.get("scale") or 15.0)
            if abs(zoom_factor - current_scale) > 1e-6:
                get_app().updates.ignore_history = True
                get_app().updates.update(["scale"], zoom_factor)
                get_app().updates.ignore_history = False

        timeline = getattr(self.win, "timeline", None)
        if timeline and hasattr(timeline, "scrollbar_position"):
            self.scrollbar_position = list(timeline.scrollbar_position)
            self.update()

    def zoomIn(self):
        """Zoom into timeline"""
        if self.zoom_factor >= 10.0:
            new_factor = self.zoom_factor - 5.0
        elif self.zoom_factor >= 4.0:
            new_factor = self.zoom_factor - 2.0
        else:
            new_factor = self.zoom_factor * 0.8

        
        self.setZoomFactor(new_factor, center=True)

    def zoomOut(self):
        """Zoom out of timeline"""
        if self.zoom_factor >= 10.0:
            new_factor = self.zoom_factor + 5.0
        elif self.zoom_factor >= 4.0:
            new_factor = self.zoom_factor + 2.0
        else:
            
            new_factor = min(self.zoom_factor * 1.25, 4.0)

        
        self.setZoomFactor(new_factor, center=True)

    def update_scrollbars(self, new_positions):
        """Consume the current scroll bar positions from the timeline view."""
        if self.mouse_dragging:
            return

        self.scrollbar_position = new_positions

        
        if not self.clip_rects:
            self.changed(None)

        
        self.is_auto_center = False

        
        self.update()

    def handle_selection(self):
        
        self.changed(None)
        self.update()

    def timeline_resized(self):
        
        self.update()
        self.delayed_resize_timer.start()

    def update_playhead_pos(self, currentFrame):
        """Callback when position is changed"""
        self.current_frame = currentFrame

        
        self.update()

    def handle_play(self):
        """Callback when play button is clicked"""
        self.is_auto_center = True

    def connect_playback(self):
        """Connect playback signals"""
        self.win.preview_thread.position_changed.connect(self.update_playhead_pos)
        self.win.PlaySignal.connect(self.handle_play)

    def ignore_updates_callback(self, ignore, show_wait=True):
        """Ignore updates callback - used to stop updating this widget during batch updates"""
        if not ignore and self.ignore_updates:
            
            self.ignore_updates = ignore
            self.changed(None)
            self.update()
        self.ignore_updates = ignore

    def __init__(self, *args):
        
        super().__init__(*args)

        
        _ = get_app()._tr

        
        self.leftHandle = None
        self.rightHandle = None
        self.centerHandle = None
        self.mouse_pressed = False
        self.mouse_dragging = False
        self.mouse_position = None
        self.zoom_factor = 15.0
        self.scrollbar_position = [0.0, 0.0, 0.0, 0.0]
        self.scrollbar_position_previous = [0.0, 0.0, 0.0, 0.0]
        self.scrollbar_zoom_previous = [0.0, 0.2, 0.0, 0.0]
        self.left_handle_rect = QRectF()
        self.left_handle_dragging = False
        self.right_handle_rect = QRectF()
        self.right_handle_dragging = False
        self.scroll_bar_rect = QRectF()
        self.scroll_bar_dragging = False
        self.clip_rects = []
        self.clip_rects_selected = []
        self.marker_rects = []
        self.current_frame = 0
        self.is_auto_center = True
        self.min_distance = 0.002
        self.ignore_updates = False
        self._syncing_backend = False
        self._pending_zoom_emit = None
        self._pending_scroll_emit = None

        
        self.cursors = {}
        for cursor_name in ["move", "resize_x", "hand"]:
            icon = QIcon(":/cursors/cursor_%s.png" % cursor_name)
            self.cursors[cursor_name] = QCursor(icon.pixmap(24, 24))

        
        super().setAttribute(Qt.WA_OpaquePaintEvent)
        super().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        
        get_app().updates.add_listener(self)

        
        self.setMouseTracking(True)

        
        self.win = get_app().window

        
        self.win.TimelineScrolled.connect(self.update_scrollbars)
        self.win.TimelineResize.connect(self.timeline_resized)
        self.win.IgnoreUpdates.connect(self.ignore_updates_callback)
        self.win.TimelineZoom.connect(lambda z: self.setZoomFactor(z, emit=False))

        
        self.win.SelectionChanged.connect(self.handle_selection)

        
        
        self.delayed_size = None
        self.delayed_resize_timer = QTimer(self)
        self.delayed_resize_timer.setInterval(100)
        self.delayed_resize_timer.setSingleShot(True)
        self.delayed_resize_timer.timeout.connect(self.delayed_resize_callback)

        self._zoom_emit_timer = QTimer(self)
        self._zoom_emit_timer.setInterval(50)
        self._zoom_emit_timer.setSingleShot(True)
        self._zoom_emit_timer.timeout.connect(self._emit_pending_zoom)
