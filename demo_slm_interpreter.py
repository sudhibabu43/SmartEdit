"""
SmartEdit - SLM Video Editing Assistant Demo
=============================================

Demonstrates the complete SLM pipeline:
1. User prompt -> Small Language Model
2. Structured JSON editing commands
3. SmartEdit Editing Controller -> AI Plan generation (Human-in-the-loop)
4. Timeline operations (silence removal, clip arrangement, camera shake detection & labeling)

Usage:
    python demo_slm_interpreter.py
    python demo_slm_interpreter.py "Arrange the clips in the best order"
    python demo_slm_interpreter.py "Remove silence and shaky clips."
    python demo_slm_interpreter.py "Remove silence, arrange the clips, and label shaky footage"
"""

import sys
import os
import io

# Ensure UTF-8 output in Windows PowerShell/cmd terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Set up paths
_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_DIR, "launch.py")):
    _SRC = _DIR
else:
    _SRC = os.path.join(_DIR, "SmartEdit", "smartedit-qt", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from slm.prompt_parser import PromptParser
from slm.editing_controller import EditingController
from slm.command_schema import ActionType


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Remove silence, arrange the clips, and label shaky footage"

    parser = PromptParser()
    controller = EditingController()

    print("=" * 70)
    print("      SmartEdit - SLM Video Editing Assistant Pipeline Demo")
    print("=" * 70)
    print(f"\n1. User Prompt:\n   \"{prompt}\"\n")

    # Step 2: SLM converts to structured JSON
    print("2. SLM Structured Editing Commands (JSON):")
    print("-" * 70)
    command = parser.parse(prompt)
    print(command.to_json(indent=2))
    print("-" * 70)

    # Step 3: Editing Controller formulates Human-in-the-loop plan
    print("\n3. SmartEdit Editing Controller - AI Plan (Human-in-the-loop Review):")
    print("-" * 70)

    # Create realistic sample mock clips for preview demonstration
    class MockClip:
        def __init__(self, cid, name, duration, is_shaky=False, has_silence=False):
            self.id = cid
            self._name = name
            self.data = {
                "title": name,
                "position": 0.0,
                "start": 0.0,
                "end": duration,
                "duration": duration,
                "reader": {"path": f"/media/{name}", "has_video": True, "has_audio": True}
            }
            self.is_shaky = is_shaky
            self.has_silence = has_silence

        def title(self):
            return self._name

    sample_clips = [
        MockClip("c1", "intro_dialogue.mp4", 18.0, is_shaky=False, has_silence=True),
        MockClip("c2", "handheld_action_walk.mp4", 24.0, is_shaky=True, has_silence=False),
        MockClip("c3", "product_demo_broll.mp4", 15.0, is_shaky=False, has_silence=True),
        MockClip("c4", "unstable_outdoor_run.mp4", 20.0, is_shaky=True, has_silence=False),
    ]

    # Monkeypatch analyzer for demo purposes if files do not exist on disk
    orig_analyze = controller.video_analyzer.analyze_shaky_footage
    controller.video_analyzer.analyze_shaky_footage = lambda path, **kw: {
        "is_shaky": "handheld" in path or "unstable" in path,
        "shake_score": 0.84 if ("handheld" in path or "unstable" in path) else 0.18,
        "shaky_segments": [{"start": 2.0, "end": 6.5}] if ("handheld" in path or "unstable" in path) else []
    }

    # Generate plan
    import unittest.mock as mock
    with mock.patch("os.path.isfile", return_value=True), \
         mock.patch("smartedit.audio_analysis.AudioAnalyzer.generate_cut_points", return_value={"cut_points": [1.8, 3.2], "time_saved_sec": 4.6}):
        plan = controller.generate_plan(command, clips=sample_clips)

    print("   AI Plan:")
    for item in plan.items:
        clean_desc = item.description.replace("<b>", "").replace("</b>", "").replace("<span style='color:#e74c3c;'>", "").replace("</span>", "")
        print(f"   {item.icon} {clean_desc}")

    print("\n   [Buttons available in SmartEdit Assistant Panel]:")
    print("   [Apply Changes]   [Reject]   [Undo]")
    print("-" * 70)

    # Step 4: Show what Apply does
    print("\n4. Timeline Execution Result:")
    if command.has_action(ActionType.DELETE_SHAKY):
        print("   * Shaky portions are split at boundaries and removed from timeline (source files untouched).")
        print("   * Stable portions (e.g. 0–5s and 8–20s) are preserved.")
    elif command.has_action(ActionType.LABEL_SHAKY):
        print("   * Shaky clips marked with: '⚠️ [SHAKY FOOTAGE]' label + Timeline Marker.")
        print("   * Shaky footage kept on timeline for human editing review.")
    if command.has_action(ActionType.REMOVE_SILENCE):
        print("   * Silence trimmed at cut points.")
    if command.has_action(ActionType.ARRANGE_CLIPS):
        print("   * All clips aligned sequentially on primary track with 0 gaps.")
    print("   * Operations bundled in an atomic undo transaction.")
    print("=" * 70)


if __name__ == "__main__":
    main()
