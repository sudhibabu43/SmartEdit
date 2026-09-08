"""
 @file
 @brief Interactive Dialog for SLM Prompt Interpretation in SmartEdit.
 @author SmartEdit Team
"""

import json
from qt_api import (
    Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QComboBox, QFrame,
    QApplication, QFileDialog, QMessageBox
)

from smartedit.prompt_interpreter import PromptInterpreter
from classes.logger import log


class PromptInterpreterDialog(QDialog):
    """
    Dialog for interpreting natural language editing prompts into structured JSON.
    """

    def __init__(self, parent=None, initial_prompt="Remove silence and shaky clips."):
        super().__init__(parent)
        self.setWindowTitle("SmartEdit AI - SLM Prompt Interpreter")
        self.resize(780, 680)
        self.interpreter = PromptInterpreter()

        self._setup_ui(initial_prompt)
        # Perform initial interpretation if default prompt is provided
        if initial_prompt:
            self._on_interpret()

    def _setup_ui(self, initial_prompt: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2a3a, stop:1 #243b55);
                border: 1px solid #3a506b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title_lbl = QLabel("✨ SLM Video Prompt Interpretation")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #64b5f6; background: transparent;")
        desc_lbl = QLabel(
            "Converts natural language editing instructions into structured timeline actions and filter parameters."
        )
        desc_lbl.setStyleSheet("font-size: 12px; color: #cfd8dc; background: transparent;")
        desc_lbl.setWordWrap(True)
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(desc_lbl)
        layout.addWidget(header_frame)

        # Presets row
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Presets:"))
        presets = [
            ("⭐ Remove silence & shaky", "Remove silence and shaky clips."),
            ("30s Fast Reel", "Create a 30s fast-paced cinematic highlight reel with upbeat music"),
            ("TikTok 9:16 Vlog", "TikTok 9:16 vertical vlog: trim silence, remove blur and camera shake"),
            ("YouTube Tutorial", "YouTube widescreen tutorial: cut pauses and dead air")
        ]
        for btn_text, prompt_val in presets:
            btn = QPushButton(btn_text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c3e50;
                    color: #eceff1;
                    border: 1px solid #455a64;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #37474f;
                    border-color: #64b5f6;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda _, p=prompt_val: self._set_preset_prompt(p))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        # Prompt input area
        input_label = QLabel("Enter Natural Language Instruction:")
        input_label.setStyleSheet("font-weight: bold; color: #eceff1;")
        layout.addWidget(input_label)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("e.g. Remove silence and shaky clips.")
        self.prompt_input.setPlainText(initial_prompt)
        self.prompt_input.setMaximumHeight(85)
        self.prompt_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e272e;
                color: #ffffff;
                border: 1px solid #37474f;
                border-radius: 6px;
                font-size: 13px;
                padding: 8px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #64b5f6;
            }
        """)
        layout.addWidget(self.prompt_input)

        # Control Row (Engine selection + Action button)
        control_layout = QHBoxLayout()

        engine_lbl = QLabel("Engine:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Auto (SLM + Semantic NLP Fallback)", "auto")
        self.engine_combo.addItem("Built-in Semantic NLP Parser (Offline)", "nlp")
        self.engine_combo.addItem("Local SLM (Ollama: phi3 / qwen)", "slm")
        self.engine_combo.setStyleSheet("""
            QComboBox {
                background-color: #263238;
                color: #ffffff;
                border: 1px solid #455a64;
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 220px;
            }
        """)
        control_layout.addWidget(engine_lbl)
        control_layout.addWidget(self.engine_combo)
        control_layout.addStretch()

        self.interpret_btn = QPushButton("⚡ Interpret Prompt")
        self.interpret_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #2196f3;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
        """)
        self.interpret_btn.clicked.connect(self._on_interpret)
        control_layout.addWidget(self.interpret_btn)
        layout.addLayout(control_layout)

        # Summary & Badges panel
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #212121;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        summary_vbox = QVBoxLayout(self.summary_frame)
        summary_vbox.setContentsMargins(8, 6, 8, 6)

        self.summary_text_lbl = QLabel("Summary: -")
        self.summary_text_lbl.setStyleSheet("color: #81c784; font-weight: bold; font-size: 12px;")
        summary_vbox.addWidget(self.summary_text_lbl)

        self.badges_layout = QHBoxLayout()
        summary_vbox.addLayout(self.badges_layout)
        layout.addWidget(self.summary_frame)

        # Structured JSON Output viewer
        json_label = QLabel("Structured JSON Representation:")
        json_label.setStyleSheet("font-weight: bold; color: #eceff1;")
        layout.addWidget(json_label)

        self.json_viewer = QPlainTextEdit()
        self.json_viewer.setReadOnly(True)
        self.json_viewer.setStyleSheet("""
            QPlainTextEdit {
                background-color: #121212;
                color: #80cbc4;
                font-family: Consolas, "Courier New", monospace;
                font-size: 12px;
                border: 1px solid #37474f;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.json_viewer)

        # Bottom action buttons
        bottom_layout = QHBoxLayout()

        self.copy_btn = QPushButton("📋 Copy JSON")
        self.copy_btn.clicked.connect(self._on_copy_json)
        self.copy_btn.setStyleSheet("padding: 6px 14px; font-weight: bold;")
        bottom_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 Save JSON...")
        self.save_btn.clicked.connect(self._on_save_json)
        bottom_layout.addWidget(self.save_btn)

        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("padding: 6px 14px;")
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

    def _set_preset_prompt(self, prompt: str):
        self.prompt_input.setPlainText(prompt)
        self._on_interpret()

    def _on_interpret(self):
        text = self.prompt_input.toPlainText().strip()
        mode = self.engine_combo.currentData()
        self.interpreter.prefer_local_slm = (mode in ("auto", "slm"))

        try:
            parsed = self.interpreter.interpret_prompt(text)
            json_str = json.dumps(parsed, indent=2, ensure_ascii=False)
            self.json_viewer.setPlainText(json_str)

            # Update summary
            summary = parsed.get("summary", "")
            engine_used = parsed.get("engine", "semantic_nlp")
            self.summary_text_lbl.setText(f"{summary} (Engine: {engine_used})")

            # Update badges
            self._update_badges(parsed)
        except Exception as ex:
            log.error("Failed to interpret prompt: %s", ex, exc_info=True)
            self.json_viewer.setPlainText(f"Error interpreting prompt: {ex}")

    def _update_badges(self, parsed: dict):
        # Clear existing badges
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        filters = parsed.get("filters", {})
        timeline = parsed.get("timeline_settings", {})

        def make_badge(text, bg_color, fg_color="#ffffff"):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {fg_color};
                    font-weight: bold;
                    font-size: 11px;
                    border-radius: 4px;
                    padding: 3px 8px;
                }}
            """)
            return lbl

        if filters.get("remove_silence"):
            self.badges_layout.addWidget(make_badge("✓ Remove Silence", "#2e7d32"))
        if filters.get("remove_shaky"):
            self.badges_layout.addWidget(make_badge("✓ Remove Shaky", "#0277bd"))
        if filters.get("remove_blur"):
            self.badges_layout.addWidget(make_badge("✓ Remove Blur", "#e65100"))

        style = timeline.get("style")
        if style and style != "default":
            self.badges_layout.addWidget(make_badge(f"Style: {style}", "#6a1b9a"))

        duration = timeline.get("target_duration_sec")
        if duration:
            self.badges_layout.addWidget(make_badge(f"Duration: {duration}s", "#ad1457"))

        aspect = timeline.get("aspect_ratio")
        if aspect:
            self.badges_layout.addWidget(make_badge(f"Ratio: {aspect}", "#00695c"))

        self.badges_layout.addStretch()

    def _on_copy_json(self):
        text = self.json_viewer.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", "Structured JSON copied to clipboard!")

    def _on_save_json(self):
        text = self.json_viewer.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Structured JSON", "smartedit_prompt_instructions.json", "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "Saved", f"JSON successfully saved to:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "Error", f"Failed to save file: {ex}")
