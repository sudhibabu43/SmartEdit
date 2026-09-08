"""
SmartEdit - SLM Prompt Interpretation Demo
==========================================

Demonstrates converting natural language video editing instructions into structured JSON.
Usage:
    python demo_slm_interpreter.py
    python demo_slm_interpreter.py "Remove silence and shaky clips."
    python demo_slm_interpreter.py "Create a 30s fast-paced cinematic highlight reel"
"""

import sys
import os

# Set up paths
_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(_DIR, "launch.py")):
    _SRC = _DIR
else:
    _SRC = os.path.join(_DIR, "SmartEdit", "smartedit-qt", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from smartedit.prompt_interpreter import PromptInterpreter


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Remove silence and shaky clips."

    interpreter = PromptInterpreter()
    print("=" * 60)
    print("  SmartEdit SLM Prompt Interpretation Demo")
    print("=" * 60)
    print(f"\nUser Input Prompt: \n  \"{prompt}\"\n")
    print("SLM Structured JSON Output:")
    print("-" * 60)
    json_output = interpreter.interpret_to_json(prompt, indent=2)
    print(json_output)
    print("-" * 60)


if __name__ == "__main__":
    main()
