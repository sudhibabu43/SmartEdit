"""
SmartEdit - Silence Detection & Removal Demo
============================================

Demonstrates detecting silent sections, generating cut points, and highlighting
speech/sound clips using Librosa.

Usage:
    python demo_silence_removal.py
    python demo_silence_removal.py path/to/video.mp4
    python demo_silence_removal.py path/to/audio.wav
"""

import sys
import os
import json

# Setup paths
_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_DIR, "launch.py")):
    _SRC = _DIR
else:
    _SRC = os.path.join(_DIR, "SmartEdit", "smartedit-qt", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from smartedit.audio_analysis import AudioAnalyzer


def render_ascii_timeline(result: dict, width: int = 60) -> str:
    """Renders a graphical ASCII timeline showing kept clips and cut silence."""
    total_dur = result["total_duration"]
    if total_dur <= 0:
        return "[Empty Timeline]"

    timeline_chars = []
    sec_per_char = total_dur / float(width)

    for i in range(width):
        t_mid = (i + 0.5) * sec_per_char
        is_kept = any(c["start_time"] <= t_mid <= c["end_time"] for c in result["kept_clips"])
        if is_kept:
            timeline_chars.append("=")  # Kept active clip
        else:
            timeline_chars.append(".")  # Silent section (to cut)

    return "".join(timeline_chars)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 68)
    print("      SmartEdit: Silence Detection & Cut Points Demonstration")
    print("=" * 68)

    analyzer = AudioAnalyzer()

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        media_path = sys.argv[1]
        print(f"\n[INFO] Analyzing user media file: {media_path}")
    else:
        print("\n[INFO] No media file specified. Auto-generating synthetic demo audio...")
        media_path = AudioAnalyzer.create_sample_audio()
        print(f"[OK] Generated demo audio with silence gaps: {media_path}")

    print("\nProcessing audio with Librosa energy split (top_db=25)...")
    result = analyzer.generate_cut_points(media_path, top_db=25, min_silence_duration_sec=0.4)

    stats = result["statistics"]
    print("\n" + "-" * 68)
    print("                 DETECTION & TIMELINE SUMMARY")
    print("-" * 68)
    print(f"  * Original Duration : {stats['original_duration']:.2f} seconds")
    print(f"  * Kept Active Audio : {stats['kept_duration']:.2f} seconds")
    print(f"  * Silent Time Trimmed: {stats['silent_duration']:.2f} seconds ({stats['silence_percentage']:.1f}% removed)")
    print(f"  * Total Kept Clips   : {stats['kept_clips_count']} clips")
    print(f"  * Silent Gaps Found  : {stats['silent_clips_count']} gaps")

    print("\n" + "-" * 68)
    print("                 VISUAL TIMELINE REPRESENTATION")
    print("-" * 68)
    ascii_bar = render_ascii_timeline(result, width=64)
    print(f"  0.0s  |{ascii_bar}|  {stats['original_duration']:.1f}s")
    print("  Legend: [=] Kept Speech/Sound Clip (HIGHLIGHTED)    [.] Silence Cut (REMOVED)")

    print("\n" + "-" * 68)
    print("                 GENERATED CUT POINTS & CLIPS")
    print("-" * 68)
    print(f"  {'#':<4} {'Type':<12} {'Start Time':<12} {'End Time':<12} {'Duration':<10} {'Status'}")
    print("  " + "-" * 64)

    for seg in result["all_segments"]:
        if seg["type"] == "KEEP":
            idx = seg.get("clip_index", 1)
            label = f"Clip #{idx}"
            status = ">> HIGHLIGHT & KEEP"
        else:
            idx = seg.get("index", 1)
            label = f"Silence #{idx}"
            status = "-- CUT & REMOVE"

        print(f"  {idx:<4} {label:<12} {seg['start']:>6.2f}s      {seg['end']:>6.2f}s      {seg['duration']:>6.2f}s     {status}")

    print("  " + "-" * 64)
    print(f"\n  Precise Split Timestamps (Cut Points): {result['cut_points']}")
    print("=" * 68)


if __name__ == "__main__":
    main()
