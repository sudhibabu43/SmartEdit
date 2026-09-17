"""
 @file
 @brief This file contains the effects model, used by the main window
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

import os

from qt_api import (
    QObject, QMimeData, Qt, QSize, pyqtSignal,
    QSortFilterProxyModel, QPersistentModelIndex, QItemSelectionModel, QItemSelection, QModelIndex,
)
from qt_api import QIcon, QPixmap, QStandardItemModel, QStandardItem
import smartedit  

from classes import info
from classes.logger import log
from classes.app import get_app

import json


class SingleColumnProxyModel(QSortFilterProxyModel):
    """Proxy that exposes only the first column for ListView accessibility"""

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        """Get text data from the underlying source model (bypassing filter proxy)"""
        if index.column() == 0 and role in (Qt.DisplayRole, Qt.AccessibleTextRole):
            source_index = self.mapToSource(index)
            filter_proxy = self.sourceModel()
            if filter_proxy:
                root_index = filter_proxy.mapToSource(source_index)
                root_model = filter_proxy.sourceModel()
                if root_model:
                    return root_model.data(root_index, Qt.DisplayRole)
        return super().data(index, role)


class EffectsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def data(self, index, role=Qt.DisplayRole):
        """Hide text in column 0 for TreeView - name is shown in column 1"""
        if index.column() == 0 and role in (Qt.DisplayRole, Qt.AccessibleTextRole):
            return ""
        return super().data(index, role)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Filter for common transitions and text filter"""

        if not get_app().window.actionEffectsShowAll.isChecked():
            
            effect_name = self.sourceModel().data(self.sourceModel().index(sourceRow, 1, sourceParent))
            effect_desc = self.sourceModel().data(self.sourceModel().index(sourceRow, 2, sourceParent))
            effect_type = self.sourceModel().data(self.sourceModel().index(sourceRow, 3, sourceParent))

            
            if get_app().window.actionEffectsShowVideo.isChecked():
                return effect_type == "Video" and \
                    (self.filterRegExp().indexIn(effect_name) >= 0 or
                     self.filterRegExp().indexIn(effect_desc) >= 0)
            else:
                return effect_type == "Audio" and \
                    (self.filterRegExp().indexIn(effect_name) >= 0 or
                     self.filterRegExp().indexIn(effect_desc) >= 0)

        
        return super(EffectsProxyModel, self).filterAcceptsRow(sourceRow, sourceParent)

    def mimeData(self, indexes):
        
        data = QMimeData()

        
        items = []
        for proxy_index in indexes:
            source_index = self.mapToSource(proxy_index)
            items.append(source_index.sibling(source_index.row(), 4).data())
        data.setText(json.dumps(items))
        data.setHtml("effect")

        
        return data


