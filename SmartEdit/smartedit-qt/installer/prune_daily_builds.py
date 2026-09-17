"""
 @file
 @brief Remove older daily builds from GitHub (so our daily repo doesn't become huge)
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2016 SmartEdit Studios, LLC
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

import sys
from github3 import login
import datetime
import pytz
import time


# Should we actually delete old assets?
SHOULD_DELETE = True
DELETE_DELAY = 0.5
MAXIMUM_ASSET_AGE_DAYS = 180

# Calculate current date (with timezone)
now = pytz.UTC.localize(datetime.datetime.now())


def get_release(repo, tag_name):
    """Fetch the GitHub release tagged with the given tag and return it
    @param repo:        github3 repository object
    @returns:           github3 release object or None
    """
    if hasattr(repo, 'releases'):
        release_iter = repo.releases()
    else:
        release_iter = repo.iter_releases()
    for release in release_iter:
        if release.tag_name == tag_name:
            return release


if len(sys.argv) >= 3:
    github_user = sys.argv[1]
    github_pass = sys.argv[2]

    # Login and get "GitHub" object
    gh = login(github_user, github_pass)
    repo = gh.repository("SmartEdit", "smartedit-qt")

    # Get daily git_release object
    github_release = get_release(repo, "daily")

    # Loop through all assets (for daily release)
    delete_count = 0
    skip_count = 0
    for asset in github_release.assets:
        asset_age = now - asset.updated_at
        if asset_age.days > MAXIMUM_ASSET_AGE_DAYS:
            delete_count += 1

            if SHOULD_DELETE:
                # Wait for a small delay so we don't get blocked from GitHub API
                time.sleep(DELETE_DELAY)

                # Delete the old asset
                print(" - Delete %s (%s days old)" % (asset.name, asset_age.days))
                asset._delete(asset._api)
        else:
            skip_count += 1

    print("------------------")
    print("Deleted %s Assets" % delete_count)
    print("Skipped %s Assets" % skip_count)
