"""
 @file
 @brief This file contains the project file model, used by the project tree
 @author Noah Figg <eggmunkee@hotmail.com>
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
import json
import re
import glob
import functools
import uuid

from qt_api import (
    QMimeData, Qt, QUrl, pyqtSignal, QEventLoop, QObject,
    QSortFilterProxyModel, QItemSelectionModel, QItemSelection, QPersistentModelIndex, QModelIndex
)
from qt_api import (
    QIcon, QPixmap, QStandardItem, QStandardItemModel
)
from qt_api import QAbstractItemView
from classes import updates
from classes import info
from classes.image_types import get_media_type
from classes.query import File
from classes.logger import log
from classes.app import get_app
from classes.thumbnail import GetThumbPath
from classes.qt_types import model_index_sibling_at_column

import smartedit


IMPORT_READER_MAX_SIZE = 128


def inspect_media(path, max_width=0, max_height=0):
    """Inspect media using the shared libsmartedit reader-selection logic."""
    def _inspect_with_reader(inspect_reader):
        reader = smartedit.Clip.CreateReader(path, inspect_reader)
        if not reader:
            raise RuntimeError(f"No reader available for path: {path}")

        if max_width > 0 and max_height > 0 and hasattr(reader, "SetMaxDecodeSize"):
            reader.SetMaxDecodeSize(int(max_width), int(max_height))

        reader.Open()
        try:
            return json.loads(reader.Json()), float(reader.info.duration or 0.0)
        finally:
            reader.Close()

    try:
        return _inspect_with_reader(False)
    except Exception:
        
        
        
        return _inspect_with_reader(True)


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


class FileFilterProxyModel(QSortFilterProxyModel):
    """Proxy class used for sorting and filtering model data"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def data(self, index, role=Qt.DisplayRole):
        """Hide text in column 0 for TreeView - name is shown in column 1"""
        if index.column() == 0 and role in (Qt.DisplayRole, Qt.AccessibleTextRole):
            return ""
        return super().data(index, role)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """Filter for text"""
        from qt_api import isdeleted, get_proxy_filter_regex, regex_is_empty, regex_matches
        files_filter = get_app().window.filesFilter
        filter_text = "" if isdeleted(files_filter) else files_filter.text()
        if get_app().window.actionFilesShowVideo.isChecked() \
                or get_app().window.actionFilesShowAudio.isChecked() \
                or get_app().window.actionFilesShowImage.isChecked() \
                or filter_text:
            
            index = self.sourceModel().index(sourceRow, 0, sourceParent)
            file_name = self.sourceModel().data(index)  

            
            index = self.sourceModel().index(sourceRow, 3, sourceParent)
            media_type = self.sourceModel().data(index)  

            index = self.sourceModel().index(sourceRow, 2, sourceParent)
            tags = self.sourceModel().data(index)  

            if any([
                get_app().window.actionFilesShowVideo.isChecked() and media_type != "video",
                get_app().window.actionFilesShowAudio.isChecked() and media_type != "audio",
                get_app().window.actionFilesShowImage.isChecked() and media_type != "image",
            ]):
                return False

            
            regex = get_proxy_filter_regex(self)
            if not regex_is_empty(regex):
                tag_text = tags or ""
                return regex_matches(regex, file_name) or regex_matches(regex, tag_text)
            return True

        
        return super().filterAcceptsRow(sourceRow, sourceParent)

    def mimeData(self, indexes):
        
        data = QMimeData()

        
        ids = []
        seen_rows = set()
        for idx in indexes:
            row = idx.row()
            if row in seen_rows:
                continue
            seen_rows.add(row)
            id_index = idx.sibling(row, 5)
            file_id = id_index.data()
            if file_id:
                ids.append(file_id)
        if not ids:
            ids = self.model_owner.selected_file_ids()
        data.setText(json.dumps(ids))
        data.setHtml("clip")
        urls = []
        for file_id in ids:
            try:
                file = File.get(id=file_id)
            except Exception:
                file = None
            if not file:
                continue
            try:
                path = file.absolute_path()
            except Exception:
                path = file.data.get("path")
            if path:
                urls.append(QUrl.fromLocalFile(path))
        if urls:
            data.setUrls(urls)

        
        return data

    def get_file_index(self, file_id):
        
        if file_id in self.model_owner.model_ids:
            return self.mapFromSource(QModelIndex(self.model_owner.model_ids[file_id]))
        return QModelIndex()

    def __init__(self, **kwargs):
        if "parent" in kwargs:
            self.model_owner = kwargs["parent"]
            kwargs.pop("parent")

        
        super().__init__(**kwargs)


