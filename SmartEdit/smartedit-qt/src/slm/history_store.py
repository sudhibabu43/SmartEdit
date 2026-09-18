import os
import json
from datetime import datetime
from classes import info
from classes.logger import log

class PromptHistoryStore:
    def __init__(self, max_items=50):
        self.max_items = max_items
        self.history_file = os.path.join(info.USER_PATH, "slm_history.json")
        self.history = self.load()

    def load(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as ex:
            log.error(f"Error loading SLM prompt history: {ex}")
        return []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
        except Exception as ex:
            log.error(f"Error saving SLM prompt history: {ex}")

    def add_prompt(self, prompt: str):
        prompt = prompt.strip()
        if not prompt:
            return

        if self.history and self.history[0].get("prompt") == prompt:
            return

        entry = {
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        }

        self.history.insert(0, entry)
        
        if len(self.history) > self.max_items:
            self.history = self.history[:self.max_items]
            
        self.save()

    def get_history(self):
        return self.history

    def clear_history(self):
        self.history = []
        self.save()
