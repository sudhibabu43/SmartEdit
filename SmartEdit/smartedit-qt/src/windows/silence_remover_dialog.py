"""
 @file
 @brief Interactive GUI Dialog for Silence Detection & Removal in SmartEdit.
 @author SmartEdit Team
"""

import os
import json
from qt_api import (
    Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QComboBox, QFrame,
    QApplication, QFileDialog, QMessageBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QPainter, QBrush, QColor, QPen,
    QFont, QRectF
)

from smartedit.audio_analysis import AudioAnalyzer
from classes.logger import log


class TimelineSegmentBar(QWidget):
    """
    Custom-drawn segmented visual timeline displaying kept clips in green
    and silent cut sections in amber/red with split markers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.segments = []
        self.total_duration = 0.0

    def set_data(self, segments: list, total_duration: float):
        self.segments = segments
        self.total_duration = total_duration
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background track
        bg_rect = QRectF(10, 25, w - 20, 36)
        painter.setBrush(QColor("#1e272e"))
        painter.setPen(QPen(QColor("#37474f"), 1))
        painter.drawRoundedRect(bg_rect, 6, 6)

        if not self.segments or self.total_duration <= 0:
            painter.setPen(QColor("#78909c"))
            painter.drawText(bg_rect, Qt.AlignCenter, "No media analyzed yet — Click 'Detect Silence & Cut Points'")
            return

        track_x = 10.0
        track_w = float(w - 20)
        track_y = 25.0
        track_h = 36.0

        # Draw time tick labels
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#90a4ae"))
        num_ticks = min(8, max(4, int(self.total_duration)))
        for i in range(num_ticks + 1):
            t = (self.total_duration / num_ticks) * i
            tx = track_x + (t / self.total_duration) * track_w
            painter.drawText(int(tx) - 15, 16, 30, 12, Qt.AlignCenter, f"{t:.1f}s")
            painter.drawLine(int(tx), 18, int(tx), 23)

        # Draw each segment
        for seg in self.segments:
            s = seg["start"]
            e = seg["end"]
            seg_type = seg["type"]

            x1 = track_x + (s / self.total_duration) * track_w
            x2 = track_x + (e / self.total_duration) * track_w
            seg_w = max(2.0, x2 - x1)

            seg_rect = QRectF(x1, track_y, seg_w, track_h)

            if seg_type == "KEEP":
                # Vibrant emerald green for kept clips
                painter.setBrush(QColor("#2e7d32"))
                painter.setPen(QPen(QColor("#1b5e20"), 1))
                painter.drawRoundedRect(seg_rect, 4, 4)

                # Clip label if width permits
                if seg_w > 45:
                    painter.setPen(QColor("#ffffff"))
                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    clip_idx = seg.get("clip_index", 1)
                    painter.drawText(seg_rect, Qt.AlignCenter, f"Clip #{clip_idx}\n{seg['duration']:.1f}s")
            else:
                # Striped / darker red for silent sections
                painter.setBrush(QColor("#b71c1c"))
                painter.setPen(QPen(QColor("#e57373"), 1, Qt.DashLine))
                painter.drawRoundedRect(seg_rect, 4, 4)

                if seg_w > 40:
                    painter.setPen(QColor("#ffcdd2"))
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(seg_rect, Qt.AlignCenter, f"CUT\n-{seg['duration']:.1f}s")

            # Cut boundary indicator line
            painter.setPen(QPen(QColor("#ffeb3b"), 2))
            painter.drawLine(int(x1), int(track_y), int(x1), int(track_y + track_h))


class SilenceRemoverDialog(QDialog):
    """
    Dialog for detecting silent sections and calculating cut points using Librosa.
    """

    def __init__(self, parent=None, initial_media_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("SmartEdit AI - Silence Detection & Removal")
        self.resize(850, 720)
        self.analyzer = AudioAnalyzer()
        self.current_result = None

        self._setup_ui(initial_media_path)

        if initial_media_path and os.path.exists(initial_media_path):
            self._on_analyze()

    def _setup_ui(self, initial_media_path: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1b2838, stop:1 #2d3748);
                border: 1px solid #4a5568;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        header_vbox = QVBoxLayout(header_frame)
        header_vbox.setContentsMargins(12, 8, 12, 8)

        title_lbl = QLabel("✂ Audio Silence Detection & Automatic Cut Points")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #48bb78; background: transparent;")
        desc_lbl = QLabel(
            "Uses Librosa audio energy analysis to identify silent pauses, highlight active speech clips, "
            "and compute precise split timestamps for rough-cut editing."
        )
        desc_lbl.setStyleSheet("font-size: 12px; color: #e2e8f0; background: transparent;")
        desc_lbl.setWordWrap(True)
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(desc_lbl)
        layout.addWidget(header_frame)

        # File selection row
        file_box = QHBoxLayout()
        file_box.addWidget(QLabel("Media File:"))
        self.path_edit = QPlainTextEdit()
        self.path_edit.setMaximumHeight(34)
        self.path_edit.setPlaceholderText("Select or enter path to video (.mp4, .mov) or audio (.wav, .mp3)...")
        self.path_edit.setPlainText(initial_media_path)
        file_box.addWidget(self.path_edit)

        browse_btn = QPushButton("📁 Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_box.addWidget(browse_btn)

        sample_btn = QPushButton("⭐ Use Demo Audio")
        sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b6cb0;
                color: #ffffff;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
        """)
        sample_btn.clicked.connect(self._on_use_sample)
        file_box.addWidget(sample_btn)
        layout.addLayout(file_box)

        # Parameter controls
        param_frame = QFrame()
        param_frame.setStyleSheet("""
            QFrame {
                background-color: #212121;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        param_layout = QHBoxLayout(param_frame)

        # Threshold top_db
        param_layout.addWidget(QLabel("Threshold (dB):"))
        self.top_db_spin = QSpinBox()
        self.top_db_spin.setRange(10, 60)
        self.top_db_spin.setValue(25)
        self.top_db_spin.setToolTip("Volume below peak to treat as silence. Higher = more sensitive.")
        param_layout.addWidget(self.top_db_spin)

        # Min silence duration
        param_layout.addWidget(QLabel("Min Silence (s):"))
        self.min_sil_spin = QDoubleSpinBox()
        self.min_sil_spin.setRange(0.1, 5.0)
        self.min_sil_spin.setSingleStep(0.1)
        self.min_sil_spin.setValue(0.40)
        self.min_sil_spin.setToolTip("Ignore pauses shorter than this duration.")
        param_layout.addWidget(self.min_sil_spin)

        # Padding
        param_layout.addWidget(QLabel("Speech Margin (s):"))
        self.padding_spin = QDoubleSpinBox()
        self.padding_spin.setRange(0.0, 0.5)
        self.padding_spin.setSingleStep(0.02)
        self.padding_spin.setValue(0.08)
        self.padding_spin.setToolTip("Safety margin around speech boundaries.")
        param_layout.addWidget(self.padding_spin)

        param_layout.addStretch()

        self.analyze_btn = QPushButton("⚡ Detect Silence & Cut Points")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #38a169;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                border-radius: 5px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background-color: #48bb78;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze)
        param_layout.addWidget(self.analyze_btn)
        layout.addWidget(param_frame)

        # Visual Timeline Display
        timeline_label = QLabel("Visual Timeline Representation:")
        timeline_label.setStyleSheet("font-weight: bold; color: #eceff1;")
        layout.addWidget(timeline_label)

        self.timeline_widget = TimelineSegmentBar()
        layout.addWidget(self.timeline_widget)

        # Summary statistics badges
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("""
            QFrame {
                background-color: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 6px;
            }
        """)
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_orig = QLabel("Original: -")
        self.lbl_orig.setStyleSheet("font-weight: bold; color: #cbd5e0;")
        self.lbl_kept = QLabel("Kept Audio: -")
        self.lbl_kept.setStyleSheet("font-weight: bold; color: #68d391;")
        self.lbl_silent = QLabel("Silence Cut: -")
        self.lbl_silent.setStyleSheet("font-weight: bold; color: #fc8181;")
        self.lbl_saved = QLabel("Saved: -")
        self.lbl_saved.setStyleSheet("font-weight: bold; color: #f6e05e;")

        stats_layout.addWidget(self.lbl_orig)
        stats_layout.addWidget(self.lbl_kept)
        stats_layout.addWidget(self.lbl_silent)
        stats_layout.addWidget(self.lbl_saved)
        stats_layout.addStretch()
        layout.addWidget(self.stats_frame)

        # Cut Points & Clips Table
        table_label = QLabel("Timeline Clips & Split Points:")
        table_label.setStyleSheet("font-weight: bold; color: #eceff1;")
        layout.addWidget(table_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "#", "Segment Type", "Start Time", "End Time", "Duration", "Action / Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121212;
                color: #ffffff;
                border: 1px solid #333333;
                gridline-color: #2d3748;
            }
            QHeaderView::section {
                background-color: #212121;
                color: #e2e8f0;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #2d3748;
            }
        """)
        layout.addWidget(self.table)

        # Bottom buttons
        btn_box = QHBoxLayout()

        copy_btn = QPushButton("📋 Copy Cut Points (JSON)")
        copy_btn.clicked.connect(self._on_copy_json)
        btn_box.addWidget(copy_btn)

        save_btn = QPushButton("💾 Export Cut List...")
        save_btn.clicked.connect(self._on_export)
        btn_box.addWidget(save_btn)

        btn_box.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio or Video File",
            "",
            "Media Files (*.mp4 *.mov *.mkv *.avi *.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"
        )
        if path:
            self.path_edit.setPlainText(path)
            self._on_analyze()

    def _on_use_sample(self):
        sample_path = AudioAnalyzer.create_sample_audio()
        self.path_edit.setPlainText(sample_path)
        self._on_analyze()

    def _on_analyze(self):
        path = self.path_edit.toPlainText().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid File", "Please select a valid audio or video file.")
            return

        top_db = float(self.top_db_spin.value())
        min_sil = float(self.min_sil_spin.value())
        padding = float(self.padding_spin.value())

        try:
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText("Analyzing...")
            QApplication.processEvents()

            result = self.analyzer.generate_cut_points(
                path,
                top_db=top_db,
                min_silence_duration_sec=min_sil,
                padding_sec=padding
            )
            self.current_result = result

            # Update timeline bar
            self.timeline_widget.set_data(result["all_segments"], result["total_duration"])

            # Update stats
            stats = result["statistics"]
            self.lbl_orig.setText(f"Original: {stats['original_duration']:.2f}s")
            self.lbl_kept.setText(f"Kept ({stats['kept_clips_count']} clips): {stats['kept_duration']:.2f}s")
            self.lbl_silent.setText(f"Silence Cut: {stats['silent_duration']:.2f}s")
            self.lbl_saved.setText(f"Reduced: {stats['silence_percentage']:.1f}%")

            # Update table
            self._populate_table(result["all_segments"])
        except Exception as ex:
            log.error("Silence detection failed: %s", ex, exc_info=True)
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze audio: {ex}")
        finally:
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("⚡ Detect Silence & Cut Points")

    def _populate_table(self, segments: list):
        self.table.setRowCount(len(segments))

        for row, seg in enumerate(segments):
            is_keep = (seg["type"] == "KEEP")
            idx = seg.get("clip_index") if is_keep else seg.get("index", 1)

            item_num = QTableWidgetItem(str(idx))
            item_type = QTableWidgetItem("Clip" if is_keep else "Silence")
            item_start = QTableWidgetItem(f"{seg['start']:.2f}s")
            item_end = QTableWidgetItem(f"{seg['end']:.2f}s")
            item_dur = QTableWidgetItem(f"{seg['duration']:.2f}s")
            item_status = QTableWidgetItem("★ HIGHLIGHT & KEEP" if is_keep else "✂ CUT & REMOVE")

            # Colors
            if is_keep:
                color = QColor("#81c784")
            else:
                color = QColor("#e57373")

            for item in (item_num, item_type, item_start, item_end, item_dur, item_status):
                item.setForeground(color)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_type)
            self.table.setItem(row, 2, item_start)
            self.table.setItem(row, 3, item_end)
            self.table.setItem(row, 4, item_dur)
            self.table.setItem(row, 5, item_status)

    def _on_copy_json(self):
        if not self.current_result:
            QMessageBox.information(self, "Notice", "Please analyze a file first.")
            return
        json_str = json.dumps(self.current_result, indent=2)
        clipboard = QApplication.clipboard()
        clipboard.setText(json_str)
        QMessageBox.information(self, "Copied", "Cut points and clip data copied to clipboard as JSON!")

    def _on_export(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Cut Points", "smartedit_silence_cut_points.json", "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.current_result, f, indent=2)
                QMessageBox.information(self, "Saved", f"Cut points successfully saved to:\n{path}")
            except Exception as ex:
                QMessageBox.critical(self, "Error", f"Failed to save file: {ex}")
