"""
@file
@brief Small Language Model (SLM) & Semantic Prompt Parser for SmartEdit.
@author SmartEdit Team
"""

import re
import json
import logging
from typing import Dict, Any, Optional

from slm.command_schema import ActionType, SLMCommand, CommandSchemaValidator

logger = logging.getLogger(__name__)


class PromptParser:
    """
    Parses natural language instructions into structured editing commands.
    Supports local SLM inference (Ollama / OpenAI API) with deterministic semantic NLP fallback.
    """

    def __init__(
        self,
        slm_url: Optional[str] = "http://localhost:11434/api/generate",
        model: str = "phi3:mini",
        prefer_local_slm: bool = False,
        timeout: float = 2.0
    ):
        self.slm_url = slm_url
        self.model = model
        self.prefer_local_slm = prefer_local_slm
        self.timeout = timeout

    def parse(self, prompt: str) -> SLMCommand:
        """
        Parses a natural language user prompt into an SLMCommand.
        """
        if not prompt or not prompt.strip():
            return SLMCommand(raw_prompt=prompt)

        clean_prompt = prompt.strip()

        # Attempt local SLM if configured and preferred
        if self.prefer_local_slm and self.slm_url:
            slm_response = self._query_slm(clean_prompt)
            if slm_response:
                return CommandSchemaValidator.validate_and_normalize(slm_response, raw_prompt=clean_prompt)

        # Built-in deterministic semantic NLP engine
        raw_dict = self._parse_semantic_nlp(clean_prompt)
        return CommandSchemaValidator.validate_and_normalize(raw_dict, raw_prompt=clean_prompt)

    def _parse_semantic_nlp(self, text: str) -> Dict[str, Any]:
        """
        High-precision regex and semantic rule parser that converts user prompts into structured actions.
        """
        t = text.lower()
        actions = []
        parameters: Dict[str, Any] = {}

        # 1. Silence removal intent
        # "Remove silence", "cut silence", "delete silence", "trim quiet parts"
        if re.search(r"\b(remove|cut|delete|drop|trim|filter|strip|clean)\s+(out\s+)?(all\s+)?(the\s+)?(silence|silent|quiet|dead\s*air)\b", t) or \
           re.search(r"\b(silence\s*(removal|cutting|detector))\b", t) or \
           re.search(r"\b(no\s+silence)\b", t):
            actions.append(ActionType.REMOVE_SILENCE)
            parameters["silence"] = {
                "top_db": 20,
                "min_silence_duration_sec": 0.5
            }

        # 2. Clip arrangement intent
        # "Arrange the clips in the best order", "arrange clips", "order clips", "sequence clips", "reorder clips"
        if re.search(r"\b(arrange|order|reorder|sort|sequence|organize|align)\s+(the\s+)?(clips?|timeline|footage|scenes?|videos?)\b", t) or \
           re.search(r"\b(in\s+(the\s+)?best\s+order)\b", t) or \
           re.search(r"\b(chronological\s+order)\b", t):
            actions.append(ActionType.ARRANGE_CLIPS)
            parameters["arrange"] = {
                "order_by": "chronological",
                "align_track": 1000000
            }

        # 3. Camera shake detection intent
        # "Find shaky footage", "detect shaky", "identify shaky footage", "spot shaky clips", "check for shake"
        detect_shaky = bool(
            re.search(r"\b(find|detect|identify|spot|search|look\s+for|check\s+for|analyze)\s+(any\s+)?(the\s+)?(shaky|jittery|unstable|wobbly)\s*(footage|clips?|videos?|shots?|scenes?)?\b", t) or \
            re.search(r"\b(shaky\s*(footage|clips?|detection|analysis))\b", t)
        )

        # 4. Camera shake labeling intent
        # "label it", "label shaky", "mark shaky", "tag shaky footage", "highlight shaky"
        label_shaky = bool(
            re.search(r"\b(label|mark|tag|flag|highlight|indicate)\s+(it|them|the\s+shaky|shaky\s+footage|shaky\s+clips?)\b", t) or \
            re.search(r"\b(label\s+shaky)\b", t) or \
            re.search(r"\b(add\s+(a\s+)?label)\b", t)
        )

        # 5. Delete shaky (explicit only!)
        # "delete shaky footage", "remove shaky clips"
        delete_shaky = bool(
            re.search(r"\b(delete|remove|drop|cut)\s+(the\s+)?(shaky|jittery|unstable)\b", t)
        )

        if delete_shaky:
            actions.append(ActionType.DELETE_SHAKY)
            detect_shaky = True
        elif label_shaky:
            actions.append(ActionType.DETECT_SHAKY)
            actions.append(ActionType.LABEL_SHAKY)
        elif detect_shaky:
            actions.append(ActionType.DETECT_SHAKY)

        if detect_shaky or label_shaky or delete_shaky:
            parameters["shaky"] = {
                "motion_threshold": 0.70,
                "label_text": "SHAKY FOOTAGE",
                "add_marker": True
            }

        # 6. Rough cut intent
        # "Create a rough cut", "make a rough cut", "build rough cut"
        if re.search(r"\b(create|make|build|generate|produce)\s+(a\s+)?(rough\s*cut)\b", t) or \
           re.search(r"\b(rough\s*cut)\b", t):
            if ActionType.ROUGH_CUT not in actions:
                actions.append(ActionType.ROUGH_CUT)
            if ActionType.REMOVE_SILENCE not in actions:
                actions.append(ActionType.REMOVE_SILENCE)
            if ActionType.ARRANGE_CLIPS not in actions:
                actions.append(ActionType.ARRANGE_CLIPS)
            parameters["rough_cut"] = {
                "pacing": "standard",
                "remove_dead_space": True
            }

        return {
            "actions": actions,
            "parameters": parameters
        }

    def _query_slm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Queries local SLM (Ollama or OpenAI-compatible) endpoint."""
        import urllib.request
        import urllib.error

        system_instruction = (
            "You are an AI video editing assistant for SmartEdit. "
            "Convert user natural language instructions into a JSON object with 'actions'. "
            "Supported actions: 'remove_silence', 'arrange_clips', 'detect_shaky', 'label_shaky', 'rough_cut'. "
            "Example: User: 'Remove silence and identify shaky footage.' -> {\"actions\": [\"remove_silence\", \"detect_shaky\"]} "
            "Only return valid JSON."
        )

        try:
            payload = {
                "model": self.model,
                "prompt": f"{system_instruction}\nUser: {prompt}\nJSON:",
                "stream": False,
                "format": "json"
            }
            req = urllib.request.Request(
                self.slm_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response") or data.get("content", "")
                return json.loads(response_text)
        except Exception as e:
            logger.debug(f"Local SLM query failed (fallback to NLP): {e}")
            return None
