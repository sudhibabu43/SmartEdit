"""
@file
@brief Service layer for Duplicate Clip Detection using video frame perceptual hashing (dHash).
@author SmartEdit Team
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV (cv2) is not available. Duplicate detection will use fallback heuristics.")


class DuplicateDetectorService:
    """
    Analyzes clips to find duplicates by computing and comparing visual signatures (dHash).
    """
    def __init__(self, sample_frames_count: int = 5, hash_size: int = 8, similarity_threshold: float = 0.90):
        self.sample_frames_count = sample_frames_count
        self.hash_size = hash_size
        self.similarity_threshold = similarity_threshold
        # Cache for hashes to avoid re-computing for the same file in the same session
        self._hash_cache: Dict[str, str] = {}

    def find_duplicate_groups(self, clips: List[Any], only_selected: bool = False) -> List[Dict[str, Any]]:
        """
        Takes a list of clips and returns a list of 'duplicate groups'.
        Each group is a dictionary describing the duplicate clips and similarity.
        """
        # If there are fewer than 2 clips, there can be no duplicates.
        if len(clips) < 2:
            return []

        # Step 1: Compute or retrieve signatures for all clips
        clip_signatures = []
        for clip in clips:
            path = self._get_clip_path(clip)
            if not path or not os.path.exists(path):
                continue
                
            c_data = clip.data if isinstance(clip.data, dict) else {}
            # Base heuristic uses file size and duration if OpenCV is unavailable
            dur = float(c_data.get("duration", 0.0))
            
            sig = self._get_video_signature(path)
            
            clip_signatures.append({
                "clip": clip,
                "path": path,
                "title": c_data.get("title", f"Clip {clip.id}"),
                "duration": dur,
                "start": float(c_data.get("start", 0.0)),
                "end": float(c_data.get("end", 0.0)),
                "position": float(c_data.get("position", 0.0)),
                "signature": sig
            })

        # Step 2: Compare signatures to cluster duplicates
        duplicate_groups = []
        visited_indices = set()

        for i in range(len(clip_signatures)):
            if i in visited_indices:
                continue

            current_group = [clip_signatures[i]]
            visited_indices.add(i)

            for j in range(i + 1, len(clip_signatures)):
                if j in visited_indices:
                    continue

                similarity = self._compute_similarity(clip_signatures[i]["signature"], clip_signatures[j]["signature"])
                
                # Check for near or exact duplicate
                if similarity >= self.similarity_threshold:
                    current_group.append(clip_signatures[j])
                    clip_signatures[j]["_similarity_to_primary"] = similarity
                    visited_indices.add(j)

            if len(current_group) > 1:
                # Group found!
                
                # Default primary similarity to 1.0
                current_group[0]["_similarity_to_primary"] = 1.0
                
                # Calculate average similarity for the group description
                avg_sim = sum(item.get("_similarity_to_primary", 1.0) for item in current_group[1:]) / (len(current_group) - 1)
                
                # Sort by start time/position so the earliest clip is considered the "Primary" one to keep
                current_group.sort(key=lambda x: x["position"])

                group_info = {
                    "group_id": i + 1,
                    "primary_clip": current_group[0]["clip"],
                    "primary_title": current_group[0]["title"],
                    "similarity_percent": round(avg_sim * 100, 1),
                    "duplicate_clips": [],
                    "all_clips_in_group": [c["clip"] for c in current_group]
                }
                
                for dup in current_group[1:]:
                    group_info["duplicate_clips"].append({
                        "clip": dup["clip"],
                        "title": dup["title"],
                        "similarity": round(dup.get("_similarity_to_primary", 1.0) * 100, 1),
                        "position": dup["position"],
                        "duration": dup["duration"]
                    })
                    
                duplicate_groups.append(group_info)

        return duplicate_groups

    def _get_video_signature(self, video_path: str) -> str:
        """
        Computes a visual signature for a video by sampling frames and computing dHashes.
        Returns a hex string representing the concatenated frame hashes.
        """
        if video_path in self._hash_cache:
            return self._hash_cache[video_path]
            
        if not OPENCV_AVAILABLE:
            return self._fallback_signature(video_path)
            
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return self._fallback_signature(video_path)

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                cap.release()
                return self._fallback_signature(video_path)

            # Pick evenly spaced frames to sample
            step = max(1, total_frames // (self.sample_frames_count + 1))
            
            frame_hashes = []
            
            for i in range(1, self.sample_frames_count + 1):
                target_frame = i * step
                if target_frame >= total_frames:
                    target_frame = total_frames - 1
                    
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # Compute dHash
                    h = self._dhash(frame)
                    frame_hashes.append(h)
                    
            cap.release()
            
            if not frame_hashes:
                return self._fallback_signature(video_path)
                
            # Concatenate binary hashes to form the signature
            signature = "".join(frame_hashes)
            self._hash_cache[video_path] = signature
            return signature

        except Exception as e:
            logger.warning(f"Error computing video signature for {video_path}: {e}")
            return self._fallback_signature(video_path)

    def _dhash(self, image: Any) -> str:
        """
        Difference Hash: Convert to grayscale, resize to (hash_size + 1) x hash_size,
        compare adjacent pixels. Returns a binary string.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Resize to 9x8
            resized = cv2.resize(gray, (self.hash_size + 1, self.hash_size), interpolation=cv2.INTER_AREA)
            
            # Compare adjacent pixels
            diff = resized[:, 1:] > resized[:, :-1]
            
            # Convert boolean array to binary string
            return "".join(["1" if b else "0" for b in diff.flatten()])
        except Exception:
            return "0" * (self.hash_size * self.hash_size)

    def _compute_similarity(self, sig1: str, sig2: str) -> float:
        """
        Computes the similarity between two signatures.
        If signatures are binary strings of the same length, computes 1 - (Hamming distance / length).
        If they are fallback string identifiers (like size_duration), uses string equality.
        """
        if len(sig1) != len(sig2) or len(sig1) == 0:
            return 1.0 if sig1 == sig2 else 0.0
            
        # Try binary string hamming distance
        if set(sig1).issubset({"0", "1"}) and set(sig2).issubset({"0", "1"}):
            differences = sum(1 for a, b in zip(sig1, sig2) if a != b)
            return 1.0 - (differences / len(sig1))
            
        # Fallback equality
        return 1.0 if sig1 == sig2 else 0.0

    def _fallback_signature(self, video_path: str) -> str:
        """Fallback signature using file size to simulate basic duplicate detection if OpenCV is missing."""
        try:
            size = os.path.getsize(video_path)
            # Create a string representation as signature
            sig = f"size_{size}"
            self._hash_cache[video_path] = sig
            return sig
        except Exception:
            return "unknown"

    def _get_clip_path(self, clip: Any) -> str:
        c_data = clip.data if isinstance(clip.data, dict) else {}
        path = c_data.get("reader", {}).get("path") or ""
        if not path and c_data.get("file_id"):
            from classes.query import File
            try:
                f = File.get(id=c_data.get("file_id"))
                if f:
                    path = f.absolute_path()
            except Exception:
                pass
        return path