class FilesModel(QObject, updates.UpdateInterface):
    ModelRefreshed = pyqtSignal()
    PLACEHOLDER_PREFIX = "__genjob__:"
    PROJECT_FILE_THUMB_ATTEMPTS = 3

    @staticmethod
    def _icon_from_thumbnail_source(thumb_source):
        """Create an icon from freshly loaded thumbnail bytes when possible."""
        thumb_source = str(thumb_source or "")
        if thumb_source:
            pixmap = QPixmap()
            if pixmap.load(thumb_source) and not pixmap.isNull():
                return QIcon(pixmap)
        return QIcon(thumb_source)

    def _thumbnail_source_for_file(self, file, clear_cache=False):
        """Return the thumbnail/artwork source path and display name for a file."""
        path, filename = os.path.split(file.data["path"])
        name = file.data.get("name", filename)
        media_type = file.data.get("media_type")

        if media_type in ["video", "image"]:
            thumbnail_frame = 1
            if 'start' in file.data:
                fps = file.data["fps"]
                fps_float = float(fps["num"]) / float(fps["den"])
                thumbnail_frame = round(float(file.data['start']) * fps_float) + 1
            thumb_source = GetThumbPath(
                file.id,
                thumbnail_frame,
                clear_cache=clear_cache,
                attempts=self.PROJECT_FILE_THUMB_ATTEMPTS,
            )
        else:
            thumb_source = os.path.join(info.PATH, "images", "AudioThumbnail.svg")

        return thumb_source, name, media_type

    def _project_file_icon_for_file(self, file):
        thumb_source, name, media_type = self._thumbnail_source_for_file(file)
        return self._icon_from_thumbnail_source(thumb_source), name, media_type

    def _tooltip_for_file(self, file, name):
        tooltip = str(name or "")
        app = get_app()
        window = getattr(app, "window", None) if app else None
        proxy_service = getattr(window, "proxy_service", None) if window else None
        if not proxy_service or not file:
            return tooltip

        state = proxy_service.get_proxy_state(file)
        if state == "ready":
            return "{} {}".format(tooltip, app._tr("(Optimized)"))
        if state == "missing":
            return "{} {}".format(tooltip, app._tr("(Optimized)"))
        return tooltip

    
    def changed(self, action):

        
        if action and ((len(action.key) >= 1 and action.key[0].lower() == "files") or action.type == "load"):
            
            if action.type == "insert":
                
                self.update_model(clear=False)
            elif action.type == "delete" and action.key[0].lower() == "files" and len(action.key) == 2:
                
                self.update_model(clear=False, delete_file_id=action.key[1].get('id', ''))
            elif action.type in ("update", "delete") and action.key[0].lower() == "files":
                
                self.update_model(clear=False, update_file_id=action.key[1].get('id', ''))
            else:
                
                self.update_model(clear=True, progressive_ui=False)

    def update_model(self, clear=True, delete_file_id=None, update_file_id=None, progressive_ui=True):
        log.debug("updating files model.")
        app = get_app()

        self.ignore_updates = True

        
        _ = app._tr

        
        if delete_file_id in self.model_ids:
            
            id_index = self.model_ids[delete_file_id]

            
            if not id_index.isValid() or delete_file_id != id_index.data():
                log.warning("Couldn't remove {} from model!".format(delete_file_id))
                return
            
            row_num = id_index.row()
            self.model.removeRows(row_num, 1, id_index.parent())
            self.model.submit()
            self.model_ids.pop(delete_file_id)

        
        if update_file_id in self.model_ids:
            
            id_index = self.model_ids[update_file_id]

            
            if not id_index.isValid() or update_file_id != id_index.data():
                log.warning("Couldn't update {} in model!".format(update_file_id))
                return

            
            f = File.get(id=update_file_id)
            if f:
                
                row_num = id_index.row()
                if f.data.get("tags") != self.model.item(row_num, 2).text():
                    self.model.item(row_num, 2).setText(f.data.get("tags"))
                path, filename = os.path.split(f.data["path"])
                name = f.data.get("name", filename)
                self.model.item(row_num, 0).setToolTip(self._tooltip_for_file(f, name))

        
        if clear:
            self.model_ids = {}
            self.model.clear()

        
        self.model.setHorizontalHeaderLabels([
            _("Thumb"), _("Name"), _("Tags"),
            "media_type", "path", "id"
        ])

        
        files = File.filter()  

        
        row_added_count = 0
        for file in files:
            id = file.data["id"]
            if id in self.model_ids and self.model_ids[id].isValid():
                
                continue

            path, filename = os.path.split(file.data["path"])
            tags = file.data.get("tags", "")
            thumb_icon, name, media_type = self._project_file_icon_for_file(file)

            row = []
            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt. ItemNeverHasChildren

            
            col = QStandardItem(thumb_icon, name)
            col.setToolTip(self._tooltip_for_file(file, name))
            col.setFlags(flags)
            col.setAccessibleText(name)
            row.append(col)

            
            col = QStandardItem(name)
            col.setFlags(flags | Qt.ItemIsEditable)
            col.setAccessibleText(name)
            row.append(col)

            
            col = QStandardItem(tags)
            col.setFlags(flags | Qt.ItemIsEditable)
            row.append(col)

            
            col = QStandardItem(media_type)
            col.setFlags(flags)
            row.append(col)

            
            col = QStandardItem(path)
            col.setFlags(flags)
            row.append(col)

            
            col = QStandardItem(id)
            col.setFlags(flags | Qt.ItemIsUserCheckable)
            row.append(col)

            
            if id not in self.model_ids:
                self.model.appendRow(row)
                
                self.model_ids[id] = QPersistentModelIndex(row[5].index())

                row_added_count += 1
                if progressive_ui and row_added_count % 25 == 0:
                    
                    get_app().processEvents(QEventLoop.ExcludeUserInputEvents)

            
            if progressive_ui:
                get_app().window.resize_contents()

        self.ignore_updates = False

        
        if not progressive_ui:
            get_app().window.resize_contents()

        
        self.ModelRefreshed.emit()
        self._rebuild_generation_placeholders()

    def add_files(self, files, image_seq_details=None, quiet=False,
                  prevent_image_seq=False, prevent_recent_folder=False):
        
        app = get_app()
        settings = app.get_settings()
        _ = app._tr

        
        if not isinstance(files, (list, tuple)):
            files = [files]
        scroll_to_files = []

        start_count = len(files)
        for count, filepath in enumerate(files):
            (dir_path, filename) = os.path.split(filepath)

            
            new_file = File.get(path=filepath)

            
            if new_file:
                
                scroll_to_files.append(new_file)
                del new_file
                continue

            try:
                
                file_data, _media_duration = inspect_media(
                    filepath,
                    max_width=IMPORT_READER_MAX_SIZE,
                    max_height=IMPORT_READER_MAX_SIZE,
                )

                
                file_data["media_type"] = get_media_type(file_data)

                
                if file_data.get("has_audio") and not file_data.get("has_video"):
                    
                    project = get_app().project
                    file_data["width"] = project.get("width")
                    file_data["height"] = project.get("height")

                
                new_file = File()
                new_file.data = file_data

                
                seq_info = None
                if not prevent_image_seq:
                    seq_info = image_seq_details or self.get_image_sequence_details(filepath)

                if seq_info:
                    
                    new_path = seq_info.get("path")

                    
                    new_file.data, media_duration = inspect_media(
                        new_path,
                        max_width=IMPORT_READER_MAX_SIZE,
                        max_height=IMPORT_READER_MAX_SIZE,
                    )
                    if media_duration > 0.0:
                        
                        new_file.data["media_type"] = "video"
                        duration = new_file.data["duration"]

                        if seq_info and "fps" in seq_info and "length_multiplier" in seq_info:
                            
                            fps_num = seq_info.get("fps", {}).get("num", 25)
                            fps_den = seq_info.get("fps", {}).get("den", 1)
                            log.debug("Image Sequence using specified FPS: %s / %s" % (fps_num, fps_den))
                        else:
                            
                            fps_num = get_app().project.get("fps").get("num", 30)
                            fps_den = get_app().project.get("fps").get("den", 1)
                            log.debug("Image Sequence using project FPS: %s / %s" % (fps_num, fps_den))

                        
                        duration *= 25.0 / (float(fps_num) / float(fps_den))
                        new_file.data["duration"] = duration
                        new_file.data["fps"] = {"num": fps_num, "den": fps_den}
                        new_file.data["video_timebase"] = {"num": fps_den, "den": fps_num}

                        log.info(f"Imported '{new_path}' as image sequence with '{fps_num}/{fps_den}' FPS "
                                 f"and '{duration}' duration")

                        
                        match_glob = "{}{}.{}".format(seq_info.get("base_name"), '[0-9]*', seq_info.get("extension"))
                        log.debug("Removing files from import list with glob: {}".format(match_glob))
                        for seq_file in glob.iglob(os.path.join(seq_info.get("folder_path"), match_glob)):
                            
                            if seq_file in files and seq_file != filepath:
                                files.remove(seq_file)
                    else:
                        
                        log.info(f"Failed to parse image sequence pattern {new_path}, ignoring...")
                        continue

                if not seq_info:
                    
                    log.info("Imported media file {}".format(filepath))

                
                new_file.save()
                scroll_to_files.append(new_file)

                if start_count > 15:
                    message = _("Importing %(count)d / %(total)d") % {
                            "count": count,
                            "total": len(files) - 1
                            }
                    app.window.statusBar.showMessage(message, 15000)

                
                get_app().processEvents()
                
                if not prevent_recent_folder:
                    settings.setDefaultPath(settings.actionType.IMPORT, dir_path)

            except Exception as ex:
                
                log.warning("Failed to import {}: {}".format(filepath, ex))

                if not quiet and start_count == 1:
                    
                    app.window.invalidImage(filename)

        
        self.ignore_image_sequence_paths = []

        
        self.selection_model.clearSelection()
        last_selected_index = QModelIndex()
        for file_object in scroll_to_files:
            
            index = self.proxy_model.get_file_index(file_object.id)
            if index.isValid():
                
                self.selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                get_app().window.filesView.scrollTo(
                    model_index_sibling_at_column(index, 0),
                    QAbstractItemView.PositionAtCenter,
                )
                last_selected_index = index
        if last_selected_index.isValid():
            
            
            self.selection_model.setCurrentIndex(last_selected_index, QItemSelectionModel.NoUpdate)

        message = _("Imported %(count)d files") % {"count": len(files) - 1}
        app.window.statusBar.showMessage(message, 3000)

    def get_image_sequence_details(self, file_path):
        """Inspect a file path and determine if this is an image sequence"""

        
        (dirName, fileName) = os.path.split(file_path)

        
        if dirName in self.ignore_image_sequence_paths:
            return None

        extensions = ["png", "jpg", "jpeg", "tif", "svg"]
        match = re.findall(r"(.*[^\d])?(0*)(\d+)\.(%s)" % "|".join(extensions), fileName, re.I)

        if not match:
            
            return None

        
        base_name = match[0][0]
        fixlen = match[0][1] > ""
        number = int(match[0][2])
        digits = len(match[0][1] + match[0][2])
        extension = match[0][3]

        full_base_name = os.path.join(dirName, base_name)

        
        fixlen = fixlen or not (
            glob.glob("%s%s.%s" % (full_base_name, "[0-9]" * (digits + 1), extension))
            or glob.glob("%s%s.%s" % (full_base_name, "[0-9]" * ((digits - 1) if digits > 1 else 3), extension))
        )

        
        for x in range(max(0, number - 100), min(number + 101, 50000)):
            if x != number and os.path.exists(
               "%s%s.%s" % (full_base_name, str(x).rjust(digits, "0") if fixlen else str(x), extension)):
                break  
        else:
            
            return None

        
        
        
        log.debug("Ignoring path for image sequence imports: {}".format(dirName))
        self.ignore_image_sequence_paths.append(dirName)

        log.info('Prompt user to import sequence starting from {}'.format(fileName))
        if not get_app().window.promptImageSequence(fileName):
            
            return None

        
        if not fixlen:
            zero_pattern = "%d"
        else:
            zero_pattern = "%%0%sd" % digits
        pattern = "%s%s.%s" % (base_name, zero_pattern, extension)
        new_file_path = os.path.join(dirName, pattern)

        
        parameters = {
            "folder_path": dirName,
            "base_name": base_name,
            "fixlen": fixlen,
            "digits": digits,
            "extension": extension,
            "pattern": pattern,
            "path": new_file_path
        }
        return parameters

    def process_urls(self, qurl_list, import_quietly=False, prevent_image_seq=False,
                     transaction_id=None):
        """Recursively process QUrls from a QDropEvent"""
        media_paths = []

        
        
        
        owns_transaction = transaction_id is None
        if owns_transaction:
            transaction_id = str(uuid.uuid4())
        get_app().updates.transaction_id = transaction_id

        for uri in qurl_list:
            filepath = uri.toLocalFile()
            if not os.path.exists(filepath):
                continue
            if filepath.endswith(".osp") and os.path.isfile(filepath):
                
                get_app().window.OpenProjectSignal.emit(filepath)
                return True
            if os.path.isdir(filepath):
                import_quietly = True
                log.info("Recursively importing {}".format(filepath))
                try:
                    for r, dirs, f in os.walk(filepath):
                        dirs.sort()
                        media_paths.extend(
                            [os.path.join(r, p) for p in sorted(f)])
                except OSError:
                    log.warning("Directory recursion failed", exc_info=1)
            elif os.path.isfile(filepath):
                media_paths.append(filepath)
        if not media_paths:
            if owns_transaction:
                get_app().updates.transaction_id = None
            return
        
        
        
        log.debug("Importing file list: {}".format(media_paths))
        self.add_files(media_paths, quiet=import_quietly, prevent_image_seq=prevent_image_seq)
        if owns_transaction:
            get_app().updates.transaction_id = None

    def update_file_thumbnail(self, file_id):
        """Update/re-generate the thumbnail of a specific file"""
        file = File.get(id=file_id)
        path, filename = os.path.split(file.data["path"])
        name = file.data.get("name", filename)

        
        self.ignore_updates = True
        m = self.model

        if file_id in self.model_ids:
            
            id_index = self.model_ids[file_id]
            if not id_index.isValid():
                return

            thumb_source, _, _ = self._thumbnail_source_for_file(file, clear_cache=True)
            thumb_icon = self._icon_from_thumbnail_source(thumb_source)

            
            thumb_index = id_index.sibling(id_index.row(), 0)
            item = m.itemFromIndex(thumb_index)
            item.setIcon(thumb_icon)
            item.setText(name)
            item.setToolTip(self._tooltip_for_file(file, name))
            item.setAccessibleText(name)

            
            text_index = id_index.sibling(id_index.row(), 1)
            item = m.itemFromIndex(text_index)
            item.setText(name)

            
            self.ModelRefreshed.emit()

        self.ignore_updates = False

    def selected_file_ids(self):
        """ Get a list of file IDs for all selected files """
        
        selected = self.selection_model.selectedRows(5)
        ids = []
        for idx in selected:
            file_id = idx.data()
            if not file_id or self._is_generation_placeholder(file_id):
                continue
            ids.append(file_id)
        return ids

    def selected_files(self):
        """ Get a list of File objects representing the current selection """
        files = []
        for id in self.selected_file_ids():
            files.append(File.get(id=id))
        return files

    def current_file_id(self):
        """ Get the file ID of the current files-view item, or the first selection """
        
        
        selected_rows = self.selection_model.selectedRows(5)
        if selected_rows:
            selected_ids = set()
            for row_index in selected_rows:
                file_id = row_index.data()
                if file_id and not self._is_generation_placeholder(file_id):
                    selected_ids.add(file_id)

            current = self.selection_model.currentIndex()
            if current and current.isValid():
                current_id = current.sibling(current.row(), 5).data()
                if current_id and current_id in selected_ids:
                    return current_id
            for row_index in selected_rows:
                file_id = row_index.data()
                if file_id and not self._is_generation_placeholder(file_id):
                    return file_id

        cur = self.selection_model.currentIndex()
        if cur and cur.isValid():
            file_id = cur.sibling(cur.row(), 5).data()
            if file_id and not self._is_generation_placeholder(file_id):
                return file_id

    def current_file(self):
        """ Get the File object for the current files-view item, or the first selection """
        cur_id = self.current_file_id()
        if cur_id:
            return File.get(id=cur_id)
        else:
            return None

    def value_updated(self, item):
        """ Table cell change event - when tags are updated on a file"""
        if item.column() == 2:
            
            tags_value = item.data(0)
            f = self.current_file()
            if f:
                
                f.data["tags"] = tags_value
                f.save()

    def _sync_tree_to_list_selection(self, selected, deselected):
        """Sync selection from TreeView (proxy_model) to ListView (list_proxy_model)"""
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            
            list_selection = QItemSelection()
            first_list_index = QModelIndex()
            for index in self.selection_model.selectedRows(0):
                list_index = self.list_proxy_model.mapFromSource(index)
                if list_index.isValid():
                    list_selection.select(list_index, list_index)
                    if not first_list_index.isValid():
                        first_list_index = list_index
            self.list_selection_model.select(
                list_selection,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            if first_list_index.isValid():
                self.list_selection_model.setCurrentIndex(first_list_index, QItemSelectionModel.NoUpdate)
        finally:
            self._syncing_selection = False

    def _sync_list_to_tree_selection(self, selected, deselected):
        """Sync selection from ListView (list_proxy_model) to TreeView (proxy_model)"""
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            
            tree_selection = QItemSelection()
            first_tree_index = QModelIndex()
            for index in self.list_selection_model.selectedRows(0):
                tree_index = self.list_proxy_model.mapToSource(index)
                if tree_index.isValid():
                    tree_selection.select(tree_index, tree_index)
                    if not first_tree_index.isValid():
                        first_tree_index = tree_index
            self.selection_model.select(
                tree_selection,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            if first_tree_index.isValid():
                self.selection_model.setCurrentIndex(first_tree_index, QItemSelectionModel.NoUpdate)
        finally:
            self._syncing_selection = False

    def __init__(self, *args, generation_queue=None, proxy_service=None):
        self.generation_queue = generation_queue
        self.proxy_service = proxy_service

        
        
        app = get_app()
        app.updates.add_listener(self)

        
        self.model = QStandardItemModel()
        self.model.setColumnCount(6)
        self.model_ids = {}
        self.ignore_updates = False
        self.ignore_image_sequence_paths = []

        
        self.proxy_model = FileFilterProxyModel(parent=self)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseSensitive)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortLocaleAware(True)

        
        self.list_proxy_model = SingleColumnProxyModel()
        self.list_proxy_model.setSourceModel(self.proxy_model)

        
        self.model.itemChanged.connect(self.value_updated)

        
        self.selection_model = QItemSelectionModel(self.proxy_model)
        self.list_selection_model = QItemSelectionModel(self.list_proxy_model)

        
        self._syncing_selection = False
        self.selection_model.selectionChanged.connect(self._sync_tree_to_list_selection)
        self.list_selection_model.selectionChanged.connect(self._sync_list_to_tree_selection)

        
        app.window.FileUpdated.connect(self.update_file_thumbnail)
        app.window.refreshFilesSignal.connect(
            functools.partial(self.update_model, clear=False))
        if self.generation_queue:
            self.generation_queue.file_job_changed.connect(self._refresh_file_generation_display)
            self.generation_queue.queue_changed.connect(self._refresh_all_generation_displays)
            self.generation_queue.job_added.connect(self._on_generation_job_added)
            self.generation_queue.job_updated.connect(self._on_generation_job_updated)
            self.generation_queue.job_finished.connect(self._on_generation_job_finished)
            self.generation_queue.job_removed.connect(self._on_generation_job_removed)
        if self.proxy_service:
            self.proxy_service.file_job_changed.connect(self._refresh_file_generation_display)
            self.proxy_service.queue_changed.connect(self._refresh_all_generation_displays)

        
        super().__init__(*args)

        
        
        if info.MODEL_TEST:
            try:
                
                from qt_api import QAbstractItemModelTester
                self.model_tests = []
                for m in [self.proxy_model, self.model]:
                    self.model_tests.append(
                        QAbstractItemModelTester(
                            m, QAbstractItemModelTester.FailureReportingMode.Warning)
                    )
                log.info("Enabled {} model tests for emoji data".format(len(self.model_tests)))
            except ImportError:
                pass

    def _is_generation_placeholder(self, file_id):
        return str(file_id or "").startswith(self.PLACEHOLDER_PREFIX)

    def _placeholder_id_for_job(self, job_id):
        return "{}{}".format(self.PLACEHOLDER_PREFIX, str(job_id or ""))

    def _job_id_from_placeholder(self, file_id):
        file_id = str(file_id or "")
        if not self._is_generation_placeholder(file_id):
            return None
        return file_id[len(self.PLACEHOLDER_PREFIX):]

    def _placeholder_row_for_job(self, job_id):
        placeholder_id = self._placeholder_id_for_job(job_id)
        if placeholder_id not in self.model_ids:
            return None
        id_index = self.model_ids[placeholder_id]
        if not id_index.isValid():
            return None
        return id_index.row()

    def _generation_icon_for_job(self, job):
        icon_name = "tool-generate-sparkle.svg"
        try:
            app = get_app()
            window = getattr(app, "window", None)
            generation_service = getattr(window, "generation_service", None)
            if generation_service and isinstance(job, dict):
                template_id = str(job.get("template_id") or "").strip()
                template = generation_service.template_registry.get_template(template_id)
                if template:
                    resolved_icon = generation_service.icon_for_template(template)
                    if resolved_icon:
                        icon_name = resolved_icon
        except Exception:
            pass

        icon_path = os.path.join(info.PATH, "themes", "cosmic", "images", icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)

        emoji_icon_path = os.path.join(info.PATH, "emojis", "color", "svg", "2728.svg")
        if os.path.exists(emoji_icon_path):
            return QIcon(emoji_icon_path)
        return QIcon(":/icons/Humanity/actions/16/media-record.svg")

    def _add_generation_placeholder(self, job_id):
        job = self.generation_queue.get_job(job_id) if self.generation_queue else None
        if not job:
            return
        if job.get("source_file_id"):
            return

        placeholder_id = self._placeholder_id_for_job(job_id)
        if placeholder_id in self.model_ids and self.model_ids[placeholder_id].isValid():
            self._update_generation_placeholder(job_id)
            return

        name = str(job.get("name") or "generation")
        status = str(job.get("status") or "queued")
        progress = int(job.get("progress", 0))
        progress_detail = str(job.get("progress_detail") or "").strip()
        label = name
        if status == "running":
            label = "{} ({}%)".format(name, progress)
            if progress_detail:
                label = "{} [{}]".format(label, progress_detail)
        elif status == "queued":
            label = "{} (Queued)".format(name)
        elif status == "canceling":
            label = "{} (Canceling...)".format(name)

        row = []
        icon = self._generation_icon_for_job(job)
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemNeverHasChildren

        col = QStandardItem(icon, label)
        col.setFlags(flags)
        row.append(col)

        col = QStandardItem(label)
        col.setFlags(flags)
        row.append(col)

        col = QStandardItem("generation")
        col.setFlags(flags)
        row.append(col)

        col = QStandardItem("generation_job")
        col.setFlags(flags)
        row.append(col)

        col = QStandardItem("")
        col.setFlags(flags)
        row.append(col)

        col = QStandardItem(placeholder_id)
        col.setFlags(flags)
        row.append(col)

        self.model.appendRow(row)
        self.model_ids[placeholder_id] = QPersistentModelIndex(row[5].index())
        self.ModelRefreshed.emit()

    def _update_generation_placeholder(self, job_id):
        row = self._placeholder_row_for_job(job_id)
        if row is None:
            self._add_generation_placeholder(job_id)
            return
        job = self.generation_queue.get_job(job_id) if self.generation_queue else None
        if not job:
            return

        name = str(job.get("name") or "generation")
        status = str(job.get("status") or "queued")
        progress = int(job.get("progress", 0))
        progress_detail = str(job.get("progress_detail") or "").strip()
        label = name
        if status == "running":
            label = "{} ({}%)".format(name, progress)
            if progress_detail:
                label = "{} [{}]".format(label, progress_detail)
        elif status == "queued":
            label = "{} (Queued)".format(name)
        elif status == "canceling":
            label = "{} (Canceling...)".format(name)

        self.model.item(row, 0).setIcon(self._generation_icon_for_job(job))
        self.model.item(row, 0).setText(label)
        self.model.item(row, 1).setText(label)
        left = self.model.index(row, 0)
        right = self.model.index(row, 1)
        self.model.dataChanged.emit(left, right, [Qt.DisplayRole, Qt.AccessibleTextRole])
        self.ModelRefreshed.emit()

    def _remove_generation_placeholder(self, job_id):
        placeholder_id = self._placeholder_id_for_job(job_id)
        if placeholder_id not in self.model_ids:
            return
        id_index = self.model_ids.get(placeholder_id)
        if not id_index or not id_index.isValid():
            self.model_ids.pop(placeholder_id, None)
            return
        row = id_index.row()
        self.model.removeRows(row, 1, id_index.parent())
        self.model.submit()
        self.model_ids.pop(placeholder_id, None)
        self.ModelRefreshed.emit()

    def _rebuild_generation_placeholders(self):
        if not self.generation_queue:
            return
        for job in list(self.generation_queue.jobs.values()):
            if job.get("source_file_id"):
                continue
            if job.get("status") in ("completed", "failed", "canceled"):
                self._remove_generation_placeholder(job.get("id"))
            else:
                self._add_generation_placeholder(job.get("id"))

    def _on_generation_job_added(self, job_id, source_file_id):
        if source_file_id:
            return
        self._add_generation_placeholder(job_id)

    def _on_generation_job_updated(self, job_id, status, progress):
        job = self.generation_queue.get_job(job_id) if self.generation_queue else None
        if not job or job.get("source_file_id"):
            return
        if status in ("completed", "failed", "canceled"):
            self._remove_generation_placeholder(job_id)
        else:
            self._update_generation_placeholder(job_id)

    def _on_generation_job_finished(self, job_id, status):
        job = self.generation_queue.get_job(job_id) if self.generation_queue else None
        if not job or job.get("source_file_id"):
            return
        self._remove_generation_placeholder(job_id)

    def _on_generation_job_removed(self, job_id):
        self._remove_generation_placeholder(job_id)

    def _refresh_file_generation_display(self, file_id):
        file_id = str(file_id or "")
        if not file_id:
            return
        if file_id not in self.model_ids:
            return
        id_index = self.model_ids[file_id]
        if not id_index.isValid():
            return
        row = id_index.row()
        file_obj = File.get(id=file_id)
        if file_obj:
            _, filename = os.path.split(file_obj.data["path"])
            name = file_obj.data.get("name", filename)
            self.model.item(row, 0).setToolTip(self._tooltip_for_file(file_obj, name))
        left = self.model.index(row, 0)
        right = self.model.index(row, 0)
        self.model.dataChanged.emit(left, right, [Qt.DisplayRole, Qt.AccessibleTextRole])
        self.ModelRefreshed.emit()

    def _refresh_all_generation_displays(self):
        if self.model.rowCount() < 1:
            return
        left = self.model.index(0, 0)
        right = self.model.index(self.model.rowCount() - 1, 0)
        self.model.dataChanged.emit(left, right, [Qt.DisplayRole, Qt.AccessibleTextRole])
        self.ModelRefreshed.emit()
