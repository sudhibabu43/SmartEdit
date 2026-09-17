"""
 @file
 @brief Helpers for SmartEdit release details metadata
 @author SmartEdit Studios, LLC

 @section 

 Copyright (c) 2008-2026 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public  as published by
 the Free Software Foundation, either version 3 of the , or
 (at your option) any later version.
 """

import re


RELEASE_DETAILS_URL = "https://www.smartedit.org/releases/%s/"
RELEASE_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def release_details_url(version):
    """Return the release details URL for official release versions only."""
    version = str(version or "").strip()
    if not RELEASE_VERSION_RE.match(version):
        return None
    return RELEASE_DETAILS_URL % version
