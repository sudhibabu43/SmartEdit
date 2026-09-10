"""
@file
@brief Unit tests for the SLM Assistant pipeline (prompt parser, schema, video analyzer, editing controller).
@author SmartEdit Team
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from slm.command_schema import ActionType, SLMCommand, CommandSchemaValidator
from slm.prompt_parser import PromptParser
from slm.video_analyzer import VideoAnalyzer
from slm.editing_controller import EditingController, AIPlan, PlanItem


class TestPromptParser(unittest.TestCase):
    """Test natural-language interpretation for all target prompts."""

    def setUp(self):
        self.parser = PromptParser(prefer_local_slm=False)

    def test_arrange_clips(self):
        cmd = self.parser.parse("Arrange the clips in the best order")
        self.assertIn(ActionType.ARRANGE_CLIPS, cmd.actions)

    def test_remove_silence(self):
        cmd = self.parser.parse("Remove silence")
        self.assertIn(ActionType.REMOVE_SILENCE, cmd.actions)

    def test_find_shaky(self):
        cmd = self.parser.parse("Find shaky footage")
        self.assertIn(ActionType.DETECT_SHAKY, cmd.actions)
        self.assertNotIn(ActionType.LABEL_SHAKY, cmd.actions)

    def test_find_shaky_and_label(self):
        cmd = self.parser.parse("Find shaky footage and label it")
        self.assertIn(ActionType.DETECT_SHAKY, cmd.actions)
        self.assertIn(ActionType.LABEL_SHAKY, cmd.actions)

    def test_silence_and_arrange(self):
        cmd = self.parser.parse("Remove silence and arrange the clips")
        self.assertIn(ActionType.REMOVE_SILENCE, cmd.actions)
        self.assertIn(ActionType.ARRANGE_CLIPS, cmd.actions)

    def test_rough_cut(self):
        cmd = self.parser.parse("Create a rough cut")
        self.assertIn(ActionType.ROUGH_CUT, cmd.actions)
        self.assertIn(ActionType.REMOVE_SILENCE, cmd.actions)
        self.assertIn(ActionType.ARRANGE_CLIPS, cmd.actions)

    def test_combined_all(self):
        cmd = self.parser.parse("Remove silence, arrange the clips, and label shaky footage")
        self.assertIn(ActionType.REMOVE_SILENCE, cmd.actions)
        self.assertIn(ActionType.ARRANGE_CLIPS, cmd.actions)
        self.assertIn(ActionType.DETECT_SHAKY, cmd.actions)
        self.assertIn(ActionType.LABEL_SHAKY, cmd.actions)

    def test_user_prompt_detect_and_split_remove_shaky(self):
        prompt = (
            "Detect the exact timestamps of shaky portions and actually split and remove "
            "those portions from the timeline. Do not only label them. For example, if a "
            "20-second clip has shake from 5–8 seconds, the timeline after applying must "
            "contain 0–5 seconds and 8–20 seconds. The source video file must remain unchanged."
        )
        cmd = self.parser.parse(prompt)
        self.assertIn(ActionType.DELETE_SHAKY, cmd.actions)
        self.assertIn(ActionType.DETECT_SHAKY, cmd.actions)
        self.assertNotIn(ActionType.LABEL_SHAKY, cmd.actions)
        self.assertFalse(cmd.parameters.get("delete_shaky", {}).get("close_gaps", True))
        self.assertFalse(cmd.parameters.get("shaky", {}).get("add_marker", True))

    def test_do_not_label_negation(self):
        cmd = self.parser.parse("Find shaky clips, split and remove them, do not label them")
        self.assertIn(ActionType.DELETE_SHAKY, cmd.actions)
        self.assertNotIn(ActionType.LABEL_SHAKY, cmd.actions)

    def test_delete_shaky_close_gaps_flag(self):
        cmd = self.parser.parse("Trim shaky footage and close gaps")
        self.assertIn(ActionType.DELETE_SHAKY, cmd.actions)
        self.assertTrue(cmd.parameters.get("delete_shaky", {}).get("close_gaps", False))


class TestCommandSchema(unittest.TestCase):
    """Test schema validation and normalization."""

    def test_valid_json_string(self):
        raw_json = '{"actions": ["remove_silence", "detect_shaky"]}'
        cmd = CommandSchemaValidator.validate_and_normalize(raw_json)
        self.assertEqual(cmd.actions, [ActionType.REMOVE_SILENCE, ActionType.DETECT_SHAKY])

    def test_markdown_codeblock_cleaning(self):
        raw = '```json\n{"actions": ["arrange_clips"]}\n```'
        cmd = CommandSchemaValidator.validate_and_normalize(raw)
        self.assertEqual(cmd.actions, [ActionType.ARRANGE_CLIPS])

    def test_malformed_json_fallback(self):
        raw = "Not JSON at all"
        cmd = CommandSchemaValidator.validate_and_normalize(raw)
        self.assertEqual(cmd.actions, [])

    def test_label_shaky_implies_detect(self):
        raw = {"actions": ["label_shaky"]}
        cmd = CommandSchemaValidator.validate_and_normalize(raw)
        self.assertIn(ActionType.DETECT_SHAKY, cmd.actions)
        self.assertIn(ActionType.LABEL_SHAKY, cmd.actions)


class TestVideoAnalyzer(unittest.TestCase):
    """Test camera shake detection."""

    def setUp(self):
        self.analyzer = VideoAnalyzer()

    def test_nonexistent_file_handled_safely(self):
        res = self.analyzer.analyze_shaky_footage("non_existent_file_xyz123.mp4")
        self.assertFalse(res["is_shaky"])
        self.assertEqual(res["shake_score"], 0.0)
        self.assertIn("error", res)

    def test_heuristic_analysis_shaky_name(self):
        res = self.analyzer._heuristic_analysis("vacation_shaky_camera.mp4")
        self.assertTrue(res["is_shaky"])
        self.assertGreater(res["shake_score"], 0.5)

    def test_heuristic_analysis_stable_name(self):
        res = self.analyzer._heuristic_analysis("interview_tripod.mp4")
        self.assertFalse(res["is_shaky"])
        self.assertLess(res["shake_score"], 0.3)


class TestEditingController(unittest.TestCase):
    """Test AI plan generation and human-in-the-loop review."""

    def setUp(self):
        self.controller = EditingController()

    @patch("os.path.isfile", return_value=True)
    @patch("classes.query.Clip.filter")
    @patch("classes.query.File.filter")
    def test_plan_generation_does_not_mutate_clips(self, mock_file_filter, mock_clip_filter, mock_isfile):
        mock_clip = MagicMock()
        mock_clip.id = "c1"
        mock_clip.title.return_value = "Test Clip"
        mock_clip.data = {
            "title": "Test Clip",
            "position": 0.0,
            "start": 0.0,
            "end": 10.0,
            "reader": {"path": "/fake/test.mp4", "has_video": True}
        }
        mock_clip_filter.return_value = [mock_clip]
        mock_file_filter.return_value = []

        
        self.controller.video_analyzer.analyze_shaky_footage = MagicMock(return_value={
            "is_shaky": True,
            "shake_score": 0.85,
            "shaky_segments": [{"start": 1.0, "end": 4.0}]
        })

        cmd = SLMCommand(actions=[ActionType.DETECT_SHAKY, ActionType.LABEL_SHAKY])
        plan = self.controller.generate_plan(cmd)

        self.assertFalse(plan.is_empty)
        self.assertEqual(len(plan.items), 2)
        
        self.assertEqual(mock_clip.data["title"], "Test Clip")
        mock_clip.save.assert_not_called()

    @patch("classes.query.Clip.save")
    @patch("classes.query.Marker.save")
    @patch("classes.app.get_app")
    def test_apply_plan_labels_shaky_without_deleting(self, mock_get_app, mock_marker_save, mock_clip_save):
        mock_app = MagicMock()
        mock_app.project.get.return_value = [{"number": 1000000}]
        mock_app.project.generate_id.return_value = "m1"
        mock_get_app.return_value = mock_app

        orig_clip = MagicMock()
        orig_clip.id = "c1"
        orig_clip.title.return_value = "My Footage"
        orig_clip.data = {"title": "My Footage", "position": 2.5, "duration": 4.0}

        plan = AIPlan(
            command=SLMCommand(actions=[ActionType.LABEL_SHAKY]),
            items=[PlanItem(ActionType.LABEL_SHAKY, "Label shaky footage")],
            operations=[{
                "type": ActionType.LABEL_SHAKY,
                "clips": [{
                    "clip_id": "c1",
                    "clip_name": "My Footage",
                    "position": 2.5,
                    "duration": 4.0,
                    "shake_percentage": 65.0,
                    "classification": "Shaky"
                }]
            }],
            is_empty=False
        )

        with patch.object(self.controller.shaky_service, "find_or_create_top_unused_layer", return_value=3000000):
            res = self.controller.apply_plan(plan)
            self.assertTrue(res["success"])
            self.assertIn("SHAKY FOOTAGE", res["message"])
            
            orig_clip.save.assert_not_called()
            orig_clip.delete.assert_not_called()
            self.assertEqual(orig_clip.data["title"], "My Footage")

    @patch("classes.query.Clip.save")
    @patch("classes.query.Clip.get")
    @patch("classes.app.get_app")
    def test_apply_plan_split_and_remove_shaky_keeps_source_unchanged(self, mock_get_app, mock_clip_get, mock_clip_save):
        mock_app = MagicMock()
        mock_app.updates.transaction_id = None
        mock_get_app.return_value = mock_app

        orig_clip = MagicMock()
        orig_clip.id = "c_20s"
        orig_clip.title.return_value = "source_camera.mp4"
        orig_clip.data = {
            "title": "source_camera.mp4",
            "position": 0.0,
            "start": 0.0,
            "end": 20.0,
            "duration": 20.0,
            "layer": 1000000,
            "reader": {"path": "/videos/source_camera.mp4", "has_video": True}
        }
        mock_clip_get.return_value = orig_clip

        plan = AIPlan(
            command=SLMCommand(
                actions=[ActionType.DELETE_SHAKY],
                parameters={"delete_shaky": {"close_gaps": False}}
            ),
            items=[PlanItem(ActionType.DELETE_SHAKY, "Split and remove shaky footage")],
            operations=[{
                "type": ActionType.DELETE_SHAKY,
                "regions": [{
                    "clip_id": "c_20s",
                    "clip_start": 0.0,
                    "clip_end": 20.0,
                    "timeline_start": 5.0,
                    "timeline_end": 8.0,
                    "timeline_duration": 3.0,
                    "shake_percentage": 75.0,
                    "classification": "Very Shaky"
                }],
                "close_gaps": False
            }],
            is_empty=False
        )

        res = self.controller.apply_plan(plan)
        self.assertTrue(res["success"])
        self.assertIn("Split and removed 1 shaky segment(s)", res["message"])

        
        self.assertEqual(orig_clip.data["position"], 0.0)
        self.assertEqual(orig_clip.data["start"], 0.0)
        self.assertEqual(orig_clip.data["end"], 5.0)
        self.assertEqual(orig_clip.data["duration"], 5.0)
        
        self.assertEqual(orig_clip.data["reader"]["path"], "/videos/source_camera.mp4")

        
        self.assertGreaterEqual(mock_clip_save.call_count, 1)


if __name__ == "__main__":
    unittest.main()
