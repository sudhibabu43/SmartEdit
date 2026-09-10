"""
 @file
 @brief This file get the current version of smartedit from the smartedit.org website
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

import threading
from classes.app import get_app
from classes import http_client, info
from classes.logger import log


def get_current_Version():
    """Get the current version """
    t = threading.Thread(target=get_version_from_http, daemon=True)
    t.start()

def get_version_from_http():
    """Get the current version # from smartedit.org"""

    url = "https://www.smartedit.org/version/json/"

    try:
        version_info = http_client.get_json(
            http_client.urls_with_http_fallback(url),
            "SmartEdit version info",
            headers={"user-agent": "smartedit-qt-%s" % info.VERSION},
        )
        log.info("Found current version: %s" % version_info)

        
        smartedit_version = version_info.get("smartedit_version")
        info.ERROR_REPORT_STABLE_VERSION = version_info.get("smartedit_version")
        info.ERROR_REPORT_RATE_STABLE = version_info.get("error_rate_stable")
        info.ERROR_REPORT_RATE_UNSTABLE = version_info.get("error_rate_unstable")
        info.TRANS_REPORT_RATE_STABLE = version_info.get("trans_rate_stable")
        info.TRANS_REPORT_RATE_UNSTABLE = version_info.get("trans_rate_unstable")

        
        get_app().window.FoundVersionSignal.emit(smartedit_version)

    except Exception:
        log.warning("Failed to get SmartEdit version info", exc_info=True)
