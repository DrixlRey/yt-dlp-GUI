"""
Controls panel for YouTube Downloader GUI.

This module provides the main controls interface including URL input,
download options, progress tracking, and download management.
"""

import sys
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
        QComboBox, QProgressBar, QGroupBox, QFileDialog, QTextEdit,
        QListWidget, QListWidgetItem, QTabWidget, QCheckBox, QSpinBox,
        QFrame, QSizePolicy, QScrollArea, QMessageBox, QSplitter
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QSettings
    from PyQt6.QtGui import QFont, QClipboard, QValidator, QIntValidator
except ImportError as e:
    print(f"PyQt6 not available: {e}")
    print("Run setup.py to install dependencies.")
    sys.exit(1)

from ..downloader.validation import (
    DownloadRequest, ProgressInfo, VideoInfo, DownloadType, 
    QualityOption, VideoFormat, AudioFormat, ProgressStatus
)

import logging
logger = logging.getLogger(__name__)


class URLValidator(QValidator):
    """Custom validator for YouTube URLs."""
    
    def validate(self, input_text: str, pos: int):
        """Validate YouTube URL format."""
        if not input_text:
            return QValidator.State.Intermediate, input_text, pos
        
        youtube_patterns = [
            'youtube.com/watch',
            'youtu.be/',
            'youtube.com/playlist',
            'youtube.com/shorts/',
            'm.youtube.com/watch'
        ]
        
        if any(pattern in input_text.lower() for pattern in youtube_patterns):
            return QValidator.State.Acceptable, input_text, pos
        elif any(input_text.lower().startswith(pattern.split('/')[0]) for pattern in youtube_patterns):
            return QValidator.State.Intermediate, input_text, pos
        else:
            return QValidator.State.Invalid, input_text, pos


