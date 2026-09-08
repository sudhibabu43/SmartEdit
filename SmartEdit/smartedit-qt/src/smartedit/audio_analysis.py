"""
 @file
 @brief Audio analysis and silence detection using Librosa and FFmpeg.
 @author SmartEdit Team

 Detects silent sections, calculates precise cut points, and segments media into
 highlighted speech/audio clips and cut points for automated rough-cut editing.
"""

import os
import shutil
import subprocess
import tempfile
import logging
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Analyzes audio and video files for silent segments and generates cut points.
    """

    DEFAULT_FFMPEG_PATH = r"C:\msys64\ucrt64\bin\ffmpeg.exe"

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or (
            self.DEFAULT_FFMPEG_PATH
            if os.path.exists(self.DEFAULT_FFMPEG_PATH)
            else shutil.which("ffmpeg")
        )

    def extract_audio_if_needed(self, media_path: str, sample_rate: int = 22050) -> Tuple[str, bool]:
        """
        Ensures an audio file exists for media_path. If media_path is a video file,
        extracts the audio track to a temporary WAV file using FFmpeg.

        Returns:
            (audio_filepath, is_temporary)
        """
        ext = os.path.splitext(media_path)[1].lower()
        video_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}

        if ext in video_extensions and self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            temp_wav = os.path.join(tempfile.gettempdir(), f"smartedit_audio_{os.getpid()}_{id(media_path)}.wav")
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", media_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(sample_rate),
                "-ac", "1",
                temp_wav
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                    return temp_wav, True
            except Exception as e:
                logger.warning("FFmpeg audio extraction failed, falling back to direct librosa load: %s", e)

        return media_path, False

    def detect_silence(
        self,
        audio_path: str,
        top_db: float = 25.0,
        min_silence_duration_sec: float = 0.4,
        frame_length: int = 2048,
        hop_length: int = 512
    ) -> List[Tuple[float, float]]:
        """
        Detects silent regions in an audio or video file using Librosa.

        Args:
            audio_path: Path to audio or video file.
            top_db: Threshold in decibels below peak audio volume to consider silence.
            min_silence_duration_sec: Minimum gap duration in seconds to classify as silence.
            frame_length: Librosa frame length for analysis.
            hop_length: Librosa hop length for analysis.

        Returns:
            List of (start_sec, end_sec) tuples representing silent segments.
        """
        analysis_path, is_temp = self.extract_audio_if_needed(audio_path)
        try:
            y, sr = librosa.load(analysis_path, sr=22050, mono=True)
            total_duration = float(len(y)) / float(sr)

            if len(y) == 0:
                return []

            # Find non-silent intervals using librosa split
            non_silent_intervals = librosa.effects.split(
                y,
                top_db=top_db,
                frame_length=frame_length,
                hop_length=hop_length
            )

            # Convert non-silent sample indices to seconds
            non_silent_sec = [
                (float(start) / float(sr), float(end) / float(sr))
                for start, end in non_silent_intervals
            ]

            # Invert non-silent intervals to find silent regions
            silences = []
            current_time = 0.0

            for start, end in non_silent_sec:
                if start - current_time >= min_silence_duration_sec:
                    silences.append((round(current_time, 3), round(start, 3)))
                current_time = max(current_time, end)

            if total_duration - current_time >= min_silence_duration_sec:
                silences.append((round(current_time, 3), round(total_duration, 3)))

            return silences
        finally:
            if is_temp and os.path.exists(analysis_path):
                try:
                    os.remove(analysis_path)
                except Exception:
                    pass

    def generate_cut_points(
        self,
        audio_path: str,
        top_db: float = 25.0,
        min_silence_duration_sec: float = 0.4,
        padding_sec: float = 0.08
    ) -> Dict[str, Any]:
        """
        Analyzes media for silence and generates precise cut points and highlighted clips.

        Args:
            audio_path: Path to audio or video file.
            top_db: Silence threshold (dB below reference). Higher = more sensitive to silence.
            min_silence_duration_sec: Minimum duration of silence to trigger a cut.
            padding_sec: Margin added around kept speech to avoid cutting off word edges.

        Returns:
            Structured dictionary with:
                - total_duration
                - silent_segments
                - kept_clips (highlighted)
                - all_segments (ordered sequence for timeline display)
                - cut_points (split timestamps)
                - statistics (time saved, % silence removed)
        """
        analysis_path, is_temp = self.extract_audio_if_needed(audio_path)
        try:
            y, sr = librosa.load(analysis_path, sr=22050, mono=True)
            total_duration = round(float(len(y)) / float(sr), 3)

            if len(y) == 0:
                return self._empty_cut_result(total_duration)

            # Find non-silent intervals (speech / active audio)
            non_silent_intervals = librosa.effects.split(
                y,
                top_db=top_db,
                frame_length=2048,
                hop_length=512
            )

            # Convert to seconds
            raw_kept = [
                (float(start) / float(sr), float(end) / float(sr))
                for start, end in non_silent_intervals
            ]

            if not raw_kept:
                # Completely silent audio
                return {
                    "total_duration": total_duration,
                    "silent_segments": [{"start": 0.0, "end": total_duration, "duration": total_duration}],
                    "kept_clips": [],
                    "all_segments": [{
                        "type": "SILENCE_CUT",
                        "start": 0.0,
                        "end": total_duration,
                        "duration": total_duration,
                        "highlight": False
                    }],
                    "cut_points": [0.0, total_duration],
                    "statistics": {
                        "original_duration": total_duration,
                        "silent_duration": total_duration,
                        "kept_duration": 0.0,
                        "silence_percentage": 100.0,
                        "kept_clips_count": 0,
                        "silent_clips_count": 1
                    }
                }

            # Apply padding and merge overlapping intervals
            padded_kept = []
            for s, e in raw_kept:
                ps = max(0.0, s - padding_sec)
                pe = min(total_duration, e + padding_sec)
                padded_kept.append((ps, pe))

            merged_kept = []
            for s, e in padded_kept:
                if not merged_kept:
                    merged_kept.append([s, e])
                else:
                    prev_s, prev_e = merged_kept[-1]
                    if s <= prev_e:
                        # Overlapping or contiguous interval
                        merged_kept[-1][1] = max(prev_e, e)
                    else:
                        merged_kept.append([s, e])

            # Build silent segments and kept clips
            all_segments = []
            kept_clips = []
            silent_segments = []
            cut_points_set = set()

            cur = 0.0
            clip_idx = 1
            silence_idx = 1

            for start, end in merged_kept:
                start = round(start, 3)
                end = round(end, 3)

                # Check for silence before this clip
                if start - cur >= min_silence_duration_sec:
                    sil_dur = round(start - cur, 3)
                    silent_segments.append({
                        "index": silence_idx,
                        "start": cur,
                        "end": start,
                        "duration": sil_dur
                    })
                    all_segments.append({
                        "type": "SILENCE_CUT",
                        "index": silence_idx,
                        "start": cur,
                        "end": start,
                        "duration": sil_dur,
                        "highlight": False
                    })
                    cut_points_set.add(cur)
                    cut_points_set.add(start)
                    silence_idx += 1

                # Kept speech/audio clip
                clip_dur = round(end - start, 3)
                if clip_dur > 0.05:
                    kept_clips.append({
                        "clip_index": clip_idx,
                        "start_time": start,
                        "end_time": end,
                        "duration": clip_dur,
                        "status": "KEEP",
                        "highlight": True
                    })
                    all_segments.append({
                        "type": "KEEP",
                        "clip_index": clip_idx,
                        "start": start,
                        "end": end,
                        "duration": clip_dur,
                        "highlight": True
                    })
                    cut_points_set.add(start)
                    cut_points_set.add(end)
                    clip_idx += 1

                cur = max(cur, end)

            # Check trailing silence
            if total_duration - cur >= min_silence_duration_sec:
                sil_dur = round(total_duration - cur, 3)
                silent_segments.append({
                    "index": silence_idx,
                    "start": cur,
                    "end": total_duration,
                    "duration": sil_dur
                })
                all_segments.append({
                    "type": "SILENCE_CUT",
                    "index": silence_idx,
                    "start": cur,
                    "end": total_duration,
                    "duration": sil_dur,
                    "highlight": False
                })
                cut_points_set.add(cur)
                cut_points_set.add(total_duration)

            cut_points = sorted([round(p, 3) for p in cut_points_set if 0.0 < p < total_duration])
            total_kept = round(sum(c["duration"] for c in kept_clips), 3)
            total_silent = round(sum(s["duration"] for s in silent_segments), 3)
            pct_silence = round((total_silent / total_duration) * 100.0, 1) if total_duration > 0 else 0.0

            return {
                "media_path": audio_path,
                "total_duration": total_duration,
                "silent_segments": silent_segments,
                "kept_clips": kept_clips,
                "all_segments": all_segments,
                "cut_points": cut_points,
                "statistics": {
                    "original_duration": total_duration,
                    "silent_duration": total_silent,
                    "kept_duration": total_kept,
                    "silence_percentage": pct_silence,
                    "kept_clips_count": len(kept_clips),
                    "silent_clips_count": len(silent_segments)
                }
            }
        finally:
            if is_temp and os.path.exists(analysis_path):
                try:
                    os.remove(analysis_path)
                except Exception:
                    pass

    @classmethod
    def create_sample_audio(cls, output_path: Optional[str] = None, sr: int = 22050) -> str:
        """
        Creates a synthetic demonstration audio file containing 3 speech/tone bursts
        and 2 clear silent pauses. Perfect for 1-click testing and demonstration.
        """
        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), "smartedit_silence_demo.wav")

        # Audio structure:
        # 1. 0.0s - 1.8s: Speech burst 1 (440Hz harmonic tone + subtle modulation)
        # 2. 1.8s - 3.2s: Silence gap 1 (1.4s dead air)
        # 3. 3.2s - 5.5s: Speech burst 2 (520Hz tone)
        # 4. 5.5s - 7.0s: Silence gap 2 (1.5s dead air)
        # 5. 7.0s - 9.0s: Speech burst 3 (440Hz tone)
        # Total duration = 9.0s, Silence = 2.9s (~32%)

        def make_tone(duration, freq):
            t = np.linspace(0, duration, int(duration * sr), endpoint=False)
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t)))  # smooth ramp
            tone = 0.4 * np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(4 * np.pi * freq * t)
            return tone * envelope

        part1 = make_tone(1.8, 440)
        silence1 = np.zeros(int(1.4 * sr))
        part2 = make_tone(2.3, 520)
        silence2 = np.zeros(int(1.5 * sr))
        part3 = make_tone(2.0, 440)

        waveform = np.concatenate([part1, silence1, part2, silence2, part3]).astype(np.float32)
        sf.write(output_path, waveform, sr)
        return output_path

    def _empty_cut_result(self, duration: float) -> Dict[str, Any]:
        return {
            "total_duration": duration,
            "silent_segments": [],
            "kept_clips": [],
            "all_segments": [],
            "cut_points": [],
            "statistics": {
                "original_duration": duration,
                "silent_duration": 0.0,
                "kept_duration": duration,
                "silence_percentage": 0.0,
                "kept_clips_count": 0,
                "silent_clips_count": 0
            }
        }
