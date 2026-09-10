"""
 @file
 @brief This file creates the QApplication, and displays the main window
 @author Noah Figg <eggmunkee@hotmail.com>
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author olivier Girard <eolinwen@gmail.com>

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

import atexit
import sys
import os
import platform
import traceback
import json

from qt_api import QT_API, QT_VERSION_STR, BINDING_VERSION_STR, Qt, Slot
from qt_api import QApplication, QMessageBox, QTimer
from qt_api import request_android_storage_permission_if_needed


def get_app():
    """ Get the current QApplication instance of SmartEdit """
    return QApplication.instance()


def get_settings():
    """Get a reference to the app's settings object"""
    return get_app().get_settings()


class StartupError:
    """ Store and later display an error encountered during setup"""
    levels = {
        "warning": QMessageBox.warning,
        "error": QMessageBox.critical,
    }

    def __init__(self, title="", message="", level="warning"):
        """Create an error message object, populated with details"""
        self.title = title
        self.message = message
        self.level = level

    def show(self):
        """Display the stored error message"""
        box_call = self.levels[self.level]
        box_call(None, self.title, self.message)
        if self.level == "error":
            sys.exit()


class SmartEditApp(QApplication):
    """The primary QApplication subclass for SmartEdit."""

    def __init__(self, *args, **kwargs):
        self.mode = kwargs.pop("mode", None)
        super().__init__(*args, **kwargs)
        self.args = super().arguments()
        self.errors = []

        try:
            
            from classes import info
            from classes.logger import log, reroute_output

            
            if self.mode != "unittest":
                import time
                log.info("-" * 48)
                log.info(time.asctime().center(48))
                log.info('Starting new session'.center(48))

            log.debug("Command line: %s", self.args)

            from classes import settings, project_data, updates, sentry
            import smartedit

            
            if self.mode != "unittest":
                reroute_output()

        except ImportError as ex:
            tb = traceback.format_exc()
            log.error('SmartEditApp::Import Error', exc_info=1)
            self.errors.append(StartupError(
                "Import Error",
                "Module: %(name)s\n\n%(tb)s" % {"name": ex.name, "tb": tb},
                level="error"))
            
            raise
        except Exception:
            log.error('SmartEditApp::Init Error', exc_info=1)
            sys.exit()

        self.info = info

        
        self.log = log
        
        try:
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
        except Exception as exc:
            log.debug("Failed to clear stale override cursor: %s", exc, exc_info=True)
        self.show_environment(info, smartedit)
        if self.mode != "unittest":
            self.check_libsmartedit_version(info, smartedit)

        
        self.settings = settings.SettingStore(parent=self)
        self.settings.load()
        self.project = project_data.ProjectDataStore()
        self.updates = updates.UpdateManager()
        
        self.updates.add_listener(self.project)
        self.updates.reset()

        
        smartedit.Settings.Instance().PATH_SMARTEDIT_INSTALL = info.PATH

        
        babl_ext_path = os.path.join(info.PATH, "lib", "babl-ext")
        log.info(f"checking babl_ext_path: {babl_ext_path}")
        if os.path.exists(babl_ext_path):
            os.environ["BABL_PATH"] = babl_ext_path
            log.info(f"setting BABL_PATH: {babl_ext_path}")

        
        if self.mode == "unittest" or not self.settings.get('send_metrics'):
            sentry.disable_tracing()

        
        self.window = None

        
        from themes.manager import ThemeManager
        self.theme_manager = ThemeManager(self)

    def show_environment(self, info, smartedit):
        log = self.log
        try:
            log.info("-" * 48)
            log.info(("SmartEdit (version %s)" % info.SETUP['version']).center(48))
            log.info("-" * 48)

            log.info("smartedit-qt version: %s" % info.VERSION)
            log.info("libsmartedit version: %s" % smartedit.SMARTEDIT_VERSION_FULL)
            log.info("platform: %s" % platform.platform())
            log.info("processor: %s" % platform.processor())
            log.info("machine: %s" % platform.machine())
            log.info("python version: %s" % platform.python_version())
            log.info("qt binding: %s (Qt %s, binding %s)" % (QT_API, QT_VERSION_STR, BINDING_VERSION_STR))

            
            version_path = os.path.join(info.PATH, "settings", "version.json")
            if os.path.exists(version_path):
                with open(version_path, "r", encoding="UTF-8") as f:
                    version_info = json.loads(f.read())
                    log.info("Frozen version info from build server:\n%s" %
                             json.dumps(version_info, indent=4, sort_keys=True))

        except Exception:
            log.debug("Error displaying dependency/system details", exc_info=1)

    def check_libsmartedit_version(self, info, smartedit):
        """Detect minimum libsmartedit version"""
        _ = self._tr
        ver = smartedit.SMARTEDIT_VERSION_FULL
        min_ver = info.MINIMUM_LIBSMARTEDIT_VERSION
        if ver >= min_ver:
            return True

        self.errors.append(StartupError(
            _("Wrong Version of libsmartedit Detected"),
            _("<b>Version %(minimum_version)s is required</b>, "
              "but %(current_version)s was detected. "
              "Please update libsmartedit or download our latest installer.") % {
                "minimum_version": min_ver,
                "current_version": ver,
                },
            level="error",
        ))

    @staticmethod
    def _show_main_window(window):
        """Map the final window geometry, then restore its serialized dock state."""
        state = window.windowState()
        window.show()
        window.raise_()
        window.activateWindow()
        if state & Qt.WindowFullScreen:
            QTimer.singleShot(
                0, lambda: (window.showNormal(), window.showFullScreen()))
        elif state & Qt.WindowMaximized:
            QTimer.singleShot(
                0, lambda: (window.showNormal(), window.showMaximized()))
        restore_state = getattr(window, "_restore_saved_window_state", None)
        if callable(restore_state):
            QTimer.singleShot(100, restore_state)

    def gui(self):
        """
        Initialize GUI and main window.
        :return: bool: True if the GUI has no errors, False if we fail to initialize the GUI
        """
        from classes import language, sentry, logger_libsmartedit

        _ = self._tr
        info = self.info
        log = self.log

        
        language.init_language()
        sentry.set_tag("locale", info.CURRENT_LANGUAGE)

        
        try:
            log.debug("Testing write access to user directory")
            
            TEST_PATH_DIR = os.path.join(info.USER_PATH, 'PERMISSION')
            TEST_PATH_FILE = os.path.join(TEST_PATH_DIR, 'test.osp')
            os.makedirs(TEST_PATH_DIR, exist_ok=True)
            with open(TEST_PATH_FILE, 'w') as f:
                f.write('{}')
                f.flush()
            
            os.unlink(TEST_PATH_FILE)
            os.rmdir(TEST_PATH_DIR)
        except PermissionError as ex:
            log.error('Failed to create file %s', TEST_PATH_FILE, exc_info=1)
            self.errors.append(StartupError(
                _("Permission Error"),
                _("%(error)s. Please delete <b>%(path)s</b> and launch SmartEdit again.") % {
                    "error": str(ex),
                    "path": info.USER_PATH,
                    },
                level="error",
            ))

        
        self.show_errors()

        
        self.logger_libsmartedit = logger_libsmartedit.LoggerLibSmartEdit()
        self.logger_libsmartedit.start()

        
        self.context_menu_object = None

        
        from windows.main_window import MainWindow
        log.debug("Creating main interface window")
        self.window = MainWindow()

        
        if self.mode == "quit":
            self.window.close()
            return False

        
        self.window.updateStatusChanged(False, False)

        
        self.aboutToQuit.connect(self.cleanup)

        
        self._show_main_window(self.window)

        
        
        QTimer.singleShot(500, request_android_storage_permission_if_needed)

        args = self.args
        if len(args) < 2:
            
            self.window.RecoverBackup.emit()
            return True

        log.info('Process command-line arguments: %s', args[1:])

        
        if args[1].endswith(".osp"):
            self.window.OpenProjectSignal.emit(args[1])
            return True

        
        self.project.load("")
        for arg in args[1:]:
            self.window.filesView.add_file(arg)
        return True

    def settings_load_error(self, filepath=None):
        """Use QMessageBox to warn the user of a settings load issue"""
        _ = self._tr
        self.errors.append(StartupError(
            _("Settings Error"),
            _("Error loading settings file: %(file_path)s. Settings will be reset.") % {
                "file_path": filepath
                },
            level="warning",
        ))

    def get_settings(self):
        if not hasattr(self, "settings"):
            return None
        return self.settings

    def show_errors(self):
        count = len(self.errors)
        if count > 0:
            self.log.warning("Displaying %d startup messages", count)
        while self.errors:
            error = self.errors.pop(0)
            error.show()

    def _tr(self, message):
        return self.translate("", message)

    @Slot()
    def cleanup(self):
        """aboutToQuit signal handler for application exit"""
        self.log.debug("Saving settings in app.cleanup")
        if getattr(self, "window", None):
            try:
                self.window._shutdown()
            except Exception:
                self.log.warning("Window shutdown raised during app cleanup.", exc_info=1)
        try:
            self.settings.save()
        except Exception:
            self.log.error("Couldn't save user settings on exit.", exc_info=1)


@atexit.register
def onLogTheEnd():
    """ Log when the primary Qt event loop ends """
    try:
        from classes.logger import log
        import time
        log.info("SmartEdit's session ended".center(48))
        log.info(time.asctime().center(48))
        log.info("=" * 48)
    except Exception:
        import logging
        log = logging.getLogger(".")
        log.debug('Failed to write session ended log', exc_info=1)
