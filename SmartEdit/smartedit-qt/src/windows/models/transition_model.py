"""
 @file
 @brief This file contains the transitions model, used by the main window
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

from qt_api import (
    QObject, QMimeData, Qt, pyqtSignal, QLocale,
    QSortFilterProxyModel, QPersistentModelIndex, QItemSelectionModel, QItemSelection, QModelIndex,
)
from qt_api import QIcon, QStandardItemModel, QStandardItem
from qt_api import QMessageBox
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

    def mimeData(self, indexes):
        """Forward drag data through TransitionFilterProxyModel for consistent path payloads."""
        source_proxy = self.sourceModel()
        if not source_proxy:
            return super().mimeData(indexes)
        proxy_indexes = []
        for index in indexes:
            mapped = self.mapToSource(index)
            if mapped.isValid():
                proxy_indexes.append(mapped)
        return source_proxy.mimeData(proxy_indexes)


class TransitionFilterProxyModel(QSortFilterProxyModel):
    """Proxy class used for sorting and filtering model data"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def data(self, index, role=Qt.DisplayRole):
        """Hide text in column 0 for TreeView - name is shown in column 1"""
        if index.column() == 0 and role in (Qt.DisplayRole, Qt.AccessibleTextRole):
            return ""
        return super().data(index, role)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Filter for common transitions and text filter"""

        if get_app().window.actionTransitionsShowCommon.isChecked():
            
            index = self.sourceModel().index(sourceRow, 2, sourceParent)  
            group_name = self.sourceModel().data(index)  

            
            index = self.sourceModel().index(sourceRow, 0, sourceParent)  
            trans_name = self.sourceModel().data(index)  

            
            return group_name == "common" and self.filterRegExp().indexIn(trans_name) >= 0

        
        return super(TransitionFilterProxyModel, self).filterAcceptsRow(sourceRow, sourceParent)

    def lessThan(self, left, right):
        """Sort with both group name and transition name"""
        leftData = left.data(self.sortRole())  
        rightData = right.data(self.sortRole())
        leftGroup = left.sibling(left.row(), 2).data()  
        rightGroup = right.sibling(right.row(), 2).data()

        return leftGroup <= rightGroup and leftData < rightData

    def mimeData(self, indexes):
        
        data = QMimeData()

        
        items = []
        for proxy_index in indexes:
            if not proxy_index.isValid():
                continue
            if proxy_index.model() is self:
                source_index = self.mapToSource(proxy_index)
            else:
                source_index = proxy_index
            if not source_index.isValid():
                continue
            path_index = source_index.sibling(source_index.row(), 3)
            path_value = path_index.data(Qt.DisplayRole)
            if not path_value:
                path_value = path_index.data()
            if not path_value:
                continue
            path_value = os.path.normpath(str(path_value))
            items.append(path_value)
            log.debug(
                "Transition drag payload path: %r (exists=%s)",
                path_value,
                os.path.exists(path_value),
            )
        data.setText(json.dumps(items))
        data.setHtml("transition")
        log.debug("Transition drag payload items: %d", len(items))

        
        return data


class TransitionsModel(QObject):
    ModelRefreshed = pyqtSignal()

    def update_model(self, clear=True):
        log.info("updating transitions model.")
        app = get_app()

        
        _ = app._tr

        
        if clear:
            self.model_paths = {}
            self.model.clear()

        
        self.model.setHorizontalHeaderLabels([_("Thumb"), _("Name")])

        
        transitions_dir = os.path.join(info.PATH, "transitions")
        common_dir = os.path.join(transitions_dir, "common")
        extra_dir = os.path.join(transitions_dir, "extra")
        transition_groups = [
            {"type": "common",
             "dir": common_dir,
             "files": os.listdir(common_dir)},
            {"type": "extra",
             "dir": extra_dir,
             "files": os.listdir(extra_dir)},
        ]

        
        if (os.path.exists(info.TRANSITIONS_PATH) and os.listdir(info.TRANSITIONS_PATH)):
            transition_groups.append(
                {"type": "user",
                 "dir": info.TRANSITIONS_PATH,
                 "files": os.listdir(info.TRANSITIONS_PATH)}
            )

        for group in transition_groups:
            type = group["type"]
            dir = group["dir"]
            files = group["files"]

            for filename in sorted(files):
                path = os.path.join(dir, filename)
                fileBaseName = os.path.splitext(filename)[0]

                
                if filename[0] == "." or "thumbs.db" in filename.lower():
                    continue

                
                suffix_number = None
                name_parts = fileBaseName.split("_")
                if name_parts[-1].isdigit():
                    suffix_number = name_parts[-1]

                
                trans_name = fileBaseName.replace("_", " ").capitalize()

                
                if suffix_number:
                    trans_name = trans_name.replace(suffix_number, "%s")
                    trans_name = self.app._tr(trans_name) % QLocale().toString(int(suffix_number))
                else:
                    trans_name = self.app._tr(trans_name)

                
                thumb_path = os.path.join(info.IMAGES_PATH, "cache", "{}.png".format(fileBaseName))

                
                if not os.path.exists(thumb_path):
                    
                    thumb_path = os.path.join(info.CACHE_PATH, "{}.png".format(fileBaseName))

                
                if not os.path.exists(thumb_path):

                    try:
                        
                        clip = smartedit.Clip(path)
                        reader = clip.Reader()

                        
                        reader.Open()

                        
                        reader.GetFrame(0).Thumbnail(thumb_path, 98, 64, os.path.join(info.IMAGES_PATH, "mask.png"),
                                                     "", "#000", True, "png", 85)
                        reader.Close()
                        clip.Close()

                    except Exception:
                        
                        log.debug('Invalid transition image file %s', filename, exc_info=1)
                        msg = QMessageBox()
                        msg.setText(_("{} is not a valid transition file.".format(filename)))
                        msg.exec_()
                        continue

                row = []

                
                icon = QIcon()
                icon.addFile(thumb_path)

                
                col = QStandardItem()
                col.setIcon(icon)
                col.setText(trans_name)
                col.setToolTip(trans_name)
                col.setData(type)
                col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                col.setAccessibleText(trans_name)
                row.append(col)

                
                col = QStandardItem("Name")
                col.setData(trans_name, Qt.DisplayRole)
                col.setText(trans_name)
                col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                col.setAccessibleText(trans_name)
                row.append(col)

                
                col = QStandardItem("Type")
                col.setData(type, Qt.DisplayRole)
                col.setText(type)
                col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                row.append(col)

                
                col = QStandardItem("Path")
                col.setData(path, Qt.DisplayRole)
                col.setText(path)
                col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                row.append(col)

                
                if path not in self.model_paths:
                    self.model.appendRow(row)
                    self.model_paths[path] = QPersistentModelIndex(row[3].index())

        
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
        self.model.setColumnCount(4)
        self.model_paths = {}

        
        self.proxy_model = TransitionFilterProxyModel()
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseSensitive)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortLocaleAware(True)

        
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
                log.info("Enabled {} model tests for transition data".format(len(self.model_tests)))
            except ImportError:
                pass
