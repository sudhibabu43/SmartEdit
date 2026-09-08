"""
@file
@brief Small Language Model (SLM) Assistant package for SmartEdit.
@author SmartEdit Team
"""

from slm.command_schema import ActionType, SLMCommand, CommandSchemaValidator
from slm.prompt_parser import PromptParser
from slm.video_analyzer import VideoAnalyzer, classify_shake
from slm.shaky_detector import ShakyFootageService
from slm.editing_controller import EditingController, AIPlan, PlanItem
from slm.panel import SLMAssistantPanel

__all__ = [
    "ActionType",
    "SLMCommand",
    "CommandSchemaValidator",
    "PromptParser",
    "VideoAnalyzer",
    "classify_shake",
    "ShakyFootageService",
    "EditingController",
    "AIPlan",
    "PlanItem",
    "SLMAssistantPanel"
]


