import re


RELEASE_DETAILS_URL = "https://github.com/sudhibabu43/SmartEdit/releases/tag/%s"
RELEASE_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def release_details_url(version):
    """Return the release details URL for official release versions only."""
    version = str(version or "").strip()
    if not RELEASE_VERSION_RE.match(version):
        return None
    return RELEASE_DETAILS_URL % version
