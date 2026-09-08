"""
@file
@brief Unit tests for the Shaky Footage Detection and Labeling feature.
@author SmartEdit Team
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from slm.video_analyzer import VideoAnalyzer, classify_shake
from slm.shaky_detector import ShakyFootageService
from slm.editing_controller import EditingController
from slm.command_schema import ActionType, SLMCommand


class TestVideoAnalyzerScores(unittest.TestCase):
    """Test 0-100% shake score calculation, classification, and thresholding."""

    def setUp(self):
        self.analyzer = VideoAnalyzer(default_shake_threshold=50.0)

    def test_classification_categories(self):
        # 0–30% = Stable
        self.assertEqual(classify_shake(0.0), "Stable")
        self.assertEqual(classify_shake(15.5), "Stable")
        self.assertEqual(classify_shake(30.0), "Stable")

        # 30–50% = Slightly Shaky
        self.assertEqual(classify_shake(30.1), "Slightly Shaky")
        self.assertEqual(classify_shake(42.0), "Slightly Shaky")
        self.assertEqual(classify_shake(50.0), "Slightly Shaky")

        # 50–70% = Shaky
        self.assertEqual(classify_shake(50.1), "Shaky")
        self.assertEqual(classify_shake(65.0), "Shaky")
        self.assertEqual(classify_shake(70.0), "Shaky")

        # 70–100% = Very Shaky
        self.assertEqual(classify_shake(70.1), "Very Shaky")
        self.assertEqual(classify_shake(88.5), "Very Shaky")
        self.assertEqual(classify_shake(100.0), "Very Shaky")

    def test_default_threshold_is_50_percent(self):
        self.assertEqual(self.analyzer.default_shake_threshold, 50.0)
        self.assertEqual(self.analyzer.get_effective_threshold(), 50.0)

    def test_custom_threshold_override(self):
        # Explicit argument
        self.assertEqual(self.analyzer.get_effective_threshold(65.0), 65.0)
        # Fractional argument (0.7 -> 70.0)
        self.assertEqual(self.analyzer.get_effective_threshold(0.7), 70.0)

    @patch("classes.app.get_app")
    def test_threshold_from_settings(self, mock_get_app):
        mock_app = MagicMock()
        mock_app.get_settings.return_value.get.side_effect = lambda k, default=None: 60 if k == "shaky-footage-threshold" else default
        mock_get_app.return_value = mock_app

        self.assertEqual(self.analyzer.get_effective_threshold(), 60.0)

    def test_heuristic_analysis_percentages(self):
        shaky_res = self.analyzer._heuristic_analysis("action_shaky_cam.mp4", threshold=50.0)
        self.assertTrue(shaky_res["is_shaky"])
        self.assertEqual(shaky_res["shake_percentage"], 75.0)
        self.assertEqual(shaky_res["classification"], "Very Shaky")

        stable_res = self.analyzer._heuristic_analysis("interview_tripod.mp4", threshold=50.0)
        self.assertFalse(stable_res["is_shaky"])
        self.assertEqual(stable_res["shake_percentage"], 15.0)
        self.assertEqual(stable_res["classification"], "Stable")


class TestTopUnusedLayerSelection(unittest.TestCase):
    """Test finding and creating the topmost unused timeline layer."""

    def setUp(self):
        self.service = ShakyFootageService()

    @patch("classes.query.Transition.filter", return_value=[])
    @patch("classes.query.Track.save")
    @patch("classes.query.Clip.filter")
    @patch("classes.app.get_app")
    def test_creates_new_layer_above_when_top_layer_occupied(self, mock_get_app, mock_clip_filter, mock_track_save, mock_trans_filter):
        # Project has Tracks 1, 2, 3 (1000000, 2000000, 3000000)
        # Clip is on Track 3 (3000000) -> top layer is occupied
        mock_app = MagicMock()
        mock_app.project.get.return_value = [
            {"number": 1000000},
            {"number": 2000000},
            {"number": 3000000}
        ]
        mock_get_app.return_value = mock_app

        c = MagicMock()
        c.data = {"layer": 3000000}
        mock_clip_filter.return_value = [c]

        chosen_layer = self.service.find_or_create_top_unused_layer()
        # Must create Track 4 (4000000) above Track 3
        self.assertEqual(chosen_layer, 4000000)
        mock_track_save.assert_called()

    @patch("classes.query.Transition.filter", return_value=[])
    @patch("classes.query.Track.get")
    @patch("classes.query.Clip.filter")
    @patch("classes.app.get_app")
    def test_uses_existing_topmost_unused_track_above_clips(self, mock_get_app, mock_clip_filter, mock_track_get, mock_trans_filter):
        # Project has Tracks 1, 2, 3, 4, 5
        # Clips only on Track 1 and 2
        # Topmost unused layer is Track 5 (5000000)
        mock_app = MagicMock()
        mock_app.project.get.return_value = [
            {"number": 1000000},
            {"number": 2000000},
            {"number": 3000000},
            {"number": 4000000},
            {"number": 5000000}
        ]
        mock_get_app.return_value = mock_app

        c1 = MagicMock()
        c1.data = {"layer": 1000000}
        c2 = MagicMock()
        c2.data = {"layer": 2000000}
        mock_clip_filter.return_value = [c1, c2]

        mock_track_obj = MagicMock()
        mock_track_obj.data = {"number": 5000000, "label": ""}
        mock_track_get.return_value = mock_track_obj

        chosen_layer = self.service.find_or_create_top_unused_layer()
        self.assertEqual(chosen_layer, 5000000)


class TestNonDestructiveLabeling(unittest.TestCase):
    """Test non-destructive behavior, exact time range alignment, and label formatting."""

    def setUp(self):
        self.service = ShakyFootageService()

    @patch("classes.query.Marker.save")
    @patch("classes.query.Clip.save")
    @patch("classes.app.get_app")
    def test_label_shaky_clips_preserves_originals(self, mock_get_app, mock_clip_save, mock_marker_save):
        mock_app = MagicMock()
        mock_app.project.generate_id.return_value = "marker_1"
        mock_get_app.return_value = mock_app

        # Original clip reference
        orig_clip = MagicMock()
        orig_clip.id = "orig_c1"
        orig_clip.data = {
            "title": "ActionScene.mp4",
            "position": 14.5,
            "duration": 8.0,
            "start": 0.0,
            "end": 8.0,
            "layer": 2000000
        }

        shaky_data = [{
            "clip_id": "orig_c1",
            "clip_name": "ActionScene.mp4",
            "position": 14.5,
            "duration": 8.0,
            "shake_percentage": 68.4,
            "classification": "Shaky",
            "clip_ref": orig_clip
        }]

        target_layer = 4000000
        created = self.service.label_shaky_clips(shaky_data, target_layer)

        # 1. Verify original clip is untouched (not deleted, not modified)
        orig_clip.delete.assert_not_called()
        self.assertEqual(orig_clip.data["position"], 14.5)
        self.assertEqual(orig_clip.data["duration"], 8.0)
        self.assertEqual(orig_clip.data["layer"], 2000000)

        # 2. Verify created label clip
        self.assertEqual(len(created), 1)
        lbl_clip = created[0]
        self.assertEqual(lbl_clip.data["position"], 14.5)
        self.assertEqual(lbl_clip.data["duration"], 8.0)
        self.assertEqual(lbl_clip.data["layer"], 4000000)
        self.assertEqual(lbl_clip.data["title"], "SHAKY FOOTAGE – 68%")
        self.assertTrue(lbl_clip.data["ui"]["ai_label"])
        self.assertEqual(lbl_clip.data["ui"]["target_clip_id"], "orig_c1")

        # 3. Verify timeline marker was created
        mock_marker_save.assert_called()

    @patch("classes.query.Marker.save")
    @patch("classes.query.Clip.save")
    @patch("classes.query.Track.save")
    @patch("classes.query.Transition.filter", return_value=[])
    @patch("classes.query.Clip.filter")
    @patch("classes.app.get_app")
    def test_full_pipeline_detect_and_label(self, mock_get_app, mock_clip_filter, mock_trans_filter, mock_track_save, mock_clip_save, mock_marker_save):
        mock_app = MagicMock()
        mock_app.project.get.return_value = [{"number": 1000000}, {"number": 2000000}]
        mock_app.project.generate_id.return_value = "id_gen"
        mock_app.updates.transaction_id = None
        mock_get_app.return_value = mock_app

        # Clip 1 is shaky, Clip 2 is stable
        c1 = MagicMock()
        c1.id = "c1"
        c1.title.return_value = "shaky_clip.mp4"
        c1.data = {"position": 0.0, "duration": 10.0, "start": 0.0, "end": 10.0, "layer": 1000000, "reader": {"path": "/fake/shaky_clip.mp4", "has_video": True}}

        c2 = MagicMock()
        c2.id = "c2"
        c2.title.return_value = "tripod_clip.mp4"
        c2.data = {"position": 10.0, "duration": 5.0, "start": 0.0, "end": 5.0, "layer": 2000000, "reader": {"path": "/fake/tripod_clip.mp4", "has_video": True}}

        mock_clip_filter.return_value = [c1, c2]

        result = self.service.detect_and_label_timeline(threshold=50.0)

        self.assertTrue(result["success"])
        self.assertEqual(result["detected_count"], 1)
        self.assertEqual(result["labeled_layer"], 3000000)
        self.assertIn("Detected 1 shaky clip(s)", result["message"])

    @patch("classes.query.Clip.filter")
    @patch("classes.app.get_app")
    def test_no_shaky_footage_detected(self, mock_get_app, mock_clip_filter):
        mock_app = MagicMock()
        mock_app.project.get.return_value = [{"number": 1000000}]
        mock_get_app.return_value = mock_app

        c = MagicMock()
        c.id = "c_stable"
        c.title.return_value = "tripod_steady.mp4"
        c.data = {"position": 0.0, "duration": 6.0, "layer": 1000000, "reader": {"path": "/fake/tripod_steady.mp4", "has_video": True}}
        mock_clip_filter.return_value = [c]

        result = self.service.detect_and_label_timeline(threshold=50.0)

        self.assertTrue(result["success"])
        self.assertEqual(result["detected_count"], 0)
        self.assertEqual(result["message"], "No shaky footage detected.")
        self.assertIsNone(result["labeled_layer"])


class TestUndoShakyLabels(unittest.TestCase):
    """Test atomic and explicit undo of AI labels."""

    def setUp(self):
        self.service = ShakyFootageService()

    @patch("classes.app.get_app")
    def test_undo_uses_smartedit_updates(self, mock_get_app):
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        self.service.last_transaction_id = "trans-123"
        res = self.service.undo_shaky_labels()

        self.assertTrue(res)
        mock_app.updates.undo.assert_called_once()
        self.assertIsNone(self.service.last_transaction_id)


class TestEditingControllerIntegration(unittest.TestCase):
    """Test integration with EditingController and SLM natural language commands."""

    def setUp(self):
        self.controller = EditingController()

    @patch("classes.query.Clip.filter")
    @patch("classes.app.get_app")
    def test_find_and_label_prompt_plan(self, mock_get_app, mock_clip_filter):
        mock_app = MagicMock()
        mock_app.project.get.return_value = [{"number": 1000000}]
        mock_get_app.return_value = mock_app

        c = MagicMock()
        c.id = "clip_shaky"
        c.title.return_value = "shaky_run.mp4"
        c.data = {"position": 0.0, "duration": 10.0, "layer": 1000000, "reader": {"path": "/fake/shaky_run.mp4", "has_video": True}}
        mock_clip_filter.return_value = [c]

        cmd = SLMCommand(actions=[ActionType.DETECT_SHAKY, ActionType.LABEL_SHAKY])
        plan = self.controller.generate_plan(cmd)

        self.assertFalse(plan.is_empty)
        # Should have detection item and labeling item on top layer
        self.assertEqual(len(plan.items), 2)
        self.assertIn("SHAKY FOOTAGE", plan.items[1].description)
        self.assertIn("topmost unused layer", plan.items[1].description)


if __name__ == "__main__":
    unittest.main()
