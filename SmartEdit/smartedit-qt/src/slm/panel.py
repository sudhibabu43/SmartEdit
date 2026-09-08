"""
@file
@brief Integrated SLM Assistant Dock Panel for SmartEdit Video Editing.
@author SmartEdit Team
"""

import json
from typing import Optional
from qt_api import (
    Qt, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QFrame, QScrollArea,
    QProgressBar, QThread, pyqtSignal, pyqtSlot
)

from slm.prompt_parser import PromptParser
from slm.editing_controller import EditingController, AIPlan
from slm.command_schema import SLMCommand
from classes.logger import log


class SLMAnalysisWorker(QThread):
    """Background worker to analyze media and generate AI plan without UI freezing."""
    statusSignal = pyqtSignal(str)
    planReadySignal = pyqtSignal(object)
    failedSignal = pyqtSignal(str)

    def __init__(self, parser: PromptParser, controller: EditingController, prompt: str):
        super().__init__()
        self.parser = parser
        self.controller = controller
        self.prompt = prompt

    def run(self):
        try:
            self.statusSignal.emit("Interpreting prompt with Small Language Model...")
            command = self.parser.parse(self.prompt)
            
            self.statusSignal.emit("Analyzing audio silence & camera motion...")
            plan = self.controller.generate_plan(command)

            self.planReadySignal.emit(plan)
        except Exception as ex:
            log.error(f"SLM analysis failed: {ex}", exc_info=1)
            self.failedSignal.emit(str(ex))


