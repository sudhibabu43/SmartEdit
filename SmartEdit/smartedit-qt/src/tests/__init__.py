"""Test package bootstrap for headless Qt environments."""

import os

from qt_api import QCoreApplication, Qt




os.environ.setdefault("QT_QPA_PLATFORM", "minimal")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
