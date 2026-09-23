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

    url = "https://github.com/sudhibabu43/SmartEdit/releases/latest"

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
