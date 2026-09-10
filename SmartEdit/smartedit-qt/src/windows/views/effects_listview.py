"""
 @file
 @brief This file contains the effects file listview, used by the main window
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

from qt_api import QSize, QPoint, Qt
from qt_api import clear_override_cursor
from qt_api import QDrag
from qt_api import QListView, QAbstractItemView

from classes import info
from classes.app import get_app
from classes.logger import log
from .menu import StyledContextMenu, add_bound_action


class EffectsListView(QListView):
    """ A TreeView QWidget used on the main window """
    drag_item_size = QSize(48, 48)
    drag_item_center = QPoint(24, 24)

    def contextMenuEvent(self, event):
        
        app = get_app()
        self.win = app.window
        app.context_menu_object = "effects"

        menu = StyledContextMenu(parent=self)
        add_bound_action(menu, self.win, "actionDetailsView", app._tr("Details View"), "actionDetailsView_trigger")
        menu.show_at(event)

    def startDrag(self, event):
        """ Override startDrag method to display custom icon """

        
        selected = self.selectionModel().selectedRows(0)

        
        current = self.selectionModel().currentIndex()
        if not current.isValid() and selected:
            current = selected[0]

        if not current.isValid():
            
            log.warning("No draggable items found in model!")
            return False

        
        icon = current.sibling(current.row(), 0).data(Qt.DecorationRole)

        
        drag = QDrag(self)
        drag.setMimeData(self.model().mimeData(selected))
        drag.setPixmap(icon.pixmap(self.drag_item_size))
        drag.setHotSpot(self.drag_item_center)
        exec_fn = getattr(drag, "exec", None) or getattr(drag, "exec_", None)
        if exec_fn is None:
            raise AttributeError("QDrag has no exec_/exec method")
        exec_fn()
        clear_override_cursor()

    def filter_changed(self):
        self.refresh_view()

    def refresh_view(self):
        """Filter transitions with proxy class"""
        filter_text = self.win.effectsFilter.text()
        from qt_api import make_filter_regex, set_proxy_filter
        pattern = filter_text.replace(' ', '.*')
        regex = make_filter_regex(pattern, case_insensitive=True)
        set_proxy_filter(self.effects_model.proxy_model, regex)
        self.effects_model.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.effects_model.proxy_model.sort(0, Qt.AscendingOrder)

    def __init__(self, model):
        
        QListView.__init__(self)

        
        app = get_app()
        self.win = app.window

        
        self.effects_model = model

        
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

        self.setModel(self.effects_model.list_proxy_model)

        
        self.selectionModel().deleteLater()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        if hasattr(self, "setSelectionRectVisible"):
            self.setSelectionRectVisible(False)
        self.setSelectionModel(self.effects_model.list_selection_model)

        
        self.setIconSize(info.LIST_ICON_SIZE)
        self.setGridSize(info.LIST_GRID_SIZE)
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)

        
        app.window.effectsFilter.textChanged.connect(self.filter_changed)
        app.window.refreshEffectsSignal.connect(self.refresh_view)