class ProgressWidget(QWidget):
    """Widget for displaying individual download progress."""
    
    # Signals
    cancel_requested = pyqtSignal(str)  # request_id
    retry_requested = pyqtSignal(str)  # request_id
    
    def __init__(self, request_id: str, url: str, title: str = ""):
        """
        Initialize progress widget.
        
        Args:
            request_id: Unique download request ID
            url: Download URL
            title: Video title (if available)
        """
        super().__init__()
        
        self.request_id = request_id
        self.url = url
        self.title = title or "Unknown Video"
        self.progress_info = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # Title and URL
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Pending")
        self.status_label.setStyleSheet("color: #666666; font-size: 10px;")
        title_layout.addWidget(self.status_label)
        
        layout.addLayout(title_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Details layout
        details_layout = QHBoxLayout()
        
        # Speed and ETA
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("color: #666666; font-size: 9px;")
        details_layout.addWidget(self.speed_label)
        
        details_layout.addStretch()
        
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #666666; font-size: 9px;")
        details_layout.addWidget(self.eta_label)
        
        # Size info
        self.size_label = QLabel("Size: --")
        self.size_label.setStyleSheet("color: #666666; font-size: 9px;")
        details_layout.addWidget(self.size_label)
        
        layout.addLayout(details_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMaximumWidth(60)
        self.cancel_button.clicked.connect(lambda: self.cancel_requested.emit(self.request_id))
        button_layout.addWidget(self.cancel_button)
        
        self.retry_button = QPushButton("Retry")
        self.retry_button.setMaximumWidth(60)
        self.retry_button.setVisible(False)
        self.retry_button.clicked.connect(lambda: self.retry_requested.emit(self.request_id))
        button_layout.addWidget(self.retry_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Set styling
        self.setStyleSheet("""
            ProgressWidget {
                border: 1px solid #cccccc;
                border-radius: 6px;
                background-color: #fafafa;
                margin: 2px;
            }
        """)
        
        self.setMaximumHeight(100)
    
    def update_progress(self, progress: ProgressInfo):
        """
        Update progress display.
        
        Args:
            progress: Progress information
        """
        self.progress_info = progress
        
        # Update progress bar
        self.progress_bar.setValue(int(progress.percentage))
        
        # Update status
        status_text = progress.status.value.title()
        if progress.current_operation:
            status_text = progress.current_operation
        self.status_label.setText(status_text)
        
        # Update speed
        if progress.speed_str:
            self.speed_label.setText(f"Speed: {progress.speed_str}")
        else:
            self.speed_label.setText("Speed: --")
        
        # Update ETA
        if progress.eta_str:
            self.eta_label.setText(f"ETA: {progress.eta_str}")
        else:
            self.eta_label.setText("ETA: --")
        
        # Update size
        self.size_label.setText(f"Size: {progress.size_str}")
        
        # Update button visibility based on status
        if progress.status == ProgressStatus.FAILED:
            self.cancel_button.setVisible(False)
            self.retry_button.setVisible(True)
            self.setStyleSheet("""
                ProgressWidget {
                    border: 1px solid #f44336;
                    border-radius: 6px;
                    background-color: #ffebee;
                }
            """)
        elif progress.status == ProgressStatus.COMPLETED:
            self.cancel_button.setVisible(False)
            self.retry_button.setVisible(False)
            self.setStyleSheet("""
                ProgressWidget {
                    border: 1px solid #4CAF50;
                    border-radius: 6px;
                    background-color: #e8f5e8;
                }
            """)
        elif progress.status == ProgressStatus.CANCELLED:
            self.cancel_button.setVisible(False)
            self.retry_button.setVisible(True)
            self.setStyleSheet("""
                ProgressWidget {
                    border: 1px solid #ff9800;
                    border-radius: 6px;
                    background-color: #fff3e0;
                }
            """)


class DownloadOptionsWidget(QWidget):
    """Widget for download format and quality options."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize download options widget.
        
        Args:
            config: Application configuration
        """
        super().__init__()
        
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Download type
        type_group = QGroupBox("Download Type")
        type_layout = QVBoxLayout(type_group)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Video (MP4)", "Audio Only (MP3)", "Both"])
        self.type_combo.setCurrentText("Video (MP4)")
        type_layout.addWidget(self.type_combo)
        
        layout.addWidget(type_group)
        
        # Quality selection
        quality_group = QGroupBox("Quality")
        quality_layout = QVBoxLayout(quality_group)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best Available", "1080p", "720p", "480p", "360p", "Worst Available"])
        self.quality_combo.setCurrentText("Best Available")
        quality_layout.addWidget(self.quality_combo)
        
        layout.addWidget(quality_group)
        
        # Format options
        format_group = QGroupBox("Format Options")
        format_layout = QVBoxLayout(format_group)
        
        # Video format
        video_format_layout = QHBoxLayout()
        video_format_layout.addWidget(QLabel("Video:"))
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["MP4", "WebM", "MKV"])
        self.video_format_combo.setCurrentText("MP4")
        video_format_layout.addWidget(self.video_format_combo)
        format_layout.addLayout(video_format_layout)
        
        # Audio format
        audio_format_layout = QHBoxLayout()
        audio_format_layout.addWidget(QLabel("Audio:"))
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["MP3", "M4A", "OGG", "WAV"])
        self.audio_format_combo.setCurrentText("MP3")
        audio_format_layout.addWidget(self.audio_format_combo)
        format_layout.addLayout(audio_format_layout)
        
        layout.addWidget(format_group)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.embed_subs_check = QCheckBox("Embed subtitles")
        advanced_layout.addWidget(self.embed_subs_check)
        
        self.extract_audio_check = QCheckBox("Also extract audio")
        advanced_layout.addWidget(self.extract_audio_check)
        
        # Retry count
        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Retry attempts:"))
        self.retry_spin = QSpinBox()
        self.retry_spin.setMinimum(0)
        self.retry_spin.setMaximum(10)
        self.retry_spin.setValue(3)
        retry_layout.addWidget(self.retry_spin)
        retry_layout.addStretch()
        advanced_layout.addLayout(retry_layout)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
    
    def get_download_options(self) -> Dict[str, Any]:
        """
        Get current download options.
        
        Returns:
            Dictionary of download options
        """
        # Map combo box selections to enum values
        type_map = {
            "Video (MP4)": DownloadType.VIDEO,
            "Audio Only (MP3)": DownloadType.AUDIO,
            "Both": DownloadType.BOTH
        }
        
        quality_map = {
            "Best Available": QualityOption.BEST,
            "1080p": QualityOption.P1080,
            "720p": QualityOption.P720,
            "480p": QualityOption.P480,
            "360p": QualityOption.P360,
            "Worst Available": QualityOption.WORST
        }
        
        format_map = {
            "MP4": VideoFormat.MP4,
            "WebM": VideoFormat.WEBM,
            "MKV": VideoFormat.MKV
        }
        
        audio_format_map = {
            "MP3": AudioFormat.MP3,
            "M4A": AudioFormat.M4A,
            "OGG": AudioFormat.OGG,
            "WAV": AudioFormat.WAV
        }
        
        return {
            "download_type": type_map[self.type_combo.currentText()],
            "quality": quality_map[self.quality_combo.currentText()],
            "video_format": format_map[self.video_format_combo.currentText()],
            "audio_format": audio_format_map[self.audio_format_combo.currentText()],
            "embed_subs": self.embed_subs_check.isChecked(),
            "extract_audio": self.extract_audio_check.isChecked(),
            "retry_count": self.retry_spin.value()
        }


class ControlsPanel(QWidget):
    """
    Main controls panel for download management.
    
    Provides URL input, download options, progress tracking,
    and download history management.
    """
    
    # Signals
    url_submitted = pyqtSignal(str)  # URL for processing
    download_requested = pyqtSignal(DownloadRequest)  # Download request
    cancel_requested = pyqtSignal(str)  # Cancel download by request_id
    retry_requested = pyqtSignal(str)  # Retry download by request_id
    settings_changed = pyqtSignal(dict)  # Settings updated
    
    def __init__(self, config: Dict[str, Any], app_root: Path):
        """
        Initialize controls panel.
        
        Args:
            config: Application configuration
            app_root: Root directory of the application
        """
        super().__init__()
        
        self.config = config
        self.app_root = Path(app_root)
        self.settings = QSettings('YTDownloaderGUI', 'ControlsPanel')
        
        # State tracking
        self.current_video_info = None
        self.active_downloads = {}  # request_id -> ProgressWidget
        self.download_history = []
        
        self._setup_ui()
        self._load_settings()
        
        # Auto-paste detection timer
        self.paste_timer = QTimer()
        self.paste_timer.timeout.connect(self._check_clipboard)
        self.paste_timer.start(1000)  # Check every second
        self.last_clipboard_text = ""
        
        logger.info("Controls panel initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Download Controls")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333; padding: 5px;")
        layout.addWidget(title_label)
        
        # URL input section
        url_group = QGroupBox("YouTube URL")
        url_layout = QVBoxLayout(url_group)
        
        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here...")
        self.url_input.setValidator(URLValidator())
        self.url_input.textChanged.connect(self._on_url_changed)
        self.url_input.returnPressed.connect(self._on_url_submitted)
        url_layout.addWidget(self.url_input)
        
        # URL buttons
        url_button_layout = QHBoxLayout()
        
        self.paste_button = QPushButton("Paste")
        self.paste_button.clicked.connect(self._paste_url)
        url_button_layout.addWidget(self.paste_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_url)
        url_button_layout.addWidget(self.clear_button)
        
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self._on_url_submitted)
        self.preview_button.setEnabled(False)
        url_button_layout.addWidget(self.preview_button)
        
        url_layout.addLayout(url_button_layout)
        layout.addWidget(url_group)
        
        # Output directory section
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout(output_group)
        
        self.output_path_label = QLabel(str(Path.home() / "Downloads"))
        self.output_path_label.setStyleSheet("border: 1px solid #cccccc; padding: 5px; background-color: white;")
        output_layout.addWidget(self.output_path_label)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_output_directory)
        output_layout.addWidget(self.browse_button)
        
        layout.addWidget(output_group)
        
        # Tab widget for options and downloads
        self.tab_widget = QTabWidget()
        
        # Options tab
        self.options_widget = DownloadOptionsWidget(self.config)
        self.tab_widget.addTab(self.options_widget, "Options")
        
        # Downloads tab
        downloads_tab = QWidget()
        downloads_layout = QVBoxLayout(downloads_tab)
        
        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self._start_download)
        downloads_layout.addWidget(self.download_button)
        
        # Progress list
        progress_label = QLabel("Active Downloads")
        progress_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        downloads_layout.addWidget(progress_label)
        
        # Scroll area for progress widgets
        self.progress_scroll = QScrollArea()
        self.progress_scroll.setWidgetResizable(True)
        self.progress_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(5, 5, 5, 5)
        self.progress_layout.setSpacing(5)
        self.progress_layout.addStretch()  # Push widgets to top
        
        self.progress_scroll.setWidget(self.progress_container)
        downloads_layout.addWidget(self.progress_scroll)
        
        # Clear completed button
        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.clicked.connect(self._clear_completed_downloads)
        downloads_layout.addWidget(self.clear_completed_button)
        
        self.tab_widget.addTab(downloads_tab, "Downloads")
        
        layout.addWidget(self.tab_widget)
    
    def _load_settings(self):
        """Load saved settings."""
        # Load output directory
        output_dir = self.settings.value('output_directory', str(Path.home() / "Downloads"))
        self.output_path_label.setText(output_dir)
        
        # Load other settings
        # Implementation for loading download options, etc.
    
    def _save_settings(self):
        """Save current settings."""
        self.settings.setValue('output_directory', self.output_path_label.text())
        self.settings.sync()
    
    def _check_clipboard(self):
        """Check clipboard for YouTube URLs and auto-paste."""
        try:
            clipboard = QApplication.clipboard()
            clipboard_text = clipboard.text()
            
            if (clipboard_text != self.last_clipboard_text and 
                clipboard_text and 
                ('youtube.com' in clipboard_text.lower() or 'youtu.be' in clipboard_text.lower()) and
                not self.url_input.text()):
                
                self.url_input.setText(clipboard_text)
                self.last_clipboard_text = clipboard_text
                
        except Exception as e:
            logger.error(f"Error checking clipboard: {e}")
    
    def _on_url_changed(self, text: str):
        """Handle URL input changes."""
        is_valid = len(text) > 0 and ('youtube.com' in text.lower() or 'youtu.be' in text.lower())
        self.preview_button.setEnabled(is_valid)
        self.download_button.setEnabled(is_valid and self.current_video_info is not None)
    
    def _on_url_submitted(self):
        """Handle URL submission for preview."""
        url = self.url_input.text().strip()
        if url:
            self.url_submitted.emit(url)
    
    def _paste_url(self):
        """Paste URL from clipboard."""
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())
    
    def _clear_url(self):
        """Clear URL input."""
        self.url_input.clear()
        self.current_video_info = None
        self.download_button.setEnabled(False)
    
    def _browse_output_directory(self):
        """Browse for output directory."""
        current_dir = self.output_path_label.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            current_dir
        )
        
        if directory:
            self.output_path_label.setText(directory)
            self._save_settings()
    
    def _start_download(self):
        """Start download with current options."""
        if not self.current_video_info:
            QMessageBox.warning(self, "No Video", "Please preview a video first.")
            return
        
        try:
            # Get download options
            options = self.options_widget.get_download_options()
            
            # Create download request
            request = DownloadRequest(
                url=self.current_video_info.url,
                download_type=options["download_type"],
                output_path=Path(self.output_path_label.text()),
                video_format=options["video_format"],
                audio_format=options["audio_format"],
                quality=options["quality"],
                embed_subs=options["embed_subs"],
                extract_audio=options["extract_audio"],
                retry_count=options["retry_count"],
                request_id=str(uuid.uuid4())
            )
            
            # Add progress widget
            self._add_progress_widget(request.request_id, str(request.url), self.current_video_info.title)
            
            # Emit download request
            self.download_requested.emit(request)
            
            # Switch to downloads tab
            self.tab_widget.setCurrentIndex(1)
            
            logger.info(f"Started download: {request.request_id}")
            
        except Exception as e:
            logger.error(f"Error starting download: {e}")
            QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")
    
    def _add_progress_widget(self, request_id: str, url: str, title: str):
        """Add progress widget for new download."""
        if request_id in self.active_downloads:
            return  # Already exists
        
        progress_widget = ProgressWidget(request_id, url, title)
        progress_widget.cancel_requested.connect(self.cancel_requested.emit)
        progress_widget.retry_requested.connect(self.retry_requested.emit)
        
        # Insert before stretch
        self.progress_layout.insertWidget(self.progress_layout.count() - 1, progress_widget)
        self.active_downloads[request_id] = progress_widget
    
    def _clear_completed_downloads(self):
        """Remove completed download widgets."""
        to_remove = []
        
        for request_id, widget in self.active_downloads.items():
            if widget.progress_info and widget.progress_info.status in [
                ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED
            ]:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            widget = self.active_downloads[request_id]
            self.progress_layout.removeWidget(widget)
            widget.setParent(None)
            del self.active_downloads[request_id]
    
    # Public interface methods
    @pyqtSlot(VideoInfo)
    def set_video_info(self, video_info: VideoInfo):
        """
        Set current video information.
        
        Args:
            video_info: VideoInfo object with metadata
        """
        self.current_video_info = video_info
        self.download_button.setEnabled(bool(self.url_input.text()))
    
    @pyqtSlot(str, ProgressInfo)
    def update_download_progress(self, request_id: str, progress: ProgressInfo):
        """
        Update download progress.
        
        Args:
            request_id: Download request ID
            progress: Progress information
        """
        if request_id in self.active_downloads:
            self.active_downloads[request_id].update_progress(progress)
    
    def get_output_directory(self) -> Path:
        """
        Get current output directory.
        
        Returns:
            Output directory path
        """
        return Path(self.output_path_label.text())
    
    def set_url(self, url: str):
        """
        Set URL in input field.
        
        Args:
            url: URL to set
        """
        self.url_input.setText(url)
    
    def clear_video_info(self):
        """Clear current video information."""
        self.current_video_info = None
        self.download_button.setEnabled(False)
    
    def get_active_downloads(self) -> List[str]:
        """
        Get list of active download IDs.
        
        Returns:
            List of active request IDs
        """
        return list(self.active_downloads.keys())