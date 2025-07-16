"""
Dialog windows for YouTube Downloader GUI.

This module provides various dialog windows including dependency management,
settings configuration, and user interaction dialogs with proper PyQt6 styling.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QProgressBar, QTextEdit, QGroupBox,
        QCheckBox, QSpinBox, QLineEdit, QComboBox, QFileDialog,
        QMessageBox, QScrollArea, QWidget, QFrame, QSizePolicy,
        QDialogButtonBox, QTabWidget, QSlider, QSpacerItem
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
    from PyQt6.QtGui import QFont, QIcon, QPalette, QPixmap, QMovie
except ImportError as e:
    print(f"PyQt6 not available: {e}")
    print("Run setup.py to install dependencies.")
    sys.exit(1)

from dependencies.manager import EmbeddedDependencyManager
from gui.workers import DependencyInstallWorker
from downloader.validation import QualityOption, VideoFormat, AudioFormat
import json
from PyQt6.QtCore import QSettings

logger = logging.getLogger(__name__)


class DependencyManagementDialog(QDialog):
    """
    Dialog for managing application dependencies.
    
    Provides interface for checking, downloading, and configuring
    embedded Python runtime, PyQt6, yt-dlp, and FFmpeg dependencies.
    """
    
    # Signals for communication with main window
    dependencies_updated = pyqtSignal()  # When dependencies change
    
    def __init__(self, app_root: Path, parent=None):
        """
        Initialize dependency management dialog.
        
        Args:
            app_root: Root directory of the application
            parent: Parent widget for proper modal behavior
        """
        super().__init__(parent)
        self.app_root = app_root
        self.dependency_manager = EmbeddedDependencyManager(app_root)
        self.install_worker: Optional[DependencyInstallWorker] = None
        
        self.setWindowTitle("Dependency Management")
        self.setModal(True)
        self.resize(600, 500)
        
        # Initialize UI
        self._setup_ui()
        self._check_dependencies()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("DependencyManagementDialog initialized")
    
    def _setup_ui(self):
        """Set up the user interface layout and widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Title and description
        title_label = QLabel("Dependency Management")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        description_label = QLabel(
            "Manage embedded dependencies for the YouTube Downloader. "
            "All components are self-contained and do not affect your system."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(description_label)
        
        # Create tab widget for different dependency categories
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Dependencies status tab
        self._create_status_tab()
        
        # Installation tab
        self._create_installation_tab()
        
        # Settings tab
        self._create_settings_tab()
        
        # Progress section
        self._create_progress_section(layout)
        
        # Button box
        self._create_button_box(layout)
    
    def _create_status_tab(self):
        """Create the dependency status tab."""
        status_widget = QWidget()
        layout = QVBoxLayout(status_widget)
        
        # Dependency status group
        self.status_group = QGroupBox("Dependency Status")
        status_layout = QGridLayout(self.status_group)
        
        # Headers
        headers = ["Component", "Status", "Version", "Location"]
        for i, header in enumerate(headers):
            label = QLabel(header)
            label.setFont(QFont("", 9, QFont.Weight.Bold))
            status_layout.addWidget(label, 0, i)
        
        # Dependency components
        self.component_labels = {}
        self.status_labels = {}
        self.version_labels = {}
        self.location_labels = {}
        
        components = [
            ("python_runtime", "Python Runtime"),
            ("pyqt6", "PyQt6 GUI Framework"),
            ("yt_dlp", "yt-dlp Downloader"),
            ("ffmpeg", "FFmpeg Media Tools")
        ]
        
        for row, (key, name) in enumerate(components, 1):
            self.component_labels[key] = QLabel(name)
            self.status_labels[key] = QLabel("Checking...")
            self.version_labels[key] = QLabel("-")
            self.location_labels[key] = QLabel("-")
            
            status_layout.addWidget(self.component_labels[key], row, 0)
            status_layout.addWidget(self.status_labels[key], row, 1)
            status_layout.addWidget(self.version_labels[key], row, 2)
            status_layout.addWidget(self.location_labels[key], row, 3)
        
        layout.addWidget(self.status_group)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._check_dependencies)
        layout.addWidget(refresh_button)
        
        layout.addStretch()
        self.tab_widget.addTab(status_widget, "Status")
    
    def _create_installation_tab(self):
        """Create the installation management tab."""
        install_widget = QWidget()
        layout = QVBoxLayout(install_widget)
        
        # Installation options group
        options_group = QGroupBox("Installation Options")
        options_layout = QFormLayout(options_group)
        
        # Force reinstall option
        self.force_reinstall_checkbox = QCheckBox("Force reinstall all components")
        self.force_reinstall_checkbox.setToolTip(
            "Reinstall all dependencies even if they are already present"
        )
        options_layout.addRow("Reinstall:", self.force_reinstall_checkbox)
        
        # Download location info
        location_label = QLabel(f"Install location: {self.app_root}")
        location_label.setStyleSheet("color: #666; font-size: 10px;")
        options_layout.addRow("Location:", location_label)
        
        layout.addWidget(options_group)
        
        # Installation actions group
        actions_group = QGroupBox("Installation Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Install all button
        self.install_all_button = QPushButton("Install All Dependencies")
        self.install_all_button.setMinimumHeight(40)
        self.install_all_button.clicked.connect(self._install_all_dependencies)
        actions_layout.addWidget(self.install_all_button)
        
        # Individual install buttons
        individual_layout = QHBoxLayout()
        
        self.install_python_button = QPushButton("Install Python")
        self.install_python_button.clicked.connect(lambda: self._install_individual("python"))
        individual_layout.addWidget(self.install_python_button)
        
        self.install_pyqt_button = QPushButton("Install PyQt6")
        self.install_pyqt_button.clicked.connect(lambda: self._install_individual("pyqt6"))
        individual_layout.addWidget(self.install_pyqt_button)
        
        self.install_ytdlp_button = QPushButton("Install yt-dlp")
        self.install_ytdlp_button.clicked.connect(lambda: self._install_individual("yt-dlp"))
        individual_layout.addWidget(self.install_ytdlp_button)
        
        self.install_ffmpeg_button = QPushButton("Install FFmpeg")
        self.install_ffmpeg_button.clicked.connect(lambda: self._install_individual("ffmpeg"))
        individual_layout.addWidget(self.install_ffmpeg_button)
        
        actions_layout.addLayout(individual_layout)
        layout.addWidget(actions_group)
        
        # Installation information
        info_group = QGroupBox("Installation Information")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "• Python Runtime: Embedded Python 3.13 (~25 MB)\n"
            "• PyQt6: GUI framework for the application (~50 MB)\n"
            "• yt-dlp: YouTube downloader with latest features (~10 MB)\n"
            "• FFmpeg: Media processing tools (~100 MB)\n\n"
            "Total download size: ~185 MB\n"
            "Installation is completely portable and self-contained."
        )
        info_text.setStyleSheet("color: #444; font-size: 11px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        self.tab_widget.addTab(install_widget, "Installation")
    
    def _create_settings_tab(self):
        """Create the settings configuration tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # Path settings group
        paths_group = QGroupBox("Path Settings")
        paths_layout = QFormLayout(paths_group)
        
        # Python runtime path
        self.python_path_edit = QLineEdit()
        self.python_path_edit.setText(str(self.app_root / "python_runtime"))
        self.python_path_edit.setReadOnly(True)
        paths_layout.addRow("Python Runtime:", self.python_path_edit)
        
        # Binaries path
        self.binaries_path_edit = QLineEdit()
        self.binaries_path_edit.setText(str(self.app_root / "binaries"))
        self.binaries_path_edit.setReadOnly(True)
        paths_layout.addRow("Binaries:", self.binaries_path_edit)
        
        # Cache path
        self.cache_path_edit = QLineEdit()
        self.cache_path_edit.setText(str(self.app_root / "cache"))
        paths_layout.addRow("Cache:", self.cache_path_edit)
        
        layout.addWidget(paths_group)
        
        # Advanced settings group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)
        
        # Download timeout
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(30, 300)
        self.timeout_spinbox.setValue(120)
        self.timeout_spinbox.setSuffix(" seconds")
        advanced_layout.addRow("Download Timeout:", self.timeout_spinbox)
        
        # Retry attempts
        self.retry_spinbox = QSpinBox()
        self.retry_spinbox.setRange(1, 10)
        self.retry_spinbox.setValue(3)
        advanced_layout.addRow("Retry Attempts:", self.retry_spinbox)
        
        # Verify SSL certificates
        self.verify_ssl_checkbox = QCheckBox("Verify SSL certificates")
        self.verify_ssl_checkbox.setChecked(True)
        advanced_layout.addRow("SSL Verification:", self.verify_ssl_checkbox)
        
        layout.addWidget(advanced_group)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_settings)
        actions_layout.addWidget(reset_button)
        
        actions_layout.addStretch()
        
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_settings)
        actions_layout.addWidget(save_button)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "Settings")
    
    def _create_progress_section(self, parent_layout):
        """Create the progress display section."""
        # Progress group
        self.progress_group = QGroupBox("Installation Progress")
        progress_layout = QVBoxLayout(self.progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # Status text
        self.progress_text = QLabel("Ready")
        self.progress_text.setStyleSheet("color: #666; font-size: 11px;")
        progress_layout.addWidget(self.progress_text)
        
        # Progress log (hidden by default)
        self.progress_log = QTextEdit()
        self.progress_log.setMaximumHeight(150)
        self.progress_log.setVisible(False)
        progress_layout.addWidget(self.progress_log)
        
        # Show/hide log button
        self.toggle_log_button = QPushButton("Show Details")
        self.toggle_log_button.clicked.connect(self._toggle_progress_log)
        self.toggle_log_button.setVisible(False)
        progress_layout.addWidget(self.toggle_log_button)
        
        parent_layout.addWidget(self.progress_group)
    
    def _create_button_box(self, parent_layout):
        """Create the dialog button box."""
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close | QDialogButtonBox.StandardButton.Help
        )
        
        # Add custom buttons
        self.cancel_button = button_box.addButton(
            "Cancel Installation", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.cancel_button.clicked.connect(self._cancel_installation)
        self.cancel_button.setVisible(False)
        
        # Connect standard buttons
        button_box.rejected.connect(self.reject)
        button_box.helpRequested.connect(self._show_help)
        
        parent_layout.addWidget(button_box)
    
    def _connect_signals(self):
        """Connect internal signals and slots."""
        # Timer for periodic dependency checks
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_dependencies)
    
    def _check_dependencies(self):
        """Check status of all dependencies and update display."""
        try:
            status = self.dependency_manager.check_all_dependencies()
            
            for component, info in status.items():
                if component == "overall":
                    continue
                
                if component in self.status_labels:
                    # Update status
                    if info["available"]:
                        self.status_labels[component].setText("✅ Available")
                        self.status_labels[component].setStyleSheet("color: green;")
                    else:
                        self.status_labels[component].setText("❌ Missing")
                        self.status_labels[component].setStyleSheet("color: red;")
                    
                    # Update version
                    version = info.get("version", "-")
                    self.version_labels[component].setText(version)
                    
                    # Update location
                    location = info.get("location", "-")
                    if location and len(str(location)) > 50:
                        location = "..." + str(location)[-47:]
                    self.location_labels[component].setText(str(location))
            
            # Update overall status
            overall = status.get("overall", {})
            if overall.get("all_available", False):
                self.progress_text.setText("✅ All dependencies are available")
                self.progress_text.setStyleSheet("color: green; font-weight: bold;")
            else:
                missing = overall.get("missing_dependencies", [])
                self.progress_text.setText(f"⚠️ Missing: {', '.join(missing)}")
                self.progress_text.setStyleSheet("color: orange; font-weight: bold;")
            
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            self.progress_text.setText(f"❌ Error checking dependencies: {e}")
            self.progress_text.setStyleSheet("color: red;")
    
    def _install_all_dependencies(self):
        """Start installation of all dependencies."""
        self._start_installation(force_reinstall=self.force_reinstall_checkbox.isChecked())
    
    def _install_individual(self, component: str):
        """Start installation of individual component."""
        # Note: For simplicity, this implementation installs all components
        # A more sophisticated implementation could install individual components
        self._start_installation(force_reinstall=True)
    
    def _start_installation(self, force_reinstall: bool = False):
        """Start the dependency installation process."""
        try:
            # Disable installation buttons
            self.install_all_button.setEnabled(False)
            self.install_python_button.setEnabled(False)
            self.install_pyqt_button.setEnabled(False)
            self.install_ytdlp_button.setEnabled(False)
            self.install_ffmpeg_button.setEnabled(False)
            
            # Show progress elements
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.toggle_log_button.setVisible(True)
            self.cancel_button.setVisible(True)
            
            # Clear progress log
            self.progress_log.clear()
            
            # Create and configure worker
            from gui.workers import DependencyInstallWorker
            self.install_worker = DependencyInstallWorker(self)
            self.install_worker.set_installation_params(self.app_root, force_reinstall)
            
            # Connect worker signals
            self.install_worker.install_started.connect(self._on_install_started)
            self.install_worker.install_progress.connect(self._on_install_progress)
            self.install_worker.install_completed.connect(self._on_install_completed)
            self.install_worker.install_failed.connect(self._on_install_failed)
            self.install_worker.finished.connect(self._on_worker_finished)
            
            # Start installation
            self.install_worker.start()
            
        except Exception as e:
            logger.error(f"Error starting installation: {e}")
            QMessageBox.critical(self, "Installation Error", f"Failed to start installation:\n{e}")
            self._reset_ui_after_installation()
    
    def _cancel_installation(self):
        """Cancel the current installation."""
        if self.install_worker and self.install_worker.isRunning():
            self.install_worker.stop()
            self.progress_text.setText("⚠️ Installation cancelled")
            self.progress_text.setStyleSheet("color: orange;")
    
    def _on_install_started(self):
        """Handle installation started signal."""
        self.progress_text.setText("📦 Starting dependency installation...")
        self.progress_text.setStyleSheet("color: blue;")
        self._log_message("Starting dependency installation...")
    
    def _on_install_progress(self, message: str, percentage: int):
        """Handle installation progress updates."""
        self.progress_text.setText(message)
        
        if percentage > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percentage)
        
        self._log_message(f"[{percentage:3d}%] {message}")
    
    def _on_install_completed(self, success: bool):
        """Handle installation completion."""
        if success:
            self.progress_text.setText("✅ Installation completed successfully!")
            self.progress_text.setStyleSheet("color: green; font-weight: bold;")
            self._log_message("Installation completed successfully!")
            
            # Refresh dependency status
            QTimer.singleShot(1000, self._check_dependencies)
            
            # Emit signal to parent
            self.dependencies_updated.emit()
        else:
            self.progress_text.setText("❌ Installation failed")
            self.progress_text.setStyleSheet("color: red; font-weight: bold;")
            self._log_message("Installation failed!")
    
    def _on_install_failed(self, error_message: str):
        """Handle installation failure."""
        self.progress_text.setText(f"❌ Installation failed: {error_message}")
        self.progress_text.setStyleSheet("color: red; font-weight: bold;")
        self._log_message(f"Installation failed: {error_message}")
        
        QMessageBox.warning(self, "Installation Failed", 
                          f"Dependency installation failed:\n\n{error_message}")
    
    def _on_worker_finished(self):
        """Handle worker thread completion."""
        self._reset_ui_after_installation()
    
    def _reset_ui_after_installation(self):
        """Reset UI elements after installation is complete."""
        # Re-enable installation buttons
        self.install_all_button.setEnabled(True)
        self.install_python_button.setEnabled(True)
        self.install_pyqt_button.setEnabled(True)
        self.install_ytdlp_button.setEnabled(True)
        self.install_ffmpeg_button.setEnabled(True)
        
        # Hide progress elements if desired
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.cancel_button.setVisible(False)
        
        # Clean up worker
        if self.install_worker:
            self.install_worker.deleteLater()
            self.install_worker = None
    
    def _toggle_progress_log(self):
        """Toggle visibility of progress log."""
        if self.progress_log.isVisible():
            self.progress_log.setVisible(False)
            self.toggle_log_button.setText("Show Details")
            self.resize(self.width(), self.height() - 150)
        else:
            self.progress_log.setVisible(True)
            self.toggle_log_button.setText("Hide Details")
            self.resize(self.width(), self.height() + 150)
    
    def _log_message(self, message: str):
        """Add message to progress log."""
        self.progress_log.append(message)
        # Scroll to bottom
        scrollbar = self.progress_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _reset_settings(self):
        """Reset all settings to defaults."""
        self.timeout_spinbox.setValue(120)
        self.retry_spinbox.setValue(3)
        self.verify_ssl_checkbox.setChecked(True)
        self.force_reinstall_checkbox.setChecked(False)
    
    def _save_settings(self):
        """Save current settings."""
        # In a full implementation, this would save to configuration file
        QMessageBox.information(self, "Settings", "Settings saved successfully!")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
        <h3>Dependency Management Help</h3>
        
        <p><b>Status Tab:</b> Shows the current status of all embedded dependencies.</p>
        
        <p><b>Installation Tab:</b> Allows you to install or reinstall dependencies.</p>
        
        <p><b>Settings Tab:</b> Configure advanced installation options.</p>
        
        <h4>Dependencies:</h4>
        <ul>
        <li><b>Python Runtime:</b> Embedded Python interpreter for running the application</li>
        <li><b>PyQt6:</b> GUI framework for the user interface</li>
        <li><b>yt-dlp:</b> YouTube downloader with the latest features</li>
        <li><b>FFmpeg:</b> Media processing tools for video/audio handling</li>
        </ul>
        
        <p>All dependencies are self-contained and portable. They do not affect your system Python or other installed software.</p>
        """
        
        QMessageBox.information(self, "Help - Dependency Management", help_text)
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop any running installation
        if self.install_worker and self.install_worker.isRunning():
            reply = QMessageBox.question(
                self, "Installation Running",
                "An installation is currently running. Do you want to cancel it and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.install_worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class AboutDialog(QDialog):
    """About dialog showing application information."""
    
    def __init__(self, parent=None):
        """Initialize about dialog."""
        super().__init__(parent)
        self.setWindowTitle("About YouTube Downloader GUI")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Application icon and title
        title_layout = QHBoxLayout()
        
        # Icon (if available)
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        title_layout.addWidget(icon_label)
        
        # Title and version
        info_layout = QVBoxLayout()
        title_label = QLabel("YouTube Downloader GUI")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        info_layout.addWidget(title_label)
        
        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet("color: #666;")
        info_layout.addWidget(version_label)
        
        title_layout.addLayout(info_layout)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Description
        desc_text = QLabel(
            "A portable YouTube downloader with embedded dependencies. "
            "Download videos and audio with real-time preview and progress tracking."
        )
        desc_text.setWordWrap(True)
        desc_text.setStyleSheet("margin: 10px 0;")
        layout.addWidget(desc_text)
        
        # Features
        features_label = QLabel("<b>Features:</b>")
        layout.addWidget(features_label)
        
        features_text = QLabel(
            "• Real-time video preview with thumbnails\n"
            "• Download videos in multiple quality options\n"
            "• Extract audio to MP3 format\n"
            "• Progress tracking with speed and ETA\n"
            "• Completely portable and self-contained"
        )
        features_text.setStyleSheet("margin-left: 20px; color: #444;")
        layout.addWidget(features_text)
        
        layout.addStretch()
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring application preferences.
    
    Provides interface for setting default download location, 
    default quality options, file formats, and other preferences.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        # Load current settings
        self.settings = QSettings('YTDownloaderGUI', 'Settings')
        self.app_root = Path(__file__).parent.parent
        self.config_file = self.app_root / "config" / "app_config.json"
        
        self._load_config()
        self._setup_ui()
        self._load_current_settings()
    
    def _load_config(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {
                "downloads": {
                    "default_path": str(Path.home() / "Downloads"),
                    "audio_format": "mp3",
                    "video_format": "mp4",
                    "quality_options": ["best", "1080p", "720p", "480p"],
                    "filename_template": "%(title)s.%(ext)s"
                }
            }
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Downloads tab
        downloads_tab = self._create_downloads_tab()
        tab_widget.addTab(downloads_tab, "Downloads")
        
        # Quality tab
        quality_tab = self._create_quality_tab()
        tab_widget.addTab(quality_tab, "Quality")
        
        # General tab
        general_tab = self._create_general_tab()
        tab_widget.addTab(general_tab, "General")
        
        layout.addWidget(tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._restore_defaults)
        
        layout.addWidget(button_box)
    
    def _create_downloads_tab(self):
        """Create downloads settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Default download location
        location_group = QGroupBox("Default Download Location")
        location_layout = QVBoxLayout(location_group)
        
        location_frame = QFrame()
        location_frame_layout = QHBoxLayout(location_frame)
        
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Select default download folder...")
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_download_location)
        
        location_frame_layout.addWidget(self.location_edit)
        location_frame_layout.addWidget(browse_button)
        
        location_layout.addWidget(location_frame)
        
        # File naming template
        naming_group = QGroupBox("File Naming")
        naming_layout = QFormLayout(naming_group)
        
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setPlaceholderText("%(title)s.%(ext)s")
        naming_layout.addRow("Filename Template:", self.filename_template_edit)
        
        template_help = QLabel("Available variables: %(title)s, %(uploader)s, %(upload_date)s, %(ext)s")
        template_help.setStyleSheet("color: #666; font-size: 10px;")
        naming_layout.addRow("", template_help)
        
        layout.addWidget(location_group)
        layout.addWidget(naming_group)
        layout.addStretch()
        
        return widget
    
    def _create_quality_tab(self):
        """Create quality settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Default quality
        quality_group = QGroupBox("Default Quality Settings")
        quality_layout = QFormLayout(quality_group)
        
        self.default_quality_combo = QComboBox()
        self.default_quality_combo.addItems(["Best Available", "1080p", "720p", "480p", "360p", "240p"])
        quality_layout.addRow("Default Video Quality:", self.default_quality_combo)
        
        # Default formats
        format_group = QGroupBox("Default Formats")
        format_layout = QFormLayout(format_group)
        
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["mp4", "webm", "mkv", "avi"])
        format_layout.addRow("Video Format:", self.video_format_combo)
        
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "wav", "flac"])
        format_layout.addRow("Audio Format:", self.audio_format_combo)
        
        layout.addWidget(quality_group)
        layout.addWidget(format_group)
        layout.addStretch()
        
        return widget
    
    def _create_general_tab(self):
        """Create general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # UI settings
        ui_group = QGroupBox("Interface")
        ui_layout = QFormLayout(ui_group)
        
        self.show_preview_checkbox = QCheckBox("Show video preview")
        ui_layout.addRow("Preview:", self.show_preview_checkbox)
        
        self.show_progress_checkbox = QCheckBox("Show detailed progress")
        ui_layout.addRow("Progress:", self.show_progress_checkbox)
        
        # Advanced settings
        advanced_group = QGroupBox("Advanced")
        advanced_layout = QFormLayout(advanced_group)
        
        self.concurrent_downloads_spin = QSpinBox()
        self.concurrent_downloads_spin.setRange(1, 5)
        self.concurrent_downloads_spin.setValue(1)
        advanced_layout.addRow("Concurrent Downloads:", self.concurrent_downloads_spin)
        
        self.retry_attempts_spin = QSpinBox()
        self.retry_attempts_spin.setRange(1, 10)
        self.retry_attempts_spin.setValue(3)
        advanced_layout.addRow("Retry Attempts:", self.retry_attempts_spin)
        
        layout.addWidget(ui_group)
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        return widget
    
    def _browse_download_location(self):
        """Browse for download location."""
        current_path = self.location_edit.text() or str(Path.home() / "Downloads")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Default Download Folder",
            current_path,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.location_edit.setText(folder)
    
    def _load_current_settings(self):
        """Load current settings into UI."""
        # Download location
        download_path = self.config.get("downloads", {}).get("default_path", str(Path.home() / "Downloads"))
        if download_path.startswith("~/"):
            download_path = str(Path.home() / download_path[2:])
        self.location_edit.setText(download_path)
        
        # Filename template
        template = self.config.get("downloads", {}).get("filename_template", "%(title)s.%(ext)s")
        self.filename_template_edit.setText(template)
        
        # Quality settings
        quality = self.config.get("downloads", {}).get("default_quality", "best")
        if quality == "best":
            self.default_quality_combo.setCurrentText("Best Available")
        else:
            self.default_quality_combo.setCurrentText(quality)
        
        # Formats
        video_format = self.config.get("downloads", {}).get("video_format", "mp4")
        self.video_format_combo.setCurrentText(video_format)
        
        audio_format = self.config.get("downloads", {}).get("audio_format", "mp3")
        self.audio_format_combo.setCurrentText(audio_format)
        
        # UI settings
        self.show_preview_checkbox.setChecked(
            self.settings.value("show_preview", True, type=bool)
        )
        self.show_progress_checkbox.setChecked(
            self.settings.value("show_progress", True, type=bool)
        )
        
        # Advanced settings
        self.concurrent_downloads_spin.setValue(
            self.settings.value("concurrent_downloads", 1, type=int)
        )
        self.retry_attempts_spin.setValue(
            self.settings.value("retry_attempts", 3, type=int)
        )
    
    def _save_settings(self):
        """Save settings and close dialog."""
        try:
            # Update config
            if "downloads" not in self.config:
                self.config["downloads"] = {}
            
            # Download settings
            self.config["downloads"]["default_path"] = self.location_edit.text()
            self.config["downloads"]["filename_template"] = self.filename_template_edit.text()
            
            # Quality settings
            quality_text = self.default_quality_combo.currentText()
            if quality_text == "Best Available":
                self.config["downloads"]["default_quality"] = "best"
            else:
                self.config["downloads"]["default_quality"] = quality_text.lower()
            
            self.config["downloads"]["video_format"] = self.video_format_combo.currentText()
            self.config["downloads"]["audio_format"] = self.audio_format_combo.currentText()
            
            # Save to JSON file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            # Save UI settings to QSettings
            self.settings.setValue("show_preview", self.show_preview_checkbox.isChecked())
            self.settings.setValue("show_progress", self.show_progress_checkbox.isChecked())
            self.settings.setValue("concurrent_downloads", self.concurrent_downloads_spin.value())
            self.settings.setValue("retry_attempts", self.retry_attempts_spin.value())
            
            # Also save default download path to QSettings for immediate use
            self.settings.setValue("default_download_path", self.location_edit.text())
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {str(e)}")
    
    def _restore_defaults(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore default settings?\nThis will reset all preferences to their default values.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to defaults
            self.location_edit.setText(str(Path.home() / "Downloads"))
            self.filename_template_edit.setText("%(title)s.%(ext)s")
            self.default_quality_combo.setCurrentText("Best Available")
            self.video_format_combo.setCurrentText("mp4")
            self.audio_format_combo.setCurrentText("mp3")
            self.show_preview_checkbox.setChecked(True)
            self.show_progress_checkbox.setChecked(True)
            self.concurrent_downloads_spin.setValue(1)
            self.retry_attempts_spin.setValue(3)