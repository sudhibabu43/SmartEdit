"""
 @file
 @brief Unit tests for SLM Prompt Interpreter.
 @author SmartEdit Team
"""

import json
import unittest
from smartedit.prompt_interpreter import PromptInterpreter


class TestPromptInterpreter(unittest.TestCase):
    def setUp(self):
        self.interpreter = PromptInterpreter()

    def test_user_prompt_remove_silence_and_shaky(self):
        """Test exact prompt requested: 'Remove silence and shaky clips.'"""
        prompt = "Remove silence and shaky clips."
        result = self.interpreter.interpret_prompt(prompt)

        self.assertEqual(result["raw_prompt"], prompt)
        self.assertTrue(result["filters"]["remove_silence"])
        self.assertTrue(result["filters"]["remove_shaky"])
        self.assertFalse(result["filters"]["remove_blur"])

        
        self.assertTrue(result["remove_silence"])
        self.assertTrue(result["remove_shaky"])

        
        action_names = [a["action"] for a in result["actions"]]
        self.assertIn("remove_silence", action_names)
        self.assertIn("remove_shaky", action_names)

        
        json_str = self.interpreter.interpret_to_json(prompt)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["filters"]["remove_silence"], True)
        self.assertEqual(parsed["filters"]["remove_shaky"], True)

    def test_silence_variations_and_negations(self):
        """Test various ways to request silence removal, as well as explicit negations."""
        self.assertTrue(self.interpreter.interpret_prompt("Cut out pauses and dead air")["filters"]["remove_silence"])
        self.assertTrue(self.interpreter.interpret_prompt("Trim silent sections")["filters"]["remove_silence"])
        self.assertTrue(self.interpreter.interpret_prompt("No silence please")["filters"]["remove_silence"])

        
        self.assertFalse(self.interpreter.interpret_prompt("Don't remove silence")["filters"]["remove_silence"])
        self.assertFalse(self.interpreter.interpret_prompt("Keep silence and pauses")["filters"]["remove_silence"])

    def test_shaky_variations_and_negations(self):
        """Test shaky footage removal phrasing and negations."""
        self.assertTrue(self.interpreter.interpret_prompt("Filter out jittery camera shots")["filters"]["remove_shaky"])
        self.assertTrue(self.interpreter.interpret_prompt("Stabilize the video")["filters"]["remove_shaky"])
        self.assertTrue(self.interpreter.interpret_prompt("Drop unstable clips")["filters"]["remove_shaky"])

        
        self.assertFalse(self.interpreter.interpret_prompt("Keep shaky camera shake for documentary look")["filters"]["remove_shaky"])
        self.assertFalse(self.interpreter.interpret_prompt("Don't filter shaky")["filters"]["remove_shaky"])

    def test_duration_parsing(self):
        """Test duration detection in seconds, minutes, and shorthand."""
        self.assertEqual(self.interpreter.interpret_prompt("Make it 30 seconds")["timeline_settings"]["target_duration_sec"], 30)
        self.assertEqual(self.interpreter.interpret_prompt("Target duration 1 minute")["timeline_settings"]["target_duration_sec"], 60)
        self.assertEqual(self.interpreter.interpret_prompt("Cut into a 45s reel")["timeline_settings"]["target_duration_sec"], 45)
        self.assertEqual(self.interpreter.interpret_prompt("2 minutes recap")["timeline_settings"]["target_duration_sec"], 120)

    def test_style_and_pacing(self):
        """Test style and pacing classification."""
        cinematic = self.interpreter.interpret_prompt("Cinematic travel movie with slow pace")
        self.assertEqual(cinematic["timeline_settings"]["style"], "cinematic")
        self.assertEqual(cinematic["timeline_settings"]["pacing"], "slow")

        fast_montage = self.interpreter.interpret_prompt("Fast paced montage with quick cuts and upbeat music")
        self.assertEqual(fast_montage["timeline_settings"]["style"], "montage")
        self.assertEqual(fast_montage["timeline_settings"]["pacing"], "fast")
        self.assertTrue(fast_montage["audio_settings"]["add_background_music"])
        self.assertEqual(fast_montage["audio_settings"]["music_genre"], "upbeat")

    def test_aspect_ratio_detection(self):
        """Test vertical and horizontal aspect ratio inference."""
        tiktok = self.interpreter.interpret_prompt("Create a TikTok 9:16 short, remove silence")
        self.assertEqual(tiktok["timeline_settings"]["aspect_ratio"], "9:16")

        youtube = self.interpreter.interpret_prompt("YouTube widescreen 16:9 tutorial")
        self.assertEqual(youtube["timeline_settings"]["aspect_ratio"], "16:9")
        self.assertEqual(youtube["timeline_settings"]["style"], "tutorial")

    def test_empty_prompt(self):
        """Test graceful handling of empty or blank prompts."""
        empty = self.interpreter.interpret_prompt("")
        self.assertEqual(empty["raw_prompt"], "")
        self.assertEqual(empty["actions"], [])
        self.assertFalse(empty["filters"]["remove_silence"])
        self.assertFalse(empty["filters"]["remove_shaky"])


if __name__ == "__main__":
    unittest.main()