class PromptInputTextEdit(QPlainTextEdit):
    """Specialized text editor ensuring keyboard focus and Enter-to-run behavior."""
    returnPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event):
        # Enter (without Shift) runs AI
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.returnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class SLMAssistantPanel(QDockWidget):
    """
    Native SmartEdit Dock Widget housing the SLM Assistant.
    Provides natural language prompt input, structured command preview,
    and human-in-the-loop plan review before applying timeline changes.
    """

    def __init__(self, parent=None):
        super().__init__("SLM Assistant", parent)
        self.setObjectName("dockSlmAssistant")
        self.setAllowedAreas(Qt.AllDockWidgetAreas)

        self.parser = PromptParser()
        self.controller = EditingController()
        self.current_plan: Optional[AIPlan] = None
        self.worker: Optional[SLMAnalysisWorker] = None

        self._setup_ui()

    def _setup_ui(self):
        # Wrap panel inside a QScrollArea so it fits all dock heights smoothly
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        main_container = QWidget()
        scroll.setWidget(main_container)
        self.setWidget(scroll)

        root_layout = QVBoxLayout(main_container)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Header Banner
        # -------------------------------------------------------------
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2536, stop:1 #111823);
                border: 1px solid #2a3d54;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(2)

        title_label = QLabel("🤖 SLM Video Editing Assistant")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4da6ff;")
        desc_label = QLabel("Describe editing changes in natural language. AI plans the edits for your review.")
        desc_label.setStyleSheet("font-size: 11px; color: #9ab4d0;")
        desc_label.setWordWrap(True)

        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        root_layout.addWidget(header_frame)

        # -------------------------------------------------------------
        # 2. Natural Language Input Area
        # -------------------------------------------------------------
        input_box_frame = QFrame()
        input_box_layout = QVBoxLayout(input_box_frame)
        input_box_layout.setContentsMargins(0, 0, 0, 0)
        input_box_layout.setSpacing(6)

        input_title = QLabel("Type Natural Language Instruction:")
        input_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e6e6e6;")
        input_box_layout.addWidget(input_title)

        self.prompt_input = PromptInputTextEdit()
        self.prompt_input.setPlaceholderText(
            "Type your instruction here (Press Enter to analyze)...\ne.g. 'Remove silence, arrange the clips, and label shaky footage'"
        )
        self.prompt_input.setFixedHeight(72)
        self.prompt_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #171e28;
                color: #ffffff;
                border: 2px solid #36485e;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                selection-background-color: #0084ff;
            }
            QPlainTextEdit:focus {
                border: 2px solid #0099ff;
                background-color: #1b2330;
            }
        """)
        self.prompt_input.returnPressed.connect(self.on_run_ai)
        input_box_layout.addWidget(self.prompt_input)

        # Quick Suggestion Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)

        chip_silence = QPushButton("⚡ Remove silence")
        chip_arrange = QPushButton("🎬 Arrange clips")
        chip_shaky = QPushButton("🔍 Find & label shaky")
        chip_all = QPushButton("🚀 Silence + Arrange + Shaky")

        for chip in (chip_silence, chip_arrange, chip_shaky, chip_all):
            chip.setStyleSheet("""
                QPushButton {
                    background-color: #212c3b;
                    color: #bcd5ef;
                    border: 1px solid #304257;
                    border-radius: 10px;
                    padding: 3px 8px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #2a3a4f;
                    color: #ffffff;
                    border-color: #4d94ff;
                }
            """)
            chips_layout.addWidget(chip)

        chip_silence.clicked.connect(lambda: self._set_prompt("Remove silence"))
        chip_arrange.clicked.connect(lambda: self._set_prompt("Arrange the clips in the best order"))
        chip_shaky.clicked.connect(lambda: self._set_prompt("Find shaky footage and label it"))
        chip_all.clicked.connect(lambda: self._set_prompt("Remove silence, arrange the clips, and label shaky footage"))

        chips_scroll = QScrollArea()
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setFixedHeight(34)
        chips_scroll.setFrameShape(QFrame.NoFrame)
        chips_container = QWidget()
        chips_container.setLayout(chips_layout)
        chips_scroll.setWidget(chips_container)
        input_box_layout.addWidget(chips_scroll)

        # Run AI Button
        self.btn_run_ai = QPushButton("⚡ Run AI / Analyze Plan")
        self.btn_run_ai.setFixedHeight(34)
        self.btn_run_ai.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066cc, stop:1 #0084ff);
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077ee, stop:1 #1a94ff);
            }
            QPushButton:disabled {
                background: #334455;
                color: #778899;
            }
        """)
        self.btn_run_ai.clicked.connect(self.on_run_ai)
        input_box_layout.addWidget(self.btn_run_ai)

        root_layout.addWidget(input_box_frame)

        # -------------------------------------------------------------
        # 3. Status Area
        # -------------------------------------------------------------
        self.status_bar_frame = QFrame()
        self.status_bar_frame.setStyleSheet("""
            QFrame {
                background-color: #1a222d;
                border: 1px solid #2a3747;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        status_layout = QHBoxLayout(self.status_bar_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #4da6ff; font-size: 14px;")
        self.status_label = QLabel("Ready. Type an instruction and click Run AI.")
        self.status_label.setStyleSheet("color: #b0c7de; font-size: 11px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #10161f;
                border: 1px solid #2a3747;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #0084ff;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()

        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.progress_bar)

        root_layout.addWidget(self.status_bar_frame)

        # -------------------------------------------------------------
        # 4. Human-in-the-Loop Result & Suggestion Area
        # -------------------------------------------------------------
        result_title = QLabel("Proposed AI Plan & Suggestions:")
        result_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e6e6e6;")
        root_layout.addWidget(result_title)

        # AI Plan Preview Box (Checklist)
        self.plan_preview = QLabel("No plan generated yet. Run AI to see proposed changes.")
        self.plan_preview.setStyleSheet("""
            QLabel {
                background-color: #151b24;
                color: #d1e2f2;
                border: 1px solid #283749;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        self.plan_preview.setWordWrap(True)
        self.plan_preview.setTextFormat(Qt.RichText)
        root_layout.addWidget(self.plan_preview)

        # Structured JSON Command Preview Box
        json_title = QLabel("Structured Editing Command (SLM Output – Read Only):")
        json_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #8899aa;")
        root_layout.addWidget(json_title)

        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setFixedHeight(75)
        self.json_preview.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1218;
                color: #55ff99;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                border: 1px solid #222d3b;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.json_preview.setPlainText('{\n  "actions": []\n}')
        root_layout.addWidget(self.json_preview)

        # -------------------------------------------------------------
        # 5. Action Control Buttons: [Apply Changes], [Reject], [Undo]
        # -------------------------------------------------------------
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setSpacing(8)

        self.btn_apply = QPushButton("✓ Apply Changes")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1b8a47, stop:1 #22aa58);
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #209f52, stop:1 #28c064);
            }
            QPushButton:disabled {
                background: #25332c;
                color: #587565;
            }
        """)
        self.btn_apply.clicked.connect(self.on_apply_changes)

        self.btn_reject = QPushButton("✕ Reject")
        self.btn_reject.setFixedHeight(34)
        self.btn_reject.setEnabled(False)
        self.btn_reject.setStyleSheet("""
            QPushButton {
                background-color: #382528;
                color: #ff8888;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #5a3338;
                border-radius: 5px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #4a2f33;
                color: #ffaaaa;
            }
            QPushButton:disabled {
                background: #281d1e;
                color: #553e40;
                border-color: #3a2628;
            }
        """)
        self.btn_reject.clicked.connect(self.on_reject_plan)

        self.btn_undo = QPushButton("↺ Undo")
        self.btn_undo.setFixedHeight(34)
        self.btn_undo.setStyleSheet("""
            QPushButton {
                background-color: #252e3d;
                color: #9bb5d1;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #36485e;
                border-radius: 5px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #2f3c4f;
                color: #c5dcf7;
            }
        """)
        self.btn_undo.clicked.connect(self.on_undo)

        btn_action_layout.addWidget(self.btn_apply, 2)
        btn_action_layout.addWidget(self.btn_reject, 1)
        btn_action_layout.addWidget(self.btn_undo, 1)

        root_layout.addLayout(btn_action_layout)

    def _set_prompt(self, text: str):
        from qt_api import QTextCursor
        self.prompt_input.setPlainText(text)
        self.prompt_input.setFocus()
        cursor = self.prompt_input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.prompt_input.setTextCursor(cursor)

    def on_run_ai(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self._update_status("Please enter an instruction first.", state="error")
            return

        self._update_status("Interpreting instruction and analyzing media...", state="busy")
        self.btn_run_ai.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_reject.setEnabled(False)
        self.progress_bar.show()

        # Run via background worker
        self.worker = SLMAnalysisWorker(self.parser, self.controller, prompt)
        self.worker.statusSignal.connect(lambda s: self._update_status(s, state="busy"))
        self.worker.planReadySignal.connect(self._on_plan_ready)
        self.worker.failedSignal.connect(self._on_analysis_failed)
        self.worker.start()

    @pyqtSlot(object)
    def _on_plan_ready(self, plan: AIPlan):
        self.current_plan = plan
        self.btn_run_ai.setEnabled(True)
        self.progress_bar.hide()

        # Update JSON Preview
        self.json_preview.setPlainText(plan.command.to_json(indent=2))

        # Update Human-in-the-Loop Plan Preview
        self.plan_preview.setText(plan.to_preview_text())

        if not plan.is_empty and len(plan.items) > 0:
            self.btn_apply.setEnabled(True)
            self.btn_reject.setEnabled(True)
            self._update_status("AI Plan generated. Review proposed changes and click Apply.", state="success")
        else:
            self.btn_apply.setEnabled(False)
            self.btn_reject.setEnabled(False)
            self._update_status("AI analyzed prompt: No matching timeline operations required.", state="info")

    @pyqtSlot(str)
    def _on_analysis_failed(self, error_msg: str):
        self.btn_run_ai.setEnabled(True)
        self.progress_bar.hide()
        self._update_status(f"Error: {error_msg}", state="error")

    def on_apply_changes(self):
        if not self.current_plan:
            return

        self._update_status("Applying changes to timeline...", state="busy")
        result = self.controller.apply_plan(self.current_plan)

        if result.get("success"):
            self.btn_apply.setEnabled(False)
            self.btn_reject.setEnabled(False)
            msg = result.get("message", "Changes applied successfully.")
            self._update_status(f"✓ {msg}", state="success")
            self.plan_preview.setText(
                f"<span style='color:#55ff99;'><b>✓ Changes Applied to Timeline:</b></span><br/>"
                f"{self.current_plan.to_preview_text()}<br/>"
                f"<i>(You can manually edit clips or click [Undo] to revert)</i>"
            )
        else:
            self._update_status(f"Failed to apply changes: {result.get('message')}", state="error")

    def on_reject_plan(self):
        self.current_plan = None
        self.btn_apply.setEnabled(False)
        self.btn_reject.setEnabled(False)
        self.plan_preview.setText("Proposed plan rejected. Timeline was not modified.")
        self.json_preview.setPlainText('{\n  "actions": []\n}')
        self._update_status("Plan rejected. Ready for a new instruction.", state="info")

    def on_undo(self):
        success = self.controller.undo_last_ai_operation()
        if success:
            self._update_status("↺ Reverted last AI timeline operation.", state="info")
            self.plan_preview.setText("Last operation was undone. Timeline restored.")
        else:
            self._update_status("Nothing to undo.", state="info")

    def _update_status(self, text: str, state: str = "info"):
        self.status_label.setText(text)
        if state == "busy":
            self.status_icon.setText("⏳")
            self.status_icon.setStyleSheet("color: #ffcc00; font-size: 13px;")
        elif state == "success":
            self.status_icon.setText("●")
            self.status_icon.setStyleSheet("color: #2ecc71; font-size: 14px;")
        elif state == "error":
            self.status_icon.setText("✕")
            self.status_icon.setStyleSheet("color: #e74c3c; font-size: 13px;")
        else:
            self.status_icon.setText("●")
            self.status_icon.setStyleSheet("color: #4da6ff; font-size: 14px;")
