import uuid
import logging
from typing import List, Dict, Any, Optional

from slm.command_schema import SLMCommand, ActionType
from slm.prompt_parser import PromptParser
from slm.editing_controller import EditingController, AIPlan

logger = logging.getLogger(__name__)

class ChatController:
    def __init__(self, parser: PromptParser, editor: EditingController):
        self.parser = parser
        self.editor = editor
        self.conversation: List[Dict[str, Any]] = []
        self.editing_state: Dict[str, Any] = {}
        self.pending_plan: Optional[AIPlan] = None

    def process_message(self, text: str) -> Dict[str, Any]:
        """
        Takes user input, parses it with context, executes business logic, 
        and returns a dict representing the AI's response message.
        """
        # Append user message to conversation history
        user_msg = {"role": "user", "text": text}
        self.conversation.append(user_msg)

        # Parse command
        command = self.parser.parse(text)
        
        # Check for conversational commands (Apply, Reject, Undo)
        if command.has_action(ActionType.APPLY_PLAN):
            if self.pending_plan:
                result = self.editor.apply_plan(self.pending_plan)
                self.pending_plan = None
                msg = "Changes applied successfully." if result.get("success") else f"Failed to apply: {result.get('message')}"
                return self._create_ai_response(msg)
            else:
                return self._create_ai_response("There are no pending changes to apply.")
                
        if command.has_action(ActionType.REJECT_PLAN):
            if self.pending_plan:
                self.pending_plan = None
                return self._create_ai_response("Okay, I've discarded the proposed changes.")
            else:
                return self._create_ai_response("There are no pending changes to discard.")

        if command.has_action(ActionType.UNDO):
            success = self.editor.undo_last_ai_operation()
            if success:
                return self._create_ai_response("Last AI operation undone successfully.")
            else:
                return self._create_ai_response("Nothing to undo.")

        # Otherwise, it's an editing request. Generate a new plan.
        plan = self.editor.generate_plan(command)
        
        if not plan.operations and not plan.items:
            return self._create_ai_response("I couldn't find any edits to make based on your request.")
            
        # Update pending plan
        self.pending_plan = plan
        
        # Format a nice chat response based on the plan items
        response_text = plan.to_preview_text()
        return self._create_ai_response(response_text, plan=plan)
        
    def _create_ai_response(self, text: str, plan: Optional[AIPlan] = None) -> Dict[str, Any]:
        msg = {
            "role": "ai",
            "text": text,
            "plan": plan
        }
        self.conversation.append(msg)
        return msg
