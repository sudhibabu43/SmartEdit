"""
 @file
 @brief This file sends anonymous application metrics and errors over HTTP
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


import encodings.idna
import base64
import platform
import threading
import time

from classes import info
from classes import http_client
from classes import language
from classes.app import get_app
from classes.logger import log

import smartedit

from qt_api import QTimer, QT_VERSION_STR, PYQT_VERSION_STR
from functools import partial

try:
    import distro
except ModuleNotFoundError:
    distro = None


s = get_app().get_settings()


os_version = "X11; Linux %s" % platform.machine()
os_distro = "None"
try:
    if platform.system() == "Darwin":
        v = platform.mac_ver()
        os_version = "Macintosh; Intel Mac OS X %s" % v[0].replace(".", "_")
        os_distro = "OS X %s" % v[0]

    elif platform.system() == "Windows":
        v = platform.win32_ver()
        os_version = "Windows NT %s; %s" % (v[0], v[1])
        os_distro = "Windows %s" % "-".join(v)

    elif platform.system() == "Linux":
        
        if distro:
            os_distro = "-".join(distro.linux_distribution()[0:2])
        else:
            os_distro = "Linux"

except Exception:
    log.debug("Error determining OS version", exc_info=1)


user_agent = "Mozilla/5.0 (%s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36" % os_version

GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"
GA4_MID = "G-YGF4YGWPE2"
GA4_MPS = "aG9qVmV0MllURXVPMlVoQm11RWRDQQ=="
GA4_SESSION_ID = int(time.time())
METRIC_QUEUE_MAX = 100
METRIC_CONNECT_TIMEOUT = http_client.DEFAULT_CONNECT_TIMEOUT
METRIC_READ_TIMEOUT = 3



metric_queue = []
metric_queue_lock = threading.Lock()
metric_worker_active = False


def _d(value):
    """Decode a stored string value."""
    return base64.b64decode(value.encode("ascii")).decode("ascii")


def _base_event_params():
    """Shared GA4 params for all events (used as custom dimensions)."""
    return {
        "engagement_time_msec": 1,
        "session_id": GA4_SESSION_ID,
        "os_app_name": info.PRODUCT_NAME,
        "os_app_version": info.VERSION,
        "os_libsmartedit_version": smartedit.SMARTEDIT_VERSION_FULL,
        "os_python_version": platform.python_version(),
        "os_qt_version": QT_VERSION_STR,
        "os_pyqt_version": PYQT_VERSION_STR,
        "os_locale": language.get_current_locale().replace('_', '-').lower(),
        "os_platform": os_version,
        "os_distro": os_distro,
    }


def _build_event(name, extra_params=None):
    """Build a GA4 event payload."""
    event_params = _base_event_params()
    if extra_params:
        event_params.update(extra_params)
    return {
        "name": name,
        "params": event_params,
    }


def track_metric_screen(screen_name):
    """Track a GUI screen being shown"""
    event = _build_event("screen_view", {"screen_name": screen_name})
    QTimer.singleShot(0, partial(send_metric, event))


def track_metric_event(event_action, event_label, event_category="General", event_value=0):
    """Track a UI event."""
    event = _build_event(
        "ui_event",
        {
            "event_category": event_category,
            "event_action": event_action,
            "event_label": event_label,
            "value": event_value,
        },
    )
    QTimer.singleShot(0, partial(send_metric, event))


def track_metric_error(error_name, is_fatal=False):
    """Track an error has occurred"""
    event = _build_event(
        "exception",
        {
            "description": error_name,
            "fatal": 1 if is_fatal else 0,
        },
    )
    QTimer.singleShot(0, partial(send_metric, event))


def track_metric_session(is_start=True):
    """Track application session start/end."""
    event_name = "session_start" if is_start else "session_end"
    event = _build_event(event_name, {"screen_name": "launch-app" if is_start else "close-app"})
    QTimer.singleShot(0, partial(send_metric, event))


def send_metric(event):
    """Send anonymous GA4 Measurement Protocol events over HTTP."""
    global metric_worker_active

    
    with metric_queue_lock:
        metric_queue.append(event)
        if len(metric_queue) > METRIC_QUEUE_MAX:
            metric_queue.pop(0)

    
    if not s.get("send_metrics"):
        return
    if not GA4_MID or not GA4_MPS:
        log.warning("GA4 metrics disabled: missing GA4 configuration")
        return

    with metric_queue_lock:
        if metric_worker_active:
            return
        metric_worker_active = True

    worker = threading.Thread(target=_send_metric_worker, name="SmartEditMetrics", daemon=True)
    worker.start()


def _send_metric_worker():
    """Flush queued metrics without blocking the Qt event loop."""
    global metric_worker_active

    while True:
        with metric_queue_lock:
            if not metric_queue:
                metric_worker_active = False
                return

            events_to_send = list(metric_queue)
            metric_queue.clear()

        url = "%s?measurement_id=%s&api_secret=%s" % (
            GA4_ENDPOINT,
            GA4_MID,
            _d(GA4_MPS),
        )
        payload = {
            "client_id": s.get("unique_install_id"),
            "events": events_to_send,
        }

        try:
            http_client.post_json(
                url,
                payload,
                "metrics",
                headers={"user-agent": user_agent},
                timeout=(METRIC_CONNECT_TIMEOUT, METRIC_READ_TIMEOUT),
            )
        except Exception:
            log.warning("Failed to track metric", exc_info=1)
            _requeue_metrics(events_to_send)
            return

        
        time.sleep(0.25)


def _requeue_metrics(events):
    """Put failed metrics back in the bounded queue for a later attempt."""
    global metric_worker_active

    with metric_queue_lock:
        metric_queue[:0] = events
        if len(metric_queue) > METRIC_QUEUE_MAX:
            del metric_queue[:-METRIC_QUEUE_MAX]
        metric_worker_active = False
