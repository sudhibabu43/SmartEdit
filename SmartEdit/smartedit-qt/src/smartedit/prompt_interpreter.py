"""
 @file
 @brief Natural language prompt interpretation using Small Language Models (SLM) & Semantic NLP.
 @author SmartEdit Team

 Converts natural language video editing instructions (e.g., "Remove silence and shaky clips.")
 into structured JSON with actions, filter parameters, and timeline targets.
"""

import json
import re
import urllib.request
import urllib.error
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptInterpreter:
    """
    Interprets natural language editing instructions using a Small Language Model (SLM)
    or a built-in deterministic semantic NLP engine.
    """

    DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
    DEFAULT_OPENAI_COMPAT_URL = "http://localhost:1234/v1/chat/completions"

    def __init__(
        self,
        slm_url: Optional[str] = None,
        model: str = "phi3:mini",
        timeout: float = 2.0,
        prefer_local_slm: bool = False
    ):
        """
        Initialize the prompt interpreter.

        Args:
            slm_url: Optional URL of local SLM endpoint (Ollama or OpenAI-compatible).
            model: Model identifier (e.g. 'phi3:mini', 'qwen2.5:0.5b', 'llama3.2:1b').
            timeout: Maximum seconds to wait for SLM before falling back to built-in NLP.
            prefer_local_slm: If True, attempt querying local SLM before NLP fallback.
        """
        self.slm_url = slm_url or self.DEFAULT_OLLAMA_URL
        self.model = model
        self.timeout = timeout
        self.prefer_local_slm = prefer_local_slm

    def interpret_prompt(self, prompt_text: str) -> Dict[str, Any]:
        """
        Interprets a natural language prompt and returns a structured dictionary.

        Args:
            prompt_text: Natural language user instruction (e.g., "Remove silence and shaky clips.").

        Returns:
            Structured dictionary of editing instructions.
        """
        if not prompt_text or not prompt_text.strip():
            return self._default_structure("", summary="Empty prompt provided.")

        prompt_clean = prompt_text.strip()

        # If local SLM is preferred and enabled, attempt SLM first
        if self.prefer_local_slm:
            slm_result = self._try_slm_query(prompt_clean)
            if slm_result:
                return slm_result

        # Built-in high-precision semantic NLP engine (guaranteed instant & offline)
        return self._interpret_with_semantic_nlp(prompt_clean)

    def interpret_to_json(self, prompt_text: str, indent: int = 2) -> str:
        """
        Interprets a prompt and returns the result as a pretty-printed JSON string.
        """
        data = self.interpret_prompt(prompt_text)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    # -------------------------------------------------------------------------
    # Built-in Semantic NLP Parser
    # -------------------------------------------------------------------------
    def _interpret_with_semantic_nlp(self, text: str) -> Dict[str, Any]:
        """Deterministic semantic NLP intent parser."""
        t = text.lower()

        # 1. Detect silence removal
        remove_silence = self._detect_silence_intent(t)

        # 2. Detect shaky removal
        remove_shaky = self._detect_shaky_intent(t)

        # 3. Detect blur removal
        remove_blur = self._detect_blur_intent(t)

        # 4. Target duration
        target_duration = self._detect_duration(t)

        # 5. Pacing
        pacing = self._detect_pacing(t)

        # 6. Style
        style = self._detect_style(t)

        # 7. Aspect ratio
        aspect_ratio = self._detect_aspect_ratio(t)

        # 8. Transitions
        transition = self._detect_transition(t)

        # 9. Music
        music_settings = self._detect_music(t)

        # 10. Highlights / energy
        extract_highlights = bool(re.search(r"\b(highlights?|best parts?|high energy|key moments?)\b", t))

        # Build actions list
        actions = []
        if remove_silence:
            actions.append({
                "action": "remove_silence",
                "enabled": True,
                "parameters": {
                    "top_db": 20,
                    "min_silence_duration_sec": 0.5
                }
            })
        if remove_shaky:
            actions.append({
                "action": "remove_shaky",
                "enabled": True,
                "parameters": {
                    "motion_threshold": 0.75,
                    "method": "optical_flow"
                }
            })
        if remove_blur:
            actions.append({
                "action": "remove_blur",
                "enabled": True,
                "parameters": {
                    "blur_threshold": 100.0,
                    "method": "laplacian_variance"
                }
            })
        if extract_highlights:
            actions.append({
                "action": "extract_highlights",
                "enabled": True,
                "parameters": {
                    "selection_ratio": 0.4
                }
            })
        if music_settings["add_background_music"]:
            actions.append({
                "action": "add_background_music",
                "enabled": True,
                "parameters": {
                    "genre": music_settings["music_genre"],
                    "ducking": True
                }
            })

        # Generate summary description
        summary = self._generate_summary(
            remove_silence, remove_shaky, remove_blur,
            target_duration, style, pacing, aspect_ratio
        )

        return {
            "raw_prompt": text,
            "engine": "semantic_nlp",
            "intent": "rough_cut_pipeline",
            "confidence": 0.96,
            "actions": actions,
            "filters": {
                "remove_silence": remove_silence,
                "remove_shaky": remove_shaky,
                "remove_blur": remove_blur,
                "keep_highlights_only": extract_highlights
            },
            "timeline_settings": {
                "target_duration_sec": target_duration,
                "style": style,
                "pacing": pacing,
                "aspect_ratio": aspect_ratio,
                "transition": transition
            },
            "audio_settings": music_settings,
            "summary": summary,
            # Backwards-compatible flat keys for existing consumers
            "style": style,
            "target_duration_sec": target_duration,
            "remove_silence": remove_silence,
            "remove_shaky": remove_shaky
        }

    # -------------------------------------------------------------------------
    # Intent Detection Helpers
    # -------------------------------------------------------------------------
    def _detect_silence_intent(self, text: str) -> bool:
        """Detect silence removal intention, handling negations."""
        if re.search(r"\b(don'?t|do not|never|skip)\s+(remove|cut|delete|filter)\s+silence\b", text):
            return False
        if re.search(r"\bkeep\s+(silence|silent|pauses)\b", text):
            return False

        patterns = [
            r"\b(remove|cut|delete|filter|strip|trim|drop|clear)\s+.*?\b(silence|silent|pauses?|dead air|quiet parts?)\b",
            r"\b(no\s+silence|without\s+silence|silence\s+removal)\b",
            r"\b(silent|silence)\s+clips?\b",
            r"\bsilence\b"
        ]
        return any(re.search(p, text) for p in patterns)

    def _detect_shaky_intent(self, text: str) -> bool:
        """Detect shaky footage removal/stabilization intention."""
        if re.search(r"\b(don'?t|do not|never)\s+(remove|cut|filter)\s+(shaky|shake)\b", text):
            return False
        if re.search(r"\bkeep\s+(shaky|handheld|camera shake)\b", text):
            return False

        patterns = [
            r"\b(remove|cut|delete|filter|drop|discard|exclude)\s+.*?\b(shak(?:y|e|ing)?|jitter(?:y)?|unstable|wobbl(?:y|e)|unsteady|those\s+portions|those\s+parts)\b",
            r"\b(split\s+and\s+(?:remove|delete|cut))\b",
            r"\b(actually\s+(?:split\s+and\s+)?(?:remove|delete|cut))\b",
            r"\b(shaky|unstable|jittery|wobbly|unsteady)\s+(clips?|footage|videos?|shots?|parts?|portions?)\b",
            r"\b(stabiliz(e|ation)|smooth out camera|no shake)\b",
            r"\bshaky\b"
        ]
        return any(re.search(p, text) for p in patterns)

    def _detect_blur_intent(self, text: str) -> bool:
        """Detect blurry footage removal intention."""
        if re.search(r"\b(don'?t|do not|never)\s+(remove|cut)\s+(blur|blurry)\b", text):
            return False

        patterns = [
            r"\b(remove|cut|delete|filter|drop)\s+.*?\b(blur|blurry|out[- ]of[- ]focus|unfocused)\b",
            r"\b(blurry|out[- ]of[- ]focus)\s+(clips?|footage|videos?|shots?)\b",
            r"\bblur\b"
        ]
        return any(re.search(p, text) for p in patterns)

    def _detect_duration(self, text: str) -> Optional[int]:
        """Detect target duration in seconds (e.g., '30 seconds', '1 minute', '45s')."""
        # Pattern: N minute(s)
        m = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:min(?:ute)?s?)\b", text)
        if m:
            return int(float(m.group(1)) * 60)

        # Pattern: N second(s) or Ns
        m = re.search(r"\b(\d+)\s*(?:s|sec(?:ond)?s?)\b", text)
        if m:
            return int(m.group(1))

        # Common phrases
        if "half minute" in text or "30 seconds" in text:
            return 30
        if "one minute" in text:
            return 60
        if "two minutes" in text:
            return 120

        return None

    def _detect_pacing(self, text: str) -> str:
        """Detect editing pacing."""
        if re.search(r"\b(fast[- ]paced?|quick cuts?|high energy|snappy|rapid|dynamic|jump cuts?)\b", text):
            return "fast"
        if re.search(r"\b(slow[- ]paced?|chill|relaxed|ambient|cinematic pace|gentle|smooth)\b", text):
            return "slow"
        return "normal"

    def _detect_style(self, text: str) -> str:
        """Detect overall editing style/genre."""
        styles = {
            "cinematic": [r"\bcinematic\b", r"\bmovie style\b", r"\bfilm look\b", r"\btrailer\b"],
            "vlog": [r"\bvlog\b", r"\btravel vlog\b", r"\bdaily vlog\b", r"\blifestyle\b"],
            "montage": [r"\bmontage\b", r"\bhighlight reel\b", r"\bhighlights?\b", r"\bcompilation\b"],
            "tutorial": [r"\btutorial\b", r"\bhow[- ]to\b", r"\bexplainer\b", r"\beducational\b"],
            "podcast": [r"\bpodcast\b", r"\btalk show\b", r"\binterview\b"],
            "promo": [r"\bpromo\b", r"\bcommercial\b", r"\bad\b", r"\bteaser\b"],
            "gaming": [r"\bgaming\b", r"\bgameplay\b", r"\bstream highlights?\b"]
        }
        for style_name, patterns in styles.items():
            if any(re.search(p, text) for p in patterns):
                return style_name
        return "default"

    def _detect_aspect_ratio(self, text: str) -> Optional[str]:
        """Detect aspect ratio (e.g. 9:16 vertical for TikTok, 16:9 for YouTube)."""
        if re.search(r"\b(9:16|vertical|portrait|tiktok|reels?|shorts?)\b", text):
            return "9:16"
        if re.search(r"\b(16:9|horizontal|landscape|widescreen|youtube)\b", text):
            return "16:9"
        if re.search(r"\b(1:1|square|instagram post)\b", text):
            return "1:1"
        return None

    def _detect_transition(self, text: str) -> Dict[str, Any]:
        """Detect requested transition type."""
        if re.search(r"\b(dissolve|cross[- ]fade|fade between)\b", text):
            return {"type": "dissolve", "duration_sec": 1.0}
        if re.search(r"\b(fade to black|black fade)\b", text):
            return {"type": "fade_black", "duration_sec": 0.8}
        if re.search(r"\b(wipe|slide)\b", text):
            return {"type": "wipe", "duration_sec": 0.6}
        return {"type": "cut", "duration_sec": 0.0}

    def _detect_music(self, text: str) -> Dict[str, Any]:
        """Detect background music requests and genres."""
        has_music = bool(re.search(r"\b(music|song|track|soundtrack|audio beat|bgm)\b", text))
        genre = None
        genres = ["upbeat", "lofi", "ambient", "rock", "cinematic", "electronic", "pop", "acoustic"]
        for g in genres:
            if g in text:
                genre = g
                has_music = True
                break
        return {
            "add_background_music": has_music,
            "music_genre": genre,
            "ducking": True
        }

    def _generate_summary(
        self,
        remove_silence: bool,
        remove_shaky: bool,
        remove_blur: bool,
        duration: Optional[int],
        style: str,
        pacing: str,
        aspect_ratio: Optional[str]
    ) -> str:
        """Generate a concise human-readable summary of the interpreted plan."""
        clauses = []
        if remove_silence:
            clauses.append("remove silent sections")
        if remove_shaky:
            clauses.append("filter out shaky clips")
        if remove_blur:
            clauses.append("remove blurry footage")
        if duration:
            clauses.append(f"target {duration}s duration")
        if style and style != "default":
            clauses.append(f"{style} style")
        if pacing and pacing != "normal":
            clauses.append(f"{pacing} pacing")
        if aspect_ratio:
            clauses.append(f"{aspect_ratio} aspect ratio")

        if not clauses:
            return "Assemble imported media using standard timeline settings."
        return "Plan: " + ", ".join(clauses).capitalize() + "."

    def _default_structure(self, raw_prompt: str, summary: str = "") -> Dict[str, Any]:
        """Returns baseline empty structure."""
        return {
            "raw_prompt": raw_prompt,
            "engine": "default",
            "intent": "rough_cut_pipeline",
            "confidence": 1.0,
            "actions": [],
            "filters": {
                "remove_silence": False,
                "remove_shaky": False,
                "remove_blur": False,
                "keep_highlights_only": False
            },
            "timeline_settings": {
                "target_duration_sec": None,
                "style": "default",
                "pacing": "normal",
                "aspect_ratio": None,
                "transition": {"type": "cut", "duration_sec": 0.0}
            },
            "audio_settings": {
                "add_background_music": False,
                "music_genre": None,
                "ducking": True
            },
            "summary": summary,
            "style": "default",
            "target_duration_sec": None,
            "remove_silence": False,
            "remove_shaky": False
        }

    # -------------------------------------------------------------------------
    # Optional Local SLM Querying
    # -------------------------------------------------------------------------
    def _try_slm_query(self, prompt_text: str) -> Optional[Dict[str, Any]]:
        """Attempt to query a local SLM via HTTP (e.g., Ollama or local endpoint)."""
        system_instruction = (
            "You are a video editing AI assistant for SmartEdit. "
            "Convert the user's natural language video editing prompt into a structured JSON object. "
            "Output ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "raw_prompt": string,\n'
            '  "intent": "rough_cut_pipeline",\n'
            '  "confidence": number,\n'
            '  "actions": [{"action": string, "enabled": boolean, "parameters": object}],\n'
            '  "filters": {"remove_silence": boolean, "remove_shaky": boolean, "remove_blur": boolean},\n'
            '  "timeline_settings": {"target_duration_sec": number|null, "style": string, "pacing": string, "aspect_ratio": string|null},\n'
            '  "summary": string\n'
            "}"
        )

        payload = {
            "model": self.model,
            "prompt": f"System: {system_instruction}\nUser Prompt: {prompt_text}\nJSON Response:",
            "stream": False,
            "format": "json"
        }

        try:
            req = urllib.request.Request(
                self.slm_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    raw_body = resp.read().decode("utf-8")
                    data = json.loads(raw_body)
                    response_text = data.get("response") or data.get("content", "")
                    parsed = json.loads(response_text)
                    parsed["engine"] = "local_slm"
                    parsed["model"] = self.model
                    # Populate compatibility flat fields
                    filters = parsed.get("filters", {})
                    parsed["remove_silence"] = filters.get("remove_silence", False)
                    parsed["remove_shaky"] = filters.get("remove_shaky", False)
                    parsed["style"] = parsed.get("timeline_settings", {}).get("style", "default")
                    parsed["target_duration_sec"] = parsed.get("timeline_settings", {}).get("target_duration_sec")
                    return parsed
        except Exception as e:
            logger.debug("Local SLM query failed, falling back to built-in semantic parser: %s", e)
        return None