class EffectsModel(QObject):
    ModelRefreshed = pyqtSignal()

    def update_model(self, clear=True):
        log.info("updating effects model.")
        app = get_app()

        
        win = app.window
        _ = app._tr

        
        if clear:
            self.model_names = {}
            self.model.clear()

        
        self.model.setHorizontalHeaderLabels([_("Thumb"), _("Name"), _("Description")])

        
        effects_dir = os.path.join(info.PATH, "effects")
        icons_dir = os.path.join(effects_dir, "icons")

        
        raw_effects_list = json.loads(smartedit.EffectInfo.Json())

        
        for effect_info in raw_effects_list:
            
            effect_name = effect_info["class_name"]
            title = effect_info["name"]
            description = effect_info["description"]
            
            icon_name = "%s.png" % effect_name.lower().replace(' ', '')
            icon_path = os.path.join(icons_dir, icon_name)

            
            category = None
            if effect_info["has_video"] and effect_info["has_audio"]:
                category = "Audio & Video"
            elif not effect_info["has_video"] and effect_info["has_audio"]:
                category = "Audio"
            elif effect_info["has_video"] and not effect_info["has_audio"]:
                category = "Video"

            
            thumb_path = os.path.join(info.IMAGES_PATH, "cache", icon_name)

            
            if not os.path.exists(thumb_path):
                
                thumb_path = os.path.join(info.CACHE_PATH, icon_name)

            
            if not os.path.exists(thumb_path):

                try:
                    
                    log.info('Generating thumbnail for %s (%s)' % (thumb_path, icon_path))
                    clip = smartedit.Clip(icon_path)
                    reader = clip.Reader()

                    
                    reader.Open()

                    
                    reader.GetFrame(0).Thumbnail(
                        thumb_path, 98, 64,
                        os.path.join(info.IMAGES_PATH, "mask.png"),
                        "", "#000", True, "png", 85
                    )
                    reader.Close()

                except Exception:
                    
                    log.warning("{} is not a valid image file.".format(icon_path))

            row = []

            
            col = QStandardItem()

            
            icon = QIcon()
            icon.addFile(thumb_path)

            col.setIcon(icon)
            col.setText(self.app._tr(title))
            col.setToolTip(self.app._tr(title))
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            col.setAccessibleText(self.app._tr(title))
            row.append(col)

            
            col = QStandardItem("Name")
            col.setData(self.app._tr(title), Qt.DisplayRole)
            col.setText(self.app._tr(title))
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            col.setAccessibleText(self.app._tr(title))
            row.append(col)

            
            col = QStandardItem("Description")
            col.setData(self.app._tr(description), Qt.DisplayRole)
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            row.append(col)

            
            col = QStandardItem("Category")
            col.setData(category, Qt.DisplayRole)
            col.setText(category)
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            row.append(col)

            
            col = QStandardItem("Effect")
            col.setData(effect_name, Qt.DisplayRole)
            col.setText(effect_name)
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            row.append(col)

            
            if effect_name not in self.model_names:
                self.model.appendRow(row)
                self.model_names[effect_name] = QPersistentModelIndex(row[1].index())

        
        self.ModelRefreshed.emit()

    def _sync_tree_to_list_selection(self, selected, deselected):
        """Sync selection from TreeView (proxy_model) to ListView (list_proxy_model)"""
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            list_selection = QItemSelection()
            for index in self.selection_model.selectedRows(0):
                list_index = self.list_proxy_model.mapFromSource(index)
                if list_index.isValid():
                    list_selection.select(list_index, list_index)
            self.list_selection_model.select(
                list_selection,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
        finally:
            self._syncing_selection = False

    def _sync_list_to_tree_selection(self, selected, deselected):
        """Sync selection from ListView (list_proxy_model) to TreeView (proxy_model)"""
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            tree_selection = QItemSelection()
            for index in self.list_selection_model.selectedRows(0):
                tree_index = self.list_proxy_model.mapToSource(index)
                if tree_index.isValid():
                    tree_selection.select(tree_index, tree_index)
            self.selection_model.select(
                tree_selection,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
        finally:
            self._syncing_selection = False

    def __init__(self, *args):
        
        super().__init__(*args)

        
        self.app = get_app()
        self.model = QStandardItemModel()
        self.model.setColumnCount(5)
        self.model_names = {}

        
        self.proxy_model = EffectsProxyModel()
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseSensitive)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortLocaleAware(True)
        self.proxy_model.setFilterKeyColumn(-1)

        
        self.list_proxy_model = SingleColumnProxyModel()
        self.list_proxy_model.setSourceModel(self.proxy_model)

        
        self.selection_model = QItemSelectionModel(self.proxy_model)
        self.list_selection_model = QItemSelectionModel(self.list_proxy_model)

        
        self._syncing_selection = False
        self.selection_model.selectionChanged.connect(self._sync_tree_to_list_selection)
        self.list_selection_model.selectionChanged.connect(self._sync_list_to_tree_selection)

        
        
        if info.MODEL_TEST:
            try:
                
                from qt_api import QAbstractItemModelTester
                self.model_tests = []
                for m in [self.proxy_model, self.model]:
                    self.model_tests.append(
                        QAbstractItemModelTester(
                            m, QAbstractItemModelTester.FailureReportingMode.Warning)
                    )
                log.info("Enabled {} model tests for effects data".format(len(self.model_tests)))
            except ImportError:
                pass
