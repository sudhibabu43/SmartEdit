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
    QProgressBar, QThread, pyqtSignal, pyqtSlot, QSizePolicy, QEvent
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
        if self.viewport():
            self.viewport().setFocusPolicy(Qt.StrongFocus)
            self.viewport().setCursor(Qt.IBeamCursor)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setTabChangesFocus(True)

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        super().mouseReleaseEvent(event)

    def viewportEvent(self, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            self.setFocus(Qt.MouseFocusReason)
        return super().viewportEvent(event)

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
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        main_container = QWidget()
        scroll.setWidget(main_container)
        self.setWidget(scroll)

        # Consistent panel padding (14px on all sides, standard 12-16px range)
        root_layout = QVBoxLayout(main_container)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Header Banner
        # -------------------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("slmHeaderFrame")
        header_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        header_frame.setStyleSheet("""
            QFrame#slmHeaderFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a2536, stop:1 #111823);
                border: 1px solid #2a3d54;
                border-radius: 6px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(3)

        # Section Header: slightly larger/bold as requested
        title_label = QLabel("🤖 SLM Video Editing Assistant")
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4da6ff;")
        # Body text: regular weight
        desc_label = QLabel("Describe editing changes in natural language. AI plans the edits for your review.")
        desc_label.setStyleSheet("font-size: 11px; font-weight: normal; color: #9ab4d0;")
        desc_label.setWordWrap(True)

        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        root_layout.addWidget(header_frame)

        # -------------------------------------------------------------
        # 2. Natural Language Input Area
        # -------------------------------------------------------------
        input_box_frame = QFrame()
        input_box_frame.setObjectName("slmInputFrame")
        input_box_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        input_box_layout = QVBoxLayout(input_box_frame)
        input_box_layout.setContentsMargins(0, 0, 0, 0)
        input_box_layout.setSpacing(6)

        # Label: regular weight as requested ("regular weight for body text and labels")
        input_title = QLabel("Type Natural Language Instruction:")
        input_title.setStyleSheet("font-size: 11px; font-weight: normal; color: #b8c7d6;")
        input_box_layout.addWidget(input_title)

        # Text input box: sits close (6px) to label, 6px rounded border, clear focus state
        self.prompt_input = PromptInputTextEdit()
        self.prompt_input.setPlaceholderText(
            "Type your instruction here (Press Enter to analyze)...\ne.g. 'Remove silence, arrange the clips, and label shaky footage'"
        )
        self.prompt_input.setFixedHeight(68)
        self.prompt_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #151b24;
                color: #ffffff;
                border: 1px solid #2d3e52;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                selection-background-color: #0084ff;
            }
            QPlainTextEdit:focus {
                border: 1.5px solid #0099ff;
                background-color: #192230;
            }
        """)
        self.prompt_input.returnPressed.connect(self.on_run_ai)
        input_box_layout.addWidget(self.prompt_input)

        # Spacing before suggestion chips: 6px
        input_box_layout.addSpacing(2)

        # Quick Suggestion Chips (even spacing, consistent 26px height, no stretch or misalignment)
        chips_scroll = QScrollArea()
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setFixedHeight(28)
        chips_scroll.setFrameShape(QFrame.NoFrame)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chips_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        chips_container = QWidget()
        chips_container.setStyleSheet("background: transparent;")
        chips_layout = QHBoxLayout(chips_container)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)

        chip_silence = QPushButton("⚡ Remove silence")
        chip_arrange = QPushButton("🎬 Arrange clips")
        chip_shaky = QPushButton("🔍 Find & label shaky")
        chip_all = QPushButton("🚀 Silence + Arrange + Shaky")

        chip_style = """
            QPushButton {
                background-color: #1f2a38;
                color: #b0c9e2;
                border: 1px solid #2d3e52;
                border-radius: 13px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #2a3a4f;
                color: #ffffff;
                border-color: #4d94ff;
            }
            QPushButton:pressed {
                background-color: #182230;
            }
        """

        for chip in (chip_silence, chip_arrange, chip_shaky, chip_all):
            chip.setFixedHeight(26)
            chip.setStyleSheet(chip_style)
            chips_layout.addWidget(chip)

        chips_layout.addStretch(1)

        chip_silence.clicked.connect(lambda: self._set_prompt("Remove silence"))
        chip_arrange.clicked.connect(lambda: self._set_prompt("Arrange the clips in the best order"))
        chip_shaky.clicked.connect(lambda: self._set_prompt("Find shaky footage and label it"))
        chip_all.clicked.connect(lambda: self._set_prompt("Remove silence, arrange the clips, and label shaky footage"))

        chips_scroll.setWidget(chips_container)
        input_box_layout.addWidget(chips_scroll)

        # Spacing before Run button: 6px
        input_box_layout.addSpacing(2)

        # Run AI Button (consistent height 34px, modern primary action)
        self.btn_run_ai = QPushButton("⚡ Run AI / Analyze Plan")
        self.btn_run_ai.setFixedHeight(34)
        self.btn_run_ai.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0066cc, stop:1 #0084ff);
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077ee, stop:1 #1a94ff);
            }
            QPushButton:pressed {
                background: #0055aa;
            }
            QPushButton:disabled {
                background: #233140;
                color: #5c7086;
                border: 1px solid #1c2733;
            }
        """)
        self.btn_run_ai.clicked.connect(self.on_run_ai)
        input_box_layout.addWidget(self.btn_run_ai)

        root_layout.addWidget(input_box_frame)

        # -------------------------------------------------------------
        # 3. Status Area
        # -------------------------------------------------------------
        self.status_bar_frame = QFrame()
        self.status_bar_frame.setObjectName("slmStatusFrame")
        self.status_bar_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.status_bar_frame.setStyleSheet("""
            QFrame#slmStatusFrame {
                background-color: #141c26;
                border: 1px solid #233142;
                border-radius: 6px;
            }
        """)
        status_layout = QHBoxLayout(self.status_bar_frame)
        status_layout.setContentsMargins(10, 6, 10, 6)
        status_layout.setSpacing(8)

        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #4da6ff; font-size: 14px;")
        self.status_label = QLabel("Ready. Type an instruction and click Run AI.")
        self.status_label.setStyleSheet("color: #b0c7de; font-size: 11px; font-weight: normal;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0d131a;
                border: 1px solid #233142;
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
        result_group_frame = QFrame()
        result_group_frame.setObjectName("slmResultFrame")
        result_group_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        result_group_layout = QVBoxLayout(result_group_frame)
        result_group_layout.setContentsMargins(0, 0, 0, 0)
        result_group_layout.setSpacing(6)

        # Section Header: slightly larger/bold as requested
        result_title = QLabel("Proposed AI Plan & Suggestions:")
        result_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e1e9f2;")
        result_group_layout.addWidget(result_title)

        # AI Plan Preview Box (Checklist)
        self.plan_preview = QLabel("No plan generated yet. Run AI to see proposed changes.")
        self.plan_preview.setStyleSheet("""
            QLabel {
                background-color: #141c26;
                color: #c9daf0;
                border: 1px solid #233142;
                border-radius: 6px;
                padding: 10px;
                font-size: 11px;
                font-weight: normal;
            }
        """)
        self.plan_preview.setWordWrap(True)
        self.plan_preview.setTextFormat(Qt.RichText)
        result_group_layout.addWidget(self.plan_preview)

        # Spacing before JSON preview: 8px
        result_group_layout.addSpacing(4)

        # Structured JSON Command Preview Box (regular weight for label)
        json_title = QLabel("Structured Editing Command (SLM Output – Read Only):")
        json_title.setStyleSheet("font-size: 11px; font-weight: normal; color: #7f93a6;")
        result_group_layout.addWidget(json_title)

        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setFixedHeight(72)
        self.json_preview.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0b1016;
                color: #55ff99;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                border: 1px solid #1f2b3a;
                border-radius: 6px;
                padding: 6px 8px;
            }
        """)
        self.json_preview.setPlainText('{\n  "actions": []\n}')
        result_group_layout.addWidget(self.json_preview)

        root_layout.addWidget(result_group_frame)

        # -------------------------------------------------------------
        # 5. Action Control Buttons: [Apply Changes], [Reject], [Undo]
        # -------------------------------------------------------------
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setContentsMargins(0, 0, 0, 0)
        btn_action_layout.setSpacing(8)

        self.btn_apply = QPushButton("✓ Apply Changes")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a8745, stop:1 #22aa58);
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f9c50, stop:1 #28c064);
            }
            QPushButton:pressed {
                background: #157339;
            }
            QPushButton:disabled {
                background: #1c2721;
                color: #4a6353;
                border: 1px solid #23332a;
            }
        """)
        self.btn_apply.clicked.connect(self.on_apply_changes)

        self.btn_reject = QPushButton("✕ Reject")
        self.btn_reject.setFixedHeight(34)
        self.btn_reject.setEnabled(False)
        self.btn_reject.setStyleSheet("""
            QPushButton {
                background-color: #351f23;
                color: #ff8888;
                font-weight: 500;
                font-size: 12px;
                border: 1px solid #5a2e33;
                border-radius: 6px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #44262b;
                color: #ffa0a0;
                border-color: #733b41;
            }
            QPushButton:pressed {
                background-color: #2c191c;
            }
            QPushButton:disabled {
                background: #201719;
                color: #553e41;
                border-color: #2d1f22;
            }
        """)
        self.btn_reject.clicked.connect(self.on_reject_plan)

        self.btn_undo = QPushButton("↺ Undo")
        self.btn_undo.setFixedHeight(34)
        self.btn_undo.setStyleSheet("""
            QPushButton {
                background-color: #212936;
                color: #9bb5d1;
                font-weight: 500;
                font-size: 12px;
                border: 1px solid #314054;
                border-radius: 6px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #2a3545;
                color: #c5dcf7;
                border-color: #3e526d;
            }
            QPushButton:pressed {
                background-color: #1b222d;
            }
            QPushButton:disabled {
                background: #191f28;
                color: #4e5e70;
                border-color: #242c38;
            }
        """)
        self.btn_undo.clicked.connect(self.on_undo)

        btn_action_layout.addWidget(self.btn_apply, 2)
        btn_action_layout.addWidget(self.btn_reject, 1)
        btn_action_layout.addWidget(self.btn_undo, 1)

        root_layout.addLayout(btn_action_layout)

        # Add expanding stretch at bottom so content is packed tightly without stretching widgets
        root_layout.addStretch(1)

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
            self.prompt_input.setEnabled(True)
            self.prompt_input.setReadOnly(False)
            return

        self._update_status("Interpreting instruction and analyzing media...", state="busy")
        self.btn_run_ai.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_reject.setEnabled(False)
        self.progress_bar.show()

        try:
            # Run via background worker
            self.worker = SLMAnalysisWorker(self.parser, self.controller, prompt)
            self.worker.statusSignal.connect(lambda s: self._update_status(s, state="busy"))
            self.worker.planReadySignal.connect(self._on_plan_ready)
            self.worker.failedSignal.connect(self._on_analysis_failed)
            self.worker.start()
        except Exception as ex:
            log.error(f"Failed to start SLMAnalysisWorker: {ex}", exc_info=1)
            self.btn_run_ai.setEnabled(True)
            self.prompt_input.setEnabled(True)
            self.prompt_input.setReadOnly(False)
            self.progress_bar.hide()
            self._update_status(f"Error starting analysis: {ex}", state="error")

    @pyqtSlot(object)
    def _on_plan_ready(self, plan: AIPlan):
        self.current_plan = plan
        self.btn_run_ai.setEnabled(True)
        self.prompt_input.setEnabled(True)
        self.prompt_input.setReadOnly(False)
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
        self.prompt_input.setEnabled(True)
        self.prompt_input.setReadOnly(False)
        self.progress_bar.hide()
        self._update_status(f"Error: {error_msg}", state="error")

    def on_apply_changes(self):
        if not self.current_plan:
            return

        self._update_status("Applying changes to timeline...", state="busy")
        result = self.controller.apply_plan(self.current_plan)

        self.prompt_input.setEnabled(True)
        self.prompt_input.setReadOnly(False)

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
        self.prompt_input.setEnabled(True)
        self.prompt_input.setReadOnly(False)
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
