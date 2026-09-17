"""
 @file
 @brief Unit tests for SmartEdit release details helpers
 @author SmartEdit Studios, LLC

 @section 

 Copyright (c) 2008-2026 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.
 """

import os
import sys
import unittest


PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if PATH not in sys.path:
    sys.path.append(PATH)

from classes import release_details


class ReleaseDetailsTests(unittest.TestCase):
    def test_release_details_url_accepts_official_versions(self):
        self.assertEqual(
            release_details.release_details_url("3.5.1"),
            "https://www.smartedit.org/releases/3.5.1/",
        )

    def test_release_details_url_skips_development_versions(self):
        self.assertIsNone(release_details.release_details_url("3.5.1-dev"))

    def test_release_details_url_skips_release_candidates(self):
        self.assertIsNone(release_details.release_details_url("3.5.1-rc1"))


if __name__ == "__main__":
    unittest.main()
