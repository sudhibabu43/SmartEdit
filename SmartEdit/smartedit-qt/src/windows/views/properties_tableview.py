"""
 @file
 @brief This file contains the properties tableview, used by the main window
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
import os
import json
import functools
import math
from operator import itemgetter
import uuid

from qt_api import Qt, QRectF, QLocale, pyqtSignal, pyqtSlot, QEvent, QPoint, QPointF, QTimer
from qt_api import isdeleted
from qt_api import get_font_dialog_selection
from qt_api import (
    QIcon, QColor, QBrush, QPen, QPalette, QPixmap,
    QPainter, QPainterPath, QLinearGradient, QFont, QFontInfo, QCursor, QGuiApplication,
)
from qt_api import (
    QTableView, QAbstractItemView, QSizePolicy,
    QHeaderView, QItemDelegate, QStyle, QLabel, QDockWidget,
    QPushButton, QHBoxLayout, QFrame, QScrollArea
)

from classes.logger import log
from classes.app import get_app
from classes import info
from classes.query import Clip, Effect, Transition, File
from classes.thumbnail import GetThumbPath

from windows.models.properties_model import PropertiesModel
from windows.color_picker import ColorPicker
from .menu import StyledContextMenu, populate_keyframe_context_menu

import smartedit


class PropertyDelegate(QItemDelegate):
    def __init__(self, parent=None, *args, **kwargs):

        self.model = kwargs.pop("model", None)
        if not self.model:
            log.error("Cannot create delegate without data model!")

        super().__init__(parent, *args, **kwargs)

        
        self.curve_pixmaps = {
            smartedit.BEZIER: QIcon(":/curves/keyframe-%s.png" % smartedit.BEZIER).pixmap(20, 20),
            smartedit.LINEAR: QIcon(":/curves/keyframe-%s.png" % smartedit.LINEAR).pixmap(20, 20),
            smartedit.CONSTANT: QIcon(":/curves/keyframe-%s.png" % smartedit.CONSTANT).pixmap(20, 20)
            }

    def paint(self, painter, option, index):
        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            
            model = self.model
            row = model.itemFromIndex(index).row()
            selected_label = model.item(row, 0)
            selected_value = model.item(row, 1)
            cur_property = selected_label.data()

            
            property_type = cur_property[1]["type"]
            property_max = cur_property[1]["max"]
            property_min = cur_property[1]["min"]
            readonly = cur_property[1]["readonly"]
            points = cur_property[1]["points"]
            interpolation = cur_property[1]["interpolation"]

            
            if property_type in ["float", "int"]:
                
                current_value = QLocale().system().toDouble(selected_value.text())[0]

                
                if property_min < 0.0:
                    property_shift = 0.0 - property_min
                    property_min += property_shift
                    property_max += property_shift
                    current_value += property_shift

                
                min_max_range = float(property_max) - float(property_min)
                if abs(min_max_range) <= 1e-12:
                    value_percent = 0.0
                else:
                    value_percent = current_value / min_max_range
            else:
                value_percent = 0.0

            
            if get_app().theme_manager:
                theme = get_app().theme_manager.get_current_theme()
                if not theme:
                    log.warning("No theme loaded yet. Skip rendering properties widget.")
                    return
                foreground_color = theme.get_color(".property_value", "foreground-color")
                background_color = theme.get_color(".property_value", "background-color")
            else:
                log.warning("No ThemeManager loaded yet. Skip rendering properties widget.")

            
            painter.setPen(QPen(Qt.NoPen))
            if property_type == "color":
                
                red = int(cur_property[1]["red"]["value"])
                green = int(cur_property[1]["green"]["value"])
                blue = int(cur_property[1]["blue"]["value"])
                painter.setBrush(QColor(red, green, blue))
            else:
                
                state_selected = getattr(QStyle, "State_Selected", None)
                if state_selected is None:
                    state_flag = getattr(QStyle, "StateFlag", None)
                    if state_flag:
                        state_selected = getattr(state_flag, "State_Selected", None)
                if state_selected and option.state & state_selected:
                    painter.setBrush(background_color)
                else:
                    painter.setBrush(background_color)

            if readonly:
                
                painter.setPen(QPen(get_app().window.palette().color(QPalette.Disabled, QPalette.Text)))
            else:
                path = QPainterPath()
                path.addRoundedRect(QRectF(option.rect), 6, 6)
                painter.fillPath(path, background_color)
                painter.drawPath(path)

                
                painter.setBrush(QBrush(QColor("#000000")))
                mask_rect = QRectF(option.rect)
                mask_rect.setWidth(option.rect.width() * value_percent)
                painter.setClipRect(mask_rect, Qt.IntersectClip)

                
                gradient = QLinearGradient(QPointF(option.rect.topLeft()), QPointF(option.rect.topRight()))
                gradient.setColorAt(0, foreground_color)
                gradient.setColorAt(1, foreground_color)

                
                painter.setBrush(gradient)
                path = QPainterPath()
                value_rect = QRectF(option.rect)
                path.addRoundedRect(value_rect, 6, 6)
                painter.fillPath(path, gradient)
                painter.drawPath(path)
                painter.setClipping(False)

                if points > 1:
                    
                    painter.drawPixmap(
                        int(option.rect.x() + option.rect.width() - 30.0),
                        int(option.rect.y() + 4),
                        self.curve_pixmaps[interpolation])

                
                painter.setPen(QPen(Qt.white))

            value = index.data(Qt.DisplayRole)
            if value:
                painter.drawText(option.rect, Qt.AlignCenter, value)
        finally:
            painter.restore()


def _event_posf(event):
    if hasattr(event, "position"):
        return event.position()
    return QPointF(event.pos())


class PropertiesTableView(QTableView):
    """ A Properties Table QWidget used on the main window """
    loadProperties = pyqtSignal(list)

    def _tracked_mask_source_choices(self, current_effect_id=None):
        _ = get_app()._tr
        tracked_effect_choices = []

        for clip in Clip.filter():
            file_id = clip.data.get("file_id")

            clip_icon = None
            for row in range(self.files_model.rowCount()):
                idx = self.files_model.index(row, 0)
                if idx.sibling(row, 5).data() == file_id:
                    clip_icon = idx.data(Qt.DecorationRole)
                    break

            effect_choices = []
            for effect in clip.data.get("effects", []):
                effect_id = effect.get("id")
                if not effect_id:
                    continue
                if current_effect_id and effect_id == current_effect_id:
                    continue
                if not effect.get("has_tracked_object"):
                    continue

                effect_class = effect.get("class_name", "")
                effect_name = effect.get("name") or effect_class or effect.get("id")
                effect_icon = None
                if effect_class:
                    effect_icon = QIcon(QPixmap(os.path.join(
                        info.PATH, "effects", "icons", "%s.png" % effect_class.lower())))

                effect_choices.append({
                    "name": f"{_(effect_name)} ({effect_id})",
                    "value": effect_id,
                    "selected": False,
                    "icon": effect_icon
                })

            if effect_choices:
                tracked_effect_choices.append({
                    "name": clip.data["title"],
                    "value": effect_choices,
                    "selected": False,
                    "icon": clip_icon
                })

        return tracked_effect_choices

    def _is_edit_text(self, event):
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return False

        text = event.text()
        if not text or text.isspace():
            return False

        return text in "0123456789.,-+"

    def _start_edit_on_key(self, event):
        key = event.key()
        is_numeric = self._is_edit_text(event)
        if key not in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) and not is_numeric:
            return False

        index = self.currentIndex()
        if not index.isValid():
            return False

        if index.column() != 1:
            index = index.sibling(index.row(), 1)
            self.setCurrentIndex(index)

        if not (index.flags() & Qt.ItemIsEditable):
            return False

        result = self.edit(index, QAbstractItemView.EditKeyPressed, event)

        
        if result and is_numeric:
            from qt_api import QTimer
            typed_char = event.text()
            def set_initial_value():
                editor = self.indexWidget(index)
                if editor and hasattr(editor, 'setText'):
                    editor.setText(typed_char)
                    editor.setCursorPosition(len(typed_char))
                elif editor and hasattr(editor, 'lineEdit'):
                    
                    editor.lineEdit().setText(typed_char)
                    editor.lineEdit().setCursorPosition(len(typed_char))
            QTimer.singleShot(0, set_initial_value)

        return result

    def event(self, event):
        
        
        if event.type() == QEvent.ShortcutOverride and self.hasFocus():
            key = event.key()
            if key in (Qt.Key_Period, Qt.Key_Comma, Qt.Key_Up, Qt.Key_Down,
                       Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
                event.accept()
                return True
        
        return super().event(event)

    def closeEditor(self, editor, hint):
        """Handle editor closing - restore focus to label column."""
        super().closeEditor(editor, hint)
        
        current_row = self.currentIndex().row()
        if current_row >= 0:
            self.setCurrentIndex(self.clip_properties_model.model.index(current_row, 0))

    def keyPressEvent(self, event):
        if self._start_edit_on_key(event):
            return

        
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            index = self.currentIndex()
            if index.isValid():
                
                if index.column() != 1:
                    index = index.sibling(index.row(), 1)

                
                model = self.clip_properties_model.model
                label_item = model.item(index.row(), 0)
                if label_item and label_item.data() and isinstance(label_item.data(), tuple):
                    cur_property = label_item.data()
                    has_choices = bool(cur_property[1].get("choices"))
                    property_type = cur_property[1].get("type", "")

                    if has_choices or property_type in ["color", "font"]:
                        
                        rect = self.visualRect(index)
                        center = rect.center()
                        global_pos = self.viewport().mapToGlobal(center)
                        self._show_property_menu_at(index, global_pos)
                        return

        super().keyPressEvent(event)

    def _show_property_menu_at(self, index, global_pos):
        """Show the property context menu at a specific position."""
        
        class FakeEvent:
            def __init__(self, gpos, lpos):
                self._global_pos = gpos
                self._local_pos = lpos
            def globalPos(self):
                return self._global_pos
            def pos(self):
                return self._local_pos
            def ignore(self):
                pass

        local_pos = self.viewport().mapFromGlobal(global_pos)
        fake_event = FakeEvent(global_pos, local_pos)
        self.contextMenuEvent(fake_event)

    def start_transaction(self, item):
        """Start a new undo/redo transaction and cache original values."""
        if (
            self.transaction_id
            or not item
            or self.clip_properties_model.ignore_update_signal
        ):
            return

        item_data = item.data()
        if not isinstance(item_data, list):
            return

        self.transaction_id = str(uuid.uuid4())
        get_app().updates.transaction_id = self.transaction_id
        get_app().updates.ignore_history = True

        self.original_data_map = {}

        for item_id, item_type in item_data:
            obj = None
            if item_type == "clip":
                obj = Clip.get(id=item_id)
            elif item_type == "transition":
                obj = Transition.get(id=item_id)
            elif item_type == "effect":
                obj = Effect.get(id=item_id)

            if obj and obj.data:
                self.original_data_map[item_id] = {
                    "type": item_type,
                    "data": json.loads(json.dumps(obj.data)),
                }

    def finalize_transaction(self):
        """Finalize current transaction and add actions to history."""
        if not self.transaction_id:
            return

        for item_id, info in self.original_data_map.items():
            item_type = info.get("type")
            original = info.get("data")
            obj = None
            if item_type == "clip":
                obj = Clip.get(id=item_id)
            elif item_type == "transition":
                obj = Transition.get(id=item_id)
            elif item_type == "effect":
                obj = Effect.get(id=item_id)

            if obj:
                get_app().updates.ignore_history = True
                get_app().updates.transaction_id = self.transaction_id
                obj.save()
                get_app().updates.apply_last_action_to_history(original)
                get_app().updates.ignore_history = False

        get_app().updates.transaction_id = None
        self.transaction_id = None
        self.original_data_map = {}
        self.update_in_progress = False

    def _restore_original_objects(self):
        for item_id, info in self.original_data_map.items():
            item_type = info.get("type")
            original = copy.deepcopy(info.get("data"))
            obj = None
            if item_type == "clip":
                obj = Clip.get(id=item_id)
            elif item_type == "transition":
                obj = Transition.get(id=item_id)
            elif item_type == "effect":
                obj = Effect.get(id=item_id)
            if obj:
                obj.data = original
                obj.save()
        get_app().window.refreshFrameSignal.emit()

    def cancel_transaction(self):
        if not self.transaction_id:
            return
        self._restore_original_objects()
        get_app().updates.transaction_id = None
        get_app().updates.ignore_history = False
        self.transaction_id = None
        self.original_data_map = {}
        self.update_in_progress = False

    def start_property_change(self, item):
        if not item or self.transaction_id or self.clip_properties_model.ignore_update_signal:
            return
        self.start_transaction(item)
        get_app().updates.ignore_history = True

    def finish_live_property_change(self):
        self.finish_property_change()

    def finish_property_change(self):
        if self.transaction_id:
            self.finalize_transaction()
        get_app().updates.ignore_history = False
        self.clip_properties_model.update_model(get_app().window.txtPropertyFilter.text())

    def value_updated_wrapper(self, item):
        """Wrap PropertiesModel.value_updated to manage transactions."""
        if (
            self.clip_properties_model.ignore_update_signal
            or not item
            or item.column() != 1
        ):
            return

        self.start_transaction(item)
        self.update_in_progress = True
        self.clip_properties_model.value_updated(item)
        if not self.mouse_pressed:
            self.finalize_transaction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
        pos = _event_posf(event).toPoint()
        row = self.indexAt(pos).row()
        model = self.clip_properties_model.model
        if model.item(row, 1):
            self.selected_item = model.item(row, 1)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        
        model = self.clip_properties_model.model
        posf = _event_posf(event)
        pos = posf.toPoint()

        
        
        idx = self.indexAt(pos)
        show_slider_cursor = False
        if idx.isValid() and idx.column() == 1:
            label_item = self.clip_properties_model.model.item(idx.row(), 0)
            if label_item:
                prop = label_item.data()
                if prop and isinstance(prop, tuple) and len(prop) > 1:
                    ptype = prop[1].get("type", "")
                    readonly = prop[1].get("readonly", False)
                    show_slider_cursor = ptype in ("float", "int") and not readonly
        if show_slider_cursor:
            self.viewport().setCursor(Qt.SizeHorCursor)
        else:
            self.viewport().unsetCursor()

        if not self.mouse_pressed:
            return

        
        if self.lock_selection and self.prev_row:
            row = self.prev_row
        else:
            pos = _event_posf(event).toPoint()
            row = self.indexAt(pos).row()
            self.prev_row = row
            self.lock_selection = True

        if row is None:
            return

        event.accept()

        if model.item(row, 0):
            self.selected_label = model.item(row, 0)
            self.selected_item = model.item(row, 1)

        
        if (self.selected_label and isdeleted(self.selected_label)) or \
                (self.selected_item and isdeleted(self.selected_item)):
            log.debug("Property has been deleted, skipping")
            self.selected_label = None
            self.selected_item = None

        
        if self.selected_label and self.selected_item and \
                self.selected_label.data() and type(self.selected_label.data()) == tuple:
            
            get_app().updates.ignore_history = True

            
            if not self._is_playing():
                smartedit.Settings.Instance().ENABLE_PLAYBACK_CACHING = False

            
            value_column_x = self.columnViewportPosition(1)
            cursor_value = posf.x() - value_column_x
            value_column_width = self.columnWidth(1)
            if value_column_width <= 0:
                return
            cursor_value_percent = cursor_value / value_column_width

            
            try:
                cur_property = self.selected_label.data()
            except Exception:
                log.debug('Failed to access data on selected label widget')
                return

            if type(cur_property) != tuple:
                log.debug('Failed to access valid data on current selected label widget')
                return

            property_key = cur_property[0]
            property_name = cur_property[1]["name"]
            property_type = cur_property[1]["type"]
            property_max = cur_property[1]["max"]
            property_min = cur_property[1]["min"]
            readonly = cur_property[1]["readonly"]

            
            if readonly:
                return

            
            if property_type in ["float", "int"] and property_name != "Track":

                if self.previous_x == -1:
                    
                    self.diff_length = 10
                    self.previous_x = posf.x()

                
                drag_diff = self.previous_x - posf.x()

                
                self.previous_x = posf.x()

                
                if abs(drag_diff) < self.diff_length:
                    
                    self.diff_length = max(0, self.diff_length - 1)
                    return

                
                if (
                    not self.transaction_id
                    and not self.clip_properties_model.ignore_update_signal
                ):
                    self.start_transaction(self.selected_item)
                self.update_in_progress = True

                
                min_max_range = float(property_max) - float(property_min)

                if min_max_range < 1000.0:
                    
                    self.new_value = property_min + (min_max_range * cursor_value_percent)
                else:
                    

                    
                    if self.new_value is None:
                        self.new_value = QLocale().system().toDouble(self.selected_item.text())[0]
                    step = 1.0 if property_type == "int" else 0.50

                    if drag_diff > 0:
                        
                        self.new_value -= step
                    elif drag_diff < 0:
                        
                        self.new_value += step

                
                self.new_value = max(property_min, self.new_value)
                self.new_value = min(property_max, self.new_value)

                if property_type == "int":
                    if self.new_value >= 0:
                        self.new_value = math.floor(self.new_value + 0.5)
                    else:
                        self.new_value = math.ceil(self.new_value - 0.5)

                
                self.clip_properties_model.value_updated(self.selected_item, -1, self.new_value)

                
                self.viewport().update()

    def leaveEvent(self, event):
        self.viewport().unsetCursor()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        
        event.accept()
        get_app().updates.ignore_history = False
        self.mouse_pressed = False

        log.debug('mouseReleaseEvent: apply_last_action to history')

        if self.update_in_progress:
            self.finalize_transaction()

        
        model = self.clip_properties_model.model
        pos = _event_posf(event).toPoint()
        row = self.indexAt(pos).row()
        if model.item(row, 0):
            self.selected_label = model.item(row, 0)
            self.selected_item = model.item(row, 1)

        
        self.lock_selection = False
        self.previous_x = -1
        self.new_value = None

    @pyqtSlot(QColor)
    def color_callback(self, newColor: QColor):
        
        if newColor.isValid():
            log.debug(f"Color callback received: {newColor.name()}, Alpha: {newColor.alpha()}")
            if not self.clip_properties_model.ignore_update_signal:
                self.start_transaction(self.selected_item)
            self.update_in_progress = True
            self.clip_properties_model.color_update(
                self.selected_item, newColor)
            if not self.mouse_pressed:
                self.finalize_transaction()

    def doubleClickedCB(self, model_index):
        """Double click handler for the property table"""

        
        _ = get_app()._tr

        
        model = self.clip_properties_model.model

        row = model_index.row()
        selected_label = model.item(row, 0)
        self.selected_item = model.item(row, 1)

        if selected_label and selected_label.data() and type(selected_label.data()) == tuple:
            cur_property = selected_label.data()
            property_type = cur_property[1]["type"]

            if property_type == "color":
                
                red = cur_property[1]["red"]["value"]
                green = cur_property[1]["green"]["value"]
                blue = cur_property[1]["blue"]["value"]
                
                alpha = cur_property[1].get("alpha", {}).get("value", 255)

                
                try:
                    
                    currentColor = QColor(int(red), int(green), int(blue), int(alpha))
                except (ValueError, TypeError):
                    
                    currentColor = QColor(255, 0, 0, 255)

                ColorPicker(
                    currentColor, parent=self.win, title=_("Select a Color"),
                    callback=self.color_callback)
                return

            elif property_type == "font":
                
                current_font_name = cur_property[1].get("memo", "sans")
                current_font = QFont(current_font_name)
                font, ok = get_font_dialog_selection(current_font, self.win, _("Change Font"))

                
                if ok and font:
                    fontinfo = QFontInfo(font)
                    
                    font_details = { "font_family": fontinfo.family(),
                                     "font_style": fontinfo.styleName(),
                                     "font_weight": fontinfo.weight(),
                                     "font_size_pixel": fontinfo.pixelSize() }
                    if not self.clip_properties_model.ignore_update_signal:
                        self.start_transaction(self.selected_item)
                    self.update_in_progress = True
                    self.clip_properties_model.value_updated(self.selected_item, value=fontinfo.family())
                    if not self.mouse_pressed:
                        self.finalize_transaction()


    def caption_text_updated(self, new_caption_text, caption_model_row):
        """Caption text has been updated in the caption editor, and needs saving"""
        if caption_model_row is None:
            
            return

        caption_model_label = caption_model_row[0]
        caption_model_value = caption_model_row[1]

        
        if (caption_model_label and isdeleted(caption_model_label)) or \
                (caption_model_value and isdeleted(caption_model_value)):
            log.debug("Property has been deleted, skipping")
            return

        
        cur_property = caption_model_label.data()
        property_type = cur_property[1]["type"]

        
        if property_type == "caption" and cur_property[1].get('memo') != new_caption_text:
            self.start_transaction(caption_model_value)
            self.update_in_progress = True
            self.clip_properties_model.value_updated(caption_model_value, value=new_caption_text)

    def caption_text_committed(self, caption_model_row):
        """Finalize a batch of live Caption editor updates into one undo action."""
        if caption_model_row is None:
            return
        if self.update_in_progress:
            self.finalize_transaction()

    def select_item(self, selection):
        """Update the selected items in the properties window"""

        self.current_selection = list(selection or [])
        self.clip_properties_model.update_item(selection)

    def select_frame(self, frame_number):
        """ Update the values of the selected clip, based on the current frame """

        
        self.clip_properties_model.update_frame(frame_number)

    def filter_changed(self, value=None):
        """ Filter the list of properties """

        
        self.clip_properties_model.update_model(value)

        
        get_app().window.SetKeyframeFilter.emit(value)

    def contextMenuEvent(self, event):
        """ Display context menu """
        
        pos = _event_posf(event).toPoint()
        index = self.indexAt(pos)
        if not index.isValid():
            event.ignore()
            return

        
        idx = self.indexAt(pos)
        row = idx.row()
        selected_label = idx.model().item(row, 0)
        selected_value = idx.model().item(row, 1)
        self.selected_item = selected_value
        self.selected_label = selected_label
        frame_number = self.clip_properties_model.frame_number

        
        cur_property = selected_label.data()
        readonly = cur_property[1]["readonly"]
        if readonly:
            return

        
        _ = get_app()._tr

        
        if selected_label and selected_label.data() and type(selected_label.data()) == tuple:
            cur_property = selected_label.data()

            
            if self.menu_reset:
                self.choices = []
                self.menu_reset = False

            property_name = cur_property[1]["name"]
            self.property_type = cur_property[1]["type"]
            points = cur_property[1]["points"]
            
            
            self.choices = copy.deepcopy(cur_property[1]["choices"])
            property_key = cur_property[0]

            for item_id, item_type in selected_value.data():
                log.info("Context menu shown for %s (%s) for item %s on frame %s" % (property_name, property_key, item_id, frame_number))
                log.info("Points: %s" % points)

                
                if property_key == "parent_effect_id" and not self.choices:
                    
                    effect = Effect.get(id=item_id)
                    if not effect:
                        return

                    
                    clip_choices = []
                    for clip in Clip.filter():
                        file_id = clip.data.get("file_id")

                        
                        parent_clip_id = effect.parent.get("id")

                        
                        if clip.id != parent_clip_id:
                            
                            for file_index in range(self.files_model.rowCount()):
                                file_row = self.files_model.index(file_index, 0)
                                project_file_id = file_row.sibling(file_index, 5).data()
                                if file_id == project_file_id:
                                    clip_instance_icon = file_row.data(Qt.DecorationRole)
                                    break

                            effect_choices = []
                            
                            for clip_effect_data in clip.data["effects"]:
                                
                                if clip_effect_data['class_name'] == effect.data['class_name']:
                                    effect_id = clip_effect_data["id"]
                                    effect_icon = QIcon(QPixmap(os.path.join(info.PATH, "effects", "icons", "%s.png" % clip_effect_data['class_name'].lower())))
                                    effect_choices.append({"name": effect_id,
                                                    "value": effect_id,
                                                    "selected": False,
                                                    "icon": effect_icon})
                            if effect_choices:
                                clip_choices.append({"name": _(clip.data["title"]),
                                                    "value": effect_choices,
                                                    "selected": False,
                                                    "icon": clip_instance_icon})

                    self.choices.append({"name": _("None"), "value": "None", "selected": False, "icon": None})
                    if clip_choices:
                        self.choices.append({"name": _("Clips"), "value": clip_choices, "selected": False, "icon": None})

                
                if property_key in ["selected_object_index", "class_filter"] and not self.choices:
                    if property_key == "class_filter":
                        
                        tracked_object_menu_name = _("Tracked Classes")
                        self.choices.append({"name": _("Clear"), "value": "", "selected": False, "icon": None})
                    else:
                        tracked_object_menu_name = _("Tracked Objects")

                    
                    timeline_instance = get_app().window.timeline_sync.timeline
                    
                    effect = timeline_instance.GetClipEffect(item_id)
                    
                    visible_objects = json.loads(effect.GetVisibleObjects(frame_number))
                    
                    object_index_choices = []
                    for enum_index, object_index in enumerate(visible_objects["visible_objects_index"]):
                        class_name = visible_objects["visible_class_names"][enum_index]
                        object_name = f"{class_name}: {object_index}"
                        object_value = f"{object_index}"
                        skip_choice = False
                        if property_key == "class_filter":
                            
                            tracked_object_menu_name = _("Tracked Classes")
                            object_name = f"{class_name}"
                            object_value = f"{class_name}"
                            skip_choice = any(d.get('name') == class_name for d in object_index_choices)

                        if not skip_choice:
                            object_index_choices.append({
                                        "name": object_name,
                                        "value": object_value,
                                        "selected": False,
                                        "icon": None
                                    })
                    if object_index_choices:
                        self.choices.append({"name": tracked_object_menu_name, "value": object_index_choices, "selected": False, "icon": None})

                
                if property_key in ["parentObjectId"] and not self.choices:
                    
                    tracked_choices = []
                    clip_choices = []
                    
                    timeline_instance = get_app().window.timeline_sync.timeline
                    
                    for clip in Clip.filter():
                        file_id = clip.data.get("file_id")

                        
                        parent_clip_id = item_id
                        if item_type == "effect":
                            parent_clip_id = Effect.get(id=item_id).parent.get("id")
                            log.debug(f"Lookup parent clip ID for effect: '{item_id}' = '{parent_clip_id}'")

                        
                        if clip.id == parent_clip_id:
                            continue

                        
                        clip_icon = None
                        for row in range(self.files_model.rowCount()):
                            idx = self.files_model.index(row, 0)
                            if idx.sibling(row, 5).data() == file_id:
                                clip_icon = idx.data(Qt.DecorationRole)
                                break

                        
                        clip_choices.append({
                            "name": clip.data["title"],
                            "value": clip.id,
                            "selected": False,
                            "icon": clip_icon
                        })

                        
                        tracked_objects = []
                        for effect in clip.data["effects"]:
                            if effect.get("has_tracked_object"):
                                eff_inst = timeline_instance.GetClipEffect(effect["id"])
                                visible = json.loads(eff_inst.GetVisibleObjects(frame_number))
                                
                                for obj_id in visible["visible_objects_id"]:
                                    tracked_objects.append({
                                        "name": obj_id,
                                        "value": obj_id,
                                        "selected": False,
                                        "icon": None
                                    })

                        if tracked_objects:
                            tracked_choices.append({
                                "name": clip.data["title"],
                                "value": tracked_objects,
                                "selected": False,
                                "icon": clip_icon
                            })

                    
                    self.choices.append({"name": _("None"), "value": "None", "selected": False, "icon": None})
                    if tracked_choices:
                        self.choices.append({
                            "name": _("Tracked Objects"),
                            "value": tracked_choices,
                            "selected": False,
                            "icon": None
                        })
                    if clip_choices:
                        self.choices.append({
                            "name": _("Clips"),
                            "value": clip_choices,
                            "selected": False,
                            "icon": None
                        })

                
                if property_key == "mask_source_id" and not self.choices:
                    tracked_effect_choices = self._tracked_mask_source_choices(item_id)

                    self.choices.append({"name": _("None"), "value": "", "selected": False, "icon": None})
                    if tracked_effect_choices:
                        self.choices.append({
                            "name": _("Tracked Objects"),
                            "value": tracked_effect_choices,
                            "selected": False,
                            "icon": None
                        })

            
            if self.property_type == "reader" and not self.choices:
                
                file_choices = []
                for i in range(self.files_model.rowCount()):
                    idx = self.files_model.index(i, 0)
                    if not idx.isValid():
                        continue
                    icon = idx.data(Qt.DecorationRole)
                    name = idx.sibling(i, 1).data()
                    file_id = idx.sibling(i, 5).data()
                    file_obj = File.get(id=file_id) if file_id else None
                    path = file_obj.absolute_path() if file_obj else ""
                    if not path:
                        continue
                    file_data = getattr(file_obj, "data", {}) or {}

                    
                    file_choices.append({"name": name,
                                         "value": {
                                             "file_id": file_id,
                                             "path": path,
                                             "start": file_data.get("start"),
                                             "end": file_data.get("end"),
                                         },
                                         "selected": False,
                                         "icon": icon
                                         })

                
                self.choices.append({"name": _("None"), "value": "", "selected": False, "icon": None})


                
                if file_choices:
                    self.choices.append({"name": _("Files"), "value": file_choices, "selected": False, "icon": None})

                
                trans_choices = []
                for i in range(self.transition_model.rowCount()):
                    idx = self.transition_model.index(i, 0)
                    if not idx.isValid():
                        continue
                    icon = idx.data(Qt.DecorationRole)
                    name = idx.sibling(i, 1).data()
                    path = idx.sibling(i, 3).data()

                    
                    trans_choices.append({"name": name,
                                          "value": path,
                                          "selected": False,
                                          "icon": icon
                                          })

                
                self.choices.append({"name": _("Transitions"), "value": trans_choices, "selected": False})

            elif property_key == "lut_path":
                self.choices = [{"name": _("None"), "value": "", "selected": False, "icon": None}]

                def _gather(dir_path):
                    try:
                        names = sorted(os.listdir(dir_path), key=str.lower)
                    except OSError:
                        return []
                    result = []
                    for name in names:
                        full = os.path.join(dir_path, name)
                        pretty = _(name.replace("_", " ").title()).replace("&", "&&")
                        if os.path.isdir(full):
                            
                            children = [
                                {"name": _(os.path.splitext(fn)[0]
                                           .replace("_", " ")
                                           .title()).replace("&", "&&"),
                                 "value": os.path.join(full, fn),
                                 "selected": False,
                                 "icon": None}
                                for fn in sorted(os.listdir(full), key=str.lower)
                                if fn.lower().endswith(".cube")
                            ]
                            if children:
                                result.append({"name": pretty, "value": children})
                        elif name.lower().endswith(".cube"):
                            
                            result.append({
                                "name": pretty,
                                "value": full,
                                "selected": False,
                                "icon": None
                            })
                    return result

                
                user_choices = _gather(info.USER_COLORS_PATH)
                if user_choices:
                    self.choices.append({"name": _("User-Defined"), "value": user_choices})

                
                self.choices.extend(_gather(info.COLORS_PATH))

            
            if property_name == "Track" and self.property_type == "int" and not self.choices:
                
                all_tracks = get_app().project.get("layers")
                display_count = len(all_tracks)
                for track in reversed(sorted(all_tracks, key=itemgetter('number'))):
                    
                    track_name = track.get("label") or _("Track %s") % QLocale().toString(display_count)
                    self.choices.append({"name": track_name, "value": track.get("number"), "selected": False, "icon": None})
                    display_count -= 1

            elif self.property_type == "font":
                
                current_font_name = cur_property[1].get("memo", "sans")
                current_font = QFont(current_font_name)
                font, ok = get_font_dialog_selection(current_font, self.win, _("Change Font"))

                
                if ok and font:
                    fontinfo = QFontInfo(font)
                    self.clip_properties_model.value_updated(self.selected_item, value=fontinfo.family())

            
            menu = StyledContextMenu(parent=self)
            if self.property_type == "color":
                Color_Action = menu.addAction(_("Select a Color"))
                Color_Action.triggered.connect(functools.partial(self.Color_Picker_Triggered, cur_property))
                menu.addSeparator()
            if points > 1:
                
                populate_keyframe_context_menu(
                    menu,
                    bezier_callback=self.Bezier_Action_Triggered,
                    linear_callback=self.Linear_Action_Triggered,
                    constant_callback=self.Constant_Action_Triggered,
                    bezier_icon=self.bezier_icon,
                    linear_icon=self.linear_icon,
                    constant_icon=self.constant_icon,
                )
                menu.addSeparator()
            if points >= 1:
                
                Insert_Action = menu.addAction(_("Insert Keyframe"))
                Insert_Action.triggered.connect(self.Insert_Action_Triggered)
                Remove_Action = menu.addAction(_("Remove Keyframe"))
                Remove_Action.triggered.connect(self.Remove_Action_Triggered)
                menu.addSeparator()

            
            log.debug(f"Context menu choices: {self.choices}")
            self.menu = self.build_menu(self.choices, menu)

            
            
            if len(self.menu.children()) > 1:
                self.menu.show_at(event)
                
                actions = self.menu.actions()
                if actions:
                    self.menu.setActiveAction(actions[0])

    def build_menu(self, data, parent_menu=None):
        """Build a Context Menu, included nested sub-menus, and divide lists if too large"""
        if parent_menu is None:
            parent_menu = StyledContextMenu(parent=self)

        
        _ = get_app()._tr

        SubMenuSize = 25
        for choice in data:
            if isinstance(choice["value"], list) and choice["value"]:
                log.info("Add submenu: " + choice["name"])
                if choice.get("icon"):
                    SubMenuRoot = parent_menu.addMenu(QIcon(choice["icon"]), choice["name"])
                else:
                    SubMenuRoot = parent_menu.addMenu(choice["name"])

                
                if len(choice["value"]) > SubMenuSize:
                    for i in range(0, len(choice["value"]), SubMenuSize):
                        range_label = f"{i + 1}-{min(i + SubMenuSize, len(choice['value']))}"
                        SubMenu = SubMenuRoot.addMenu(range_label)
                        self.build_menu(choice["value"][i:i + SubMenuSize], SubMenu)
                else:
                    self.build_menu(choice["value"], SubMenuRoot)
            else:
                
                log.info(" - Add choice: " + choice["name"])
                Choice_Action = parent_menu.addAction(_(choice["name"]))
                if choice.get("icon"):
                    Choice_Action.setIcon(QIcon(choice["icon"]))
                Choice_Action.setData(choice["value"])
                Choice_Action.triggered.connect(self.Choice_Action_Triggered)

        return parent_menu

    def Bezier_Action_Triggered(self, preset=[]):
        log.info("Bezier_Action_Triggered: %s" % str(preset))
        if self.property_type != "color":
            
            self.clip_properties_model.value_updated(self.selected_item, interpolation=0, interpolation_details=preset)
        else:
            
            self.clip_properties_model.color_update(self.selected_item, QColor("#000"), interpolation=0, interpolation_details=preset)

    def Linear_Action_Triggered(self):
        log.info("Linear_Action_Triggered")
        if self.property_type != "color":
            
            self.clip_properties_model.value_updated(self.selected_item, interpolation=1)
        else:
            
            self.clip_properties_model.color_update(self.selected_item, QColor("#000"), interpolation=1, interpolation_details=[])

    def Constant_Action_Triggered(self):
        log.info("Constant_Action_Triggered")
        if self.property_type != "color":
            
            self.clip_properties_model.value_updated(self.selected_item, interpolation=2)
        else:
            
            self.clip_properties_model.color_update(self.selected_item, QColor("#000"), interpolation=2, interpolation_details=[])

        if not self.mouse_pressed:
            self.finalize_transaction()

    def Color_Picker_Triggered(self, cur_property):
        log.info("Color_Picker_Triggered")

        _ = get_app()._tr

        
        red = int(cur_property[1]["red"]["value"])
        green = int(cur_property[1]["green"]["value"])
        blue = int(cur_property[1]["blue"]["value"])
        
        alpha = int(cur_property[1].get("alpha", {}).get("value", 255))

        
        try:
            
            currentColor = QColor(red, green, blue, alpha)
        except (ValueError, TypeError):
            
            currentColor = QColor(255, 0, 0, 255)

        ColorPicker(
            currentColor, parent=self.win, title=_("Select a Color"),
            callback=self.color_callback)

    def Insert_Action_Triggered(self):
        log.info("Insert_Action_Triggered")

        
        if (self.selected_label and isdeleted(self.selected_label)) or \
                (self.selected_item and isdeleted(self.selected_item)):
            log.debug("Property has been deleted, skipping")
            self.selected_label = None
            self.selected_item = None

        if self.selected_item:
            self.clip_properties_model.insert_keyframe(self.selected_item)

    def Remove_Action_Triggered(self):
        log.info("Remove_Action_Triggered")
        if not self.clip_properties_model.ignore_update_signal:
            self.start_transaction(self.selected_item)
        self.update_in_progress = True
        self.clip_properties_model.remove_keyframe(self.selected_item)
        if not self.mouse_pressed:
            self.finalize_transaction()

    def Choice_Action_Triggered(self):
        log.info("Choice_Action_Triggered")
        choice_value = self.sender().data()

        
        if not self.clip_properties_model.ignore_update_signal:
            self.start_transaction(self.selected_item)
        self.update_in_progress = True
        self.clip_properties_model.value_updated(self.selected_item, value=choice_value)
        if not self.mouse_pressed:
            self.finalize_transaction()

        
        current_row = self.currentIndex().row()
        if current_row >= 0:
            self.setCurrentIndex(self.clip_properties_model.model.index(current_row, 0))

    def refresh_menu(self):
        """ Ensure we update the menu when our source models change """
        self.menu_reset = True

    def __init__(self, *args):
        
        QTableView.__init__(self, *args)

        
        self.win = get_app().window

        
        self.clip_properties_model = PropertiesModel(self)

        
        try:
            self.clip_properties_model.model.itemChanged.disconnect(
                self.clip_properties_model.value_updated
            )
        except (TypeError, RuntimeError) as ex:
            log.debug("Failed to disconnect itemChanged: %s", ex)
        self.clip_properties_model.model.itemChanged.connect(self.value_updated_wrapper)

        
        self.transition_model = self.win.transition_model.model
        self.files_model = self.win.files_model.model

        
        self.files_model.dataChanged.connect(self.refresh_menu)
        self.win.files_model.ModelRefreshed.connect(self.refresh_menu)
        self.win.transition_model.ModelRefreshed.connect(self.refresh_menu)
        self.menu_reset = False

        
        self.selected = []
        self.selected_label = None
        self.selected_item = None
        self.new_value = None
        self.original_data = None
        self.original_data_map = {}
        self.transaction_id = None
        self.update_in_progress = False
        self.mouse_pressed = False
        self.lock_selection = False
        self.prev_row = None
        self.menu = None
        self.current_selection = []

        
        self.bezier_icon = QIcon(QPixmap(os.path.join(info.IMAGES_PATH, "keyframe-%s.png" % smartedit.BEZIER)))
        self.linear_icon = QIcon(QPixmap(os.path.join(info.IMAGES_PATH, "keyframe-%s.png" % smartedit.LINEAR)))
        self.constant_icon = QIcon(QPixmap(os.path.join(info.IMAGES_PATH, "keyframe-%s.png" % smartedit.CONSTANT)))

        
        self.setModel(self.clip_properties_model.model)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setWordWrap(True)

        
        delegate = PropertyDelegate(model=self.clip_properties_model.model)
        self.setItemDelegateForColumn(1, delegate)
        self.previous_x = -1

        
        self.viewport().setMouseTracking(True)

        
        horizontal_header = self.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.Stretch)
        vertical_header = self.verticalHeader()
        vertical_header.setVisible(False)

        
        self.clip_properties_model.update_model()

        
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

        
        get_app().window.txtPropertyFilter.textChanged.connect(self.filter_changed)
        get_app().window.InsertKeyframe.connect(self.Insert_Action_Triggered)
        self.doubleClicked.connect(self.doubleClickedCB)
        self.loadProperties.connect(self.select_item)
        get_app().window.CaptionTextUpdated.connect(self.caption_text_updated)
        get_app().window.CaptionTextCommitted.connect(self.caption_text_committed)


    def _show_scope_docks_if_hidden(self):
        """Show scope docks if currently hidden."""
        win = self.win
        for attr in ("dockAudio",):
            dock = getattr(win, attr, None)
            if dock and not dock.isVisible():
                dock.show()

            return

        available = screen.availableGeometry()
        min_x = available.left()
        max_x = available.right() - dialog_size.width() + 1
        x = max(min_x, min(x, max_x))

        min_y = available.top()
        if y < min_y:
            y = self.viewport().mapToGlobal(rect.bottomLeft()).y() + 6
            max_y = available.bottom() - dialog_size.height() + 1
            y = max(min_y, min(y, max_y))

        dialog.move(x, y)


class SelectionLabel(QFrame):
    """ The label to display selections """

    def getMenu(self):
        
        menu = StyledContextMenu(parent=self)

        
        _ = get_app()._tr

        
        if self.item_type == "clip":
            item = Clip.get(id=self.item_id)
            if item:
                self.item_name = item.title()
        elif self.item_type == "transition":
            item = Transition.get(id=self.item_id)
            if item:
                self.item_name = item.title()
        elif self.item_type == "effect":
            item = Effect.get(id=self.item_id)
            if item:
                self.item_name = item.title()

        
        selection = self.all_selection if self.all_selection else get_app().window.selected_items
        if not selection:
            return None

        
        if len(selection) > 1:
            label = _("%d selections") % len(selection)
            action = menu.addAction(label)
            action.setData({'selection': list(selection)})
            action.triggered.connect(self.Action_Triggered)
            menu.addSeparator()

        
        
        cursor_set = False
        count = 0
        try:
            for selected in selection:
                count += 1
                if count > 10 and not cursor_set:
                    get_app().setOverrideCursor(QCursor(Qt.WaitCursor))
                    cursor_set = True
                elif cursor_set and count % 10 == 0:
                    get_app().processEvents()

                item_id = selected['id']
                item_type = selected['type']

                if item_type == "clip":
                    clip = Clip.get(id=item_id)
                    if not clip:
                        continue
                    item_name = clip.title()

                    
                    file_id = clip.data.get("file_id")
                    file = File.get(id=file_id)
                    if not file:
                        continue

                    
                    media_type = file.data.get("media_type")
                    if media_type in ["video", "image"]:
                        
                        fps = file.data["fps"]
                        fps_float = float(fps["num"]) / float(fps["den"])
                        thumbnail_frame = round(float(clip.data['start']) * fps_float) + 1
                        thumb_icon = QIcon(GetThumbPath(file.id, thumbnail_frame))
                    else:
                        
                        thumb_icon = QIcon(os.path.join(info.PATH, "images", "AudioThumbnail.svg"))

                    action = menu.addAction(thumb_icon, item_name)
                    action.setData({'item_id': item_id, 'item_type': 'clip'})
                    action.triggered.connect(self.Action_Triggered)

                    for effect_info in clip.data.get('effects', []):
                        effect = Effect.get(id=effect_info.get('id'))
                        if not effect:
                            continue
                        effect_name = effect.title()
                        effect_icon = QIcon(QPixmap(
                            os.path.join(info.PATH, "effects", "icons", "%s.png" % effect.data.get('class_name').lower())))
                        effect_action = menu.addAction(effect_icon, '  >  %s' % _(effect_name))
                        effect_action.setData({'item_id': effect.id, 'item_type': 'effect'})
                        effect_action.triggered.connect(self.Action_Triggered)

                elif item_type == "transition":
                    trans = Transition.get(id=item_id)
                    if not trans:
                        continue
                    item_name = _(trans.title())
                    item_icon = QIcon(QPixmap(trans.data.get('reader', {}).get('path')))
                    action = menu.addAction(item_icon, item_name)
                    action.setData({'item_id': item_id, 'item_type': 'transition'})
                    action.triggered.connect(self.Action_Triggered)

                elif item_type == "effect":
                    effect = Effect.get(id=item_id)
                    if not effect:
                        continue
                    item_name = _(effect.title())
                    item_icon = QIcon(QPixmap(
                        os.path.join(info.PATH, "effects", "icons", "%s.png" % effect.data.get('class_name').lower())))
                    action = menu.addAction(item_icon, item_name)
                    action.setData({'item_id': item_id, 'item_type': 'effect'})
                    action.triggered.connect(self.Action_Triggered)

        finally:
            if cursor_set:
                
                get_app().restoreOverrideCursor()

        
        if len(menu.actions()) == 0:
            return None

        
        return menu

    def _selections_equal(self, first, second):
        def norm(s):
            return sorted([(i['id'], i['type']) for i in s])
        return norm(first) == norm(second)

    def open_menu(self):
        """Create and display the selection menu when requested."""
        menu = self.getMenu()
        if menu:
            menu.exec_(self.btnSelectionName.mapToGlobal(QPoint(0, self.btnSelectionName.height())))

    def Action_Triggered(self):
        data = self.sender().data()
        win = get_app().window

        if 'selection' in data:
            
            self.all_selection = list(data['selection'])  
            self.target_selection = None
            
            for idx, sel in enumerate(self.all_selection):
                win.timeline.AddSelectionJS(sel['id'], sel['type'], idx == 0)
        else:
            
            item_id = data['item_id']
            item_type = data['item_type']
            self.target_selection = [{'id': item_id, 'type': item_type}]
            
            if not self.all_selection:
                self.all_selection = list(win.selected_items)
            win.timeline.AddSelectionJS(item_id, item_type, True)

    def select_item(self, selection):
        
        if self.target_selection is not None:
            
            if self._selections_equal(selection, self.target_selection):
                
                self.target_selection = None
                
            else:
                
                return
        else:
            
            if not self._selections_equal(selection, self.all_selection):
                self.all_selection = list(selection)

        count = len(selection)
        if count == 1:
            self.item_id = selection[0]['id']
            self.item_type = selection[0]['type']
        else:
            self.item_type = 'multi'

        
        _ = get_app()._tr

        
        if self.item_type == "multi":
            self.lblSelection.setText("<strong>%s</strong>" % _("Selection:"))
            self.btnSelectionName.setText(_("%d selections") % count)
            self.btnSelectionName.setVisible(True)
            self.btnSelectionName.setIcon(QIcon())
            self.btnSelectionName.setMenu(None)
            return
        def _set_item_icon(path):
            if path and isinstance(path, (str, bytes, os.PathLike)) and os.path.exists(path):
                self.item_icon = QIcon(QPixmap(path))
            else:
                self.item_icon = QIcon()

        if self.item_type == "clip":
            clip = Clip.get(id=self.item_id)
            if clip:
                self.item_name = clip.title()
                _set_item_icon(clip.data.get('image'))
        elif self.item_type == "transition":
            trans = Transition.get(id=self.item_id)
            if trans:
                self.item_name = _(trans.title())
                _set_item_icon(trans.data.get('reader', {}).get('path'))
        elif self.item_type == "effect":
            effect = Effect.get(id=self.item_id)
            if effect:
                self.item_name = _(effect.title())
                _set_item_icon(os.path.join(info.PATH, "effects", "icons", "%s.png" % effect.data.get('class_name').lower()))

        
        if self.item_name and len(self.item_name) > 25:
            self.item_name = "%s..." % self.item_name[:22]

        
        if self.item_id:
            self.lblSelection.setText("<strong>%s</strong>" % _("Selection:"))
            self.btnSelectionName.setText(self.item_name)
            self.btnSelectionName.setVisible(True)
            if self.item_icon:
                self.btnSelectionName.setIcon(self.item_icon)
        else:
            self.lblSelection.setText("<strong>%s</strong>" % _("No Selection"))
            self.btnSelectionName.setVisible(False)

        
        self.btnSelectionName.setMenu(None)

    def __init__(self, *args):
        
        super().__init__(*args)
        self.item_id = None
        self.item_type = None
        self.item_name = None
        self.item_icon = None
        self.all_selection = []

        
        _ = get_app()._tr

        
        self.lblSelection = QLabel()
        self.lblSelection.setText("<strong>%s</strong>" % _("No Selection"))
        self.btnSelectionName = QPushButton()
        self.setObjectName("selectionLabel")
        self.btnSelectionName.setObjectName("btnSelectionName")
        self.btnSelectionName.setVisible(False)
        self.btnSelectionName.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.btnSelectionName.clicked.connect(self.open_menu)

        
        self.lblSelection.setTextFormat(Qt.RichText)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(self.lblSelection)
        hbox.addWidget(self.btnSelectionName)
        self.setLayout(hbox)

        
        self.target_selection = None
        self.previous_selection = []

        
        get_app().window.propertyTableView.loadProperties.connect(self.select_item)
