"""
 @file
 @brief Unit tests for AudioAnalyzer silence detection and cut points generation.
 @author SmartEdit Team
"""

import os
import unittest
from smartedit.audio_analysis import AudioAnalyzer


class TestSilenceDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = AudioAnalyzer()
        cls.sample_wav = AudioAnalyzer.create_sample_audio()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.sample_wav):
            try:
                os.remove(cls.sample_wav)
            except Exception:
                pass

    def test_sample_audio_creation(self):
        """Verify sample audio file was created and is non-empty."""
        self.assertTrue(os.path.exists(self.sample_wav))
        self.assertGreater(os.path.getsize(self.sample_wav), 1000)

    def test_detect_silence_intervals(self):
        """Verify detect_silence identifies the two silence gaps in demo audio."""
        silences = self.analyzer.detect_silence(self.sample_wav, top_db=25, min_silence_duration_sec=0.4)
        self.assertGreaterEqual(len(silences), 2)

        
        gap1_start, gap1_end = silences[0]
        self.assertAlmostEqual(gap1_start, 1.8, delta=0.3)
        self.assertAlmostEqual(gap1_end, 3.2, delta=0.3)

        
        gap2_start, gap2_end = silences[1]
        self.assertAlmostEqual(gap2_start, 5.5, delta=0.3)
        self.assertAlmostEqual(gap2_end, 7.0, delta=0.3)

    def test_generate_cut_points(self):
        """Verify generate_cut_points produces 3 kept clips, cut points, and valid statistics."""
        result = self.analyzer.generate_cut_points(self.sample_wav, top_db=25, min_silence_duration_sec=0.4)

        self.assertIn("total_duration", result)
        self.assertAlmostEqual(result["total_duration"], 9.0, delta=0.2)

        
        kept = result["kept_clips"]
        self.assertEqual(len(kept), 3)
        for clip in kept:
            self.assertEqual(clip["status"], "KEEP")
            self.assertTrue(clip["highlight"])
            self.assertGreater(clip["duration"], 0.5)

        
        silent = result["silent_segments"]
        self.assertEqual(len(silent), 2)
        for s in silent:
            self.assertGreaterEqual(s["duration"], 0.4)

        
        cut_points = result["cut_points"]
        self.assertGreaterEqual(len(cut_points), 4)

        
        stats = result["statistics"]
        self.assertAlmostEqual(stats["original_duration"], 9.0, delta=0.2)
        self.assertGreater(stats["silent_duration"], 1.5)
        self.assertGreater(stats["kept_duration"], 4.0)
        self.assertAlmostEqual(
            stats["silent_duration"] + stats["kept_duration"],
            stats["original_duration"],
            delta=0.1
        )
        self.assertEqual(stats["kept_clips_count"], 3)
        self.assertEqual(stats["silent_clips_count"], 2)


if __name__ == "__main__":
    unittest.main()
