"""
Main application window for YouTube Downloader GUI.

This module provides the main QMainWindow with menu system, status bar,
and layout management for all GUI components.
"""

import sys
import os
import json
# Logging import removed
from pathlib import Path
from typing import Dict, Any, Optional

# Debug flag - set directly to avoid circular import
True  # Debug always enabled = False  # Set to True to show CMD window for debugging

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QStatusBar,
        QMessageBox, QFileDialog, QSplitter, QFrame, QLabel,
        QApplication, QStyleFactory, QProgressBar, QLineEdit, QPushButton, QRadioButton, QDialog
    )
    from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal, QThread
    from PyQt6.QtGui import QIcon, QFont, QPalette, QPixmap, QAction
except ImportError as e:
    print(f"PyQt6 not available: {e}")
    print("Run setup.py to install dependencies.")
    sys.exit(1)

# Logger removed


class MainWindow(QMainWindow):
    """
    Main application window for YouTube Downloader GUI.
    
    Provides the main interface with menu system, status bar,
    and layout management for preview and control panels.
    """
    
    # Signals
    url_requested = pyqtSignal(str)  # When user requests URL processing
    download_requested = pyqtSignal(dict)  # When user requests download
    settings_changed = pyqtSignal(dict)  # When settings are modified
    
    def __init__(self, config: Dict[str, Any], app_root: Path):
        """
        Initialize main window.
        
        Args:
            config: Application configuration dictionary
            app_root: Root directory of the application
        """
        super().__init__()
        
        self.config = config
        self.app_root = Path(app_root)
        self.settings = QSettings('YTDownloaderGUI', 'MainWindow')
        
        # Initialize components
        self.preview_panel = None
        self.controls_panel = None
        self.status_progress = None
        
        # Status tracking
        self.current_status = "Ready"
        self.download_count = 0
        self.active_downloads = 0
        
        # Setup UI
        self._setup_window()
        self._create_menu_bar()
        self._create_status_bar()
        self._create_central_widget()
        self._apply_styling()
        self._restore_settings()
        
        # Setup update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_display)
        self.status_timer.start(1000)  # Update every second
        
        print("Main window initialized")
    
    def _setup_window(self):
        """Configure main window properties."""
        # Window title and icon
        self.setWindowTitle(f"{self.config['app']['name']} v{self.config['app']['version']}")
        
        # Set window icon if available
        icon_path = self.app_root / "resources" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Window size and position
        default_size = self.config['app']['window_size']
        self.resize(default_size[0], default_size[1])
        
        # Center window on screen
        self._center_window()
        
        # Window properties
        self.setMinimumSize(600, 500)
        self.setAcceptDrops(True)  # Enable drag and drop
    
    def _center_window(self):
        """Center window on the primary screen."""
        screen = QApplication.primaryScreen().geometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())
    
    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Import URLs action
        import_action = QAction('&Import URLs...', self)
        import_action.setShortcut('Ctrl+I')
        import_action.setStatusTip('Import URLs from file')
        import_action.triggered.connect(self._import_urls)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('&Tools')
        
        # Settings action
        settings_action = QAction('&Settings...', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.setStatusTip('Open application settings')
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)
        
        # Dependencies action
        deps_action = QAction('&Manage Dependencies...', self)
        deps_action.setStatusTip('Check and manage embedded dependencies')
        deps_action.triggered.connect(self._manage_dependencies)
        tools_menu.addAction(deps_action)
        
        tools_menu.addSeparator()
        
        # Clear cache action
        cache_action = QAction('&Clear Cache', self)
        cache_action.setStatusTip('Clear download cache and temporary files')
        cache_action.triggered.connect(self._clear_cache)
        tools_menu.addAction(cache_action)
        
        # Open downloads folder
        folder_action = QAction('Open &Downloads Folder', self)
        folder_action.setStatusTip('Open downloads directory')
        folder_action.triggered.connect(self._open_downloads_folder)
        tools_menu.addAction(folder_action)
        
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        # About action
        about_action = QAction('&About', self)
        about_action.setStatusTip('Show application information')
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Help action
        help_action = QAction('&Help', self)
        help_action.setShortcut('F1')
        help_action.setStatusTip('Show help information')
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
    
    def _create_status_bar(self):
        """Create application status bar."""
        self.status_bar = self.statusBar()
        
        # Main status label
        self.status_label = QLabel(self.current_status)
        self.status_bar.addWidget(self.status_label)
        
        # Spacer
        self.status_bar.addPermanentWidget(QLabel(""))
        
        # Progress bar for active downloads
        self.status_progress = QProgressBar()
        self.status_progress.setVisible(False)
        self.status_progress.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.status_progress)
        
        # Version label
        version_label = QLabel(f"v{self.config['app']['version']}")
        version_label.setStyleSheet("color: gray;")
        self.status_bar.addPermanentWidget(version_label)
    
    def _create_central_widget(self):
        """Create and setup central widget layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal layout like before but without splitter
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Left panel - Preview 
        self.preview_frame = QFrame()
        self.preview_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.preview_frame.setMinimumWidth(350)
        self.preview_frame.setMaximumWidth(450)
        
        preview_layout = QVBoxLayout(self.preview_frame)
        self._setup_preview_panel(preview_layout)
        
        main_layout.addWidget(self.preview_frame)
        
        # Right panel - Controls
        self.controls_frame = QFrame()
        self.controls_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.controls_frame.setMinimumWidth(400)
        
        controls_layout = QVBoxLayout(self.controls_frame)
        self._setup_controls_panel(controls_layout)
        
        main_layout.addWidget(self.controls_frame)
        
        # Store references for panel integration
        self.preview_layout = preview_layout
        self.controls_layout = controls_layout
    
    def _apply_styling(self):
        """Apply application styling based on theme."""
        theme = self.config['app']['theme']
        
        if theme == 'dark':
            self._apply_dark_theme()
        elif theme == 'light':
            self._apply_light_theme()
        else:
            self._apply_system_theme()
    
    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        dark_palette = QPalette()
        
        # Window colors
        dark_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.darkGray)
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        
        # Base colors
        dark_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.black)
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, Qt.GlobalColor.darkGray)
        
        # Text colors
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        
        # Button colors
        dark_palette.setColor(QPalette.ColorRole.Button, Qt.GlobalColor.darkGray)
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        
        # Highlight colors
        dark_palette.setColor(QPalette.ColorRole.Highlight, Qt.GlobalColor.darkBlue)
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        self.setPalette(dark_palette)
    
    def _apply_light_theme(self):
        """Apply light theme styling."""
        light_palette = QPalette()
        
        # Use default light palette
        self.setPalette(QApplication.style().standardPalette())
    
    def _apply_system_theme(self):
        """Apply system default theme."""
        self.setPalette(QApplication.style().standardPalette())
    
    def _restore_settings(self):
        """Restore window settings from previous session."""
        # Window geometry
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        
        # Window state
        state = self.settings.value('windowState')
        if state:
            self.restoreState(state)
    
    def _save_settings(self):
        """Save window settings for next session."""
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.sync()
    
    def _update_status_display(self):
        """Update status bar information."""
        # Update status label
        self.status_label.setText(self.current_status)
    
    # Menu action handlers
    
    def _import_urls(self):
        """Handle import URLs action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Import URLs',
            '',
            'Text files (*.txt);;All files (*.*)'
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                # Process each URL
                for url in urls:
                    if url.startswith(('http://', 'https://')):
                        self.url_requested.emit(url)
                
                self.set_status(f"Imported {len(urls)} URLs")
                
            except Exception as e:
                QMessageBox.warning(self, 'Import Error', f'Failed to import URLs: {str(e)}')
    
    
    def _open_settings(self):
        """Handle settings action."""
        from gui.dialogs import SettingsDialog
        
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_status("Settings saved successfully")
            # Reload settings to apply changes
            self._load_settings()
        else:
            self.set_status("Settings dialog cancelled")
    
    def _manage_dependencies(self):
        """Handle manage dependencies action."""
        # This will open dependency management dialog
        self.set_status("Dependency management dialog not yet implemented")
    
    def _clear_cache(self):
        """Handle clear cache action."""
        reply = QMessageBox.question(
            self,
            'Clear Cache',
            'Are you sure you want to clear all cached data?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cache_dir = self.app_root / "cache"
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir()
                
                self.set_status("Cache cleared successfully")
                
            except Exception as e:
                QMessageBox.warning(self, 'Clear Cache Error', f'Failed to clear cache: {str(e)}')
    
    def _open_downloads_folder(self):
        """Handle open downloads folder action."""
        # Use the tool's downloads folder (same as utility function)
        downloads_path = self.app_root / "downloads"
        
        # Ensure downloads folder exists
        downloads_path.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"Opening downloads folder from menu: {downloads_path}")
            if sys.platform == 'win32':
                os.startfile(str(downloads_path))
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.call(['open', str(downloads_path)])
            else:
                import subprocess
                subprocess.call(['xdg-open', str(downloads_path)])
        except Exception as e:
            print(f"Error opening downloads folder: {e}")
            QMessageBox.warning(self, 'Open Folder Error', f'Failed to open downloads folder: {str(e)}')
    
    def _change_theme(self, theme: str):
        """Handle theme change."""
        self.config['app']['theme'] = theme
        self._apply_styling()
        self.settings_changed.emit(self.config)
        self.set_status(f"Theme changed to {theme}")
    
    def _toggle_status_bar(self):
        """Handle status bar toggle."""
        self.status_bar.setVisible(not self.status_bar.isVisible())
    
    def _show_about(self):
        """Handle about action."""
        QMessageBox.about(
            self,
            'About YouTube Downloader GUI',
            f'''
            <h3>{self.config['app']['name']}</h3>
            <p>Version {self.config['app']['version']}</p>
            <p>A portable YouTube video downloader with embedded dependencies.</p>
            <p>Built with PyQt6 and yt-dlp.</p>
            <p>No system dependencies required!</p>
            '''
        )
    
    def _show_help(self):
        """Handle help action."""
        help_text = '''
        <h3>YouTube Downloader GUI Help</h3>
        
        <h4>Getting Started:</h4>
        <ol>
        <li>Paste a YouTube URL in the input field</li>
        <li>Select your preferred quality and format</li>
        <li>Choose download location</li>
        <li>Click Download to start</li>
        </ol>
        
        <h4>Supported URLs:</h4>
        <ul>
        <li>YouTube videos</li>
        <li>YouTube playlists</li>
        <li>YouTube shorts</li>
        </ul>
        
        <h4>Features:</h4>
        <ul>
        <li>Real-time video preview</li>
        <li>Multiple quality options</li>
        <li>Audio-only downloads</li>
        <li>Progress tracking</li>
        <li>Completely portable</li>
        </ul>
        '''
        
        QMessageBox.information(self, 'Help', help_text)
    
    # Public interface methods
    def set_status(self, message: str):
        """
        Set status bar message.
        
        Args:
            message: Status message to display
        """
        self.current_status = message
        print(f"Status: {message}")
    
    def set_download_count(self, total: int, active: int = 0):
        """
        Update download counters.
        
        Args:
            total: Total number of downloads
            active: Number of active downloads
        """
        self.download_count = total
        self.active_downloads = active
    
    def set_progress(self, percentage: float, visible: bool = True):
        """
        Update status bar progress.
        
        Args:
            percentage: Progress percentage (0-100)
            visible: Whether progress bar should be visible
        """
        self.status_progress.setVisible(visible)
        if visible:
            self.status_progress.setValue(int(percentage))
    
    def add_preview_panel(self, panel_widget: QWidget):
        """
        Add preview panel to the window.
        
        Args:
            panel_widget: Preview panel widget to add
        """
        # Clear existing content
        for i in reversed(range(self.preview_layout.count())):
            self.preview_layout.itemAt(i).widget().setParent(None)
        
        # Add new panel
        self.preview_layout.addWidget(panel_widget)
        self.preview_panel = panel_widget
        print("Preview panel added to main window")
    
    def add_controls_panel(self, panel_widget: QWidget):
        """
        Add controls panel to the window.
        
        Args:
            panel_widget: Controls panel widget to add
        """
        # Clear existing content
        for i in reversed(range(self.controls_layout.count())):
            self.controls_layout.itemAt(i).widget().setParent(None)
        
        # Add new panel
        self.controls_layout.addWidget(panel_widget)
        self.controls_panel = panel_widget
        print("Controls panel added to main window")
    
    # Event handlers
    def dragEnterEvent(self, event):
        """Handle drag enter events for URL drops."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop events for URL drops."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                url_string = url.toString()
                if 'youtube.com' in url_string or 'youtu.be' in url_string:
                    self.url_requested.emit(url_string)
                    break
        elif event.mimeData().hasText():
            text = event.mimeData().text()
            if 'youtube.com' in text or 'youtu.be' in text:
                self.url_requested.emit(text)
    
    def closeEvent(self, event):
        """Handle window close events."""
        # Save settings
        self._save_settings()
        
        # Ask user to confirm if downloads are active
        if self.active_downloads > 0:
            reply = QMessageBox.question(
                self,
                'Active Downloads',
                f'There are {self.active_downloads} active downloads. Are you sure you want to exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Accept close event
        event.accept()
        print("Main window closed")
    
    def set_downloader(self, downloader):
        """Set the YouTube downloader instance."""
        self.downloader = downloader
        print("Downloader set in main window")
    
    def set_progress_manager(self, progress_manager):
        """Set the progress manager instance."""
        self.progress_manager = progress_manager
        print("Progress manager set in main window")
    
    def set_worker_manager(self, worker_manager):
        """Set the worker manager instance."""
        self.worker_manager = worker_manager
        print("Worker manager set in main window")
    
    def set_dependency_manager(self, dependency_manager):
        """Set the dependency manager instance."""
        self.dependency_manager = dependency_manager
        print("Dependency manager set in main window")
    
    def _setup_preview_panel(self, layout):
        """Setup the video preview panel with thumbnail and metadata."""
        # Preview title
        preview_title = QLabel("Video Preview")
        preview_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(preview_title)
        
        # Thumbnail display - YouTube standard size is 320x180
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)  # YouTube's default thumbnail size
        self.thumbnail_label.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0; color: black;")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("Paste YouTube URL to see preview")
        layout.addWidget(self.thumbnail_label)
        
        # Video info panel
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_frame.setFixedWidth(320)  # Match video preview width
        info_layout = QVBoxLayout(info_frame)
        
        # Title
        self.video_title = QLabel("Video Title")
        self.video_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.video_title.setWordWrap(True)
        self.video_title.setFixedHeight(40)
        self.video_title.setFixedWidth(320)  # Match video preview width
        info_layout.addWidget(self.video_title)
        
        # Channel and duration
        metadata_layout = QHBoxLayout()
        self.channel_label = QLabel("Channel: Unknown")
        self.duration_label = QLabel("Duration: Unknown")
        metadata_layout.addWidget(self.channel_label)
        metadata_layout.addWidget(self.duration_label)
        info_layout.addLayout(metadata_layout)
        
        # View count and upload date
        stats_layout = QHBoxLayout()
        self.views_label = QLabel("Views: Unknown")
        self.upload_label = QLabel("Uploaded: Unknown")
        stats_layout.addWidget(self.views_label)
        stats_layout.addWidget(self.upload_label)
        info_layout.addLayout(stats_layout)
        
        layout.addWidget(info_frame)
        
        # Status label for preview loading
        self.preview_status = QLabel("Ready")
        self.preview_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.preview_status)
        
        layout.addStretch()
    
    def _setup_controls_panel(self, layout):
        """Setup the download controls panel."""
        # URL input section
        url_group = QFrame()
        url_group.setFrameStyle(QFrame.Shape.StyledPanel)
        url_layout = QVBoxLayout(url_group)
        
        url_layout.addWidget(QLabel("YouTube URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here...")
        self.url_input.textChanged.connect(self._on_url_changed)
        url_layout.addWidget(self.url_input)
        
        layout.addWidget(url_group)
        
        # Quality selection
        quality_group = QFrame()
        quality_group.setFrameStyle(QFrame.Shape.StyledPanel)
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.addWidget(QLabel("Video Quality:"))
        
        self.quality_best = QRadioButton("Best Quality")
        self.quality_1080 = QRadioButton("1080p Max")
        self.quality_720 = QRadioButton("720p Max")
        self.quality_480 = QRadioButton("480p Max")
        self.quality_best.setChecked(True)
        
        for radio in [self.quality_best, self.quality_1080, self.quality_720, self.quality_480]:
            quality_layout.addWidget(radio)
        
        layout.addWidget(quality_group)
        
        # Download buttons
        button_group = QFrame()
        button_group.setFrameStyle(QFrame.Shape.StyledPanel)
        button_layout = QVBoxLayout(button_group)
        button_layout.addWidget(QLabel("Download Options:"))
        
        button_row = QHBoxLayout()
        self.audio_button = QPushButton("Download Audio (MP3)")
        self.video_button = QPushButton("Download Video (MP4)")
        self.audio_button.clicked.connect(self._download_audio)
        self.video_button.clicked.connect(self._download_video)
        self.audio_button.setEnabled(False)
        self.video_button.setEnabled(False)
        
        button_row.addWidget(self.audio_button)
        button_row.addWidget(self.video_button)
        button_layout.addLayout(button_row)
        
        layout.addWidget(button_group)
        
        # Progress section
        progress_group = QFrame()
        progress_group.setFrameStyle(QFrame.Shape.StyledPanel)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.addWidget(QLabel("Download Progress:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        layout.addStretch()
    
    def _on_url_changed(self):
        """Handle URL input changes."""
        url = self.url_input.text().strip()
        if url and len(url) > 10:
            # Basic YouTube URL validation
            if 'youtube.com/watch' in url or 'youtu.be/' in url:
                # Enable download buttons immediately for valid URLs
                self.audio_button.setEnabled(True)
                self.video_button.setEnabled(True)
                
                # Load video info for preview (independent of download buttons)
                self.preview_status.setText("Loading video info...")
                self._fetch_video_info(url)
            else:
                self.preview_status.setText("Please enter a valid YouTube URL")
                self.audio_button.setEnabled(False)
                self.video_button.setEnabled(False)
        else:
            self.preview_status.setText("Ready")
            self.audio_button.setEnabled(False)
            self.video_button.setEnabled(False)
    
    def _download_audio(self):
        """Handle audio download."""
        url = self.url_input.text().strip()
        if not url:
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting audio download...")
        
        try:
            # Use embedded yt-dlp for download
            self._start_download(url, "audio")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start audio download:\n{str(e)}")
            self.progress_bar.setVisible(False)
    
    def _download_video(self):
        """Handle video download."""
        url = self.url_input.text().strip()
        if not url:
            return
        
        # Get selected quality
        quality = "best"
        if self.quality_1080.isChecked():
            quality = "1080p"
        elif self.quality_720.isChecked():
            quality = "720p"
        elif self.quality_480.isChecked():
            quality = "480p"
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Starting video download ({quality})...")
        
        try:
            # Use embedded yt-dlp for download
            self._start_download(url, "video", quality)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start video download:\n{str(e)}")
            self.progress_bar.setVisible(False)
    
    def _start_download(self, url: str, download_type: str, quality: str = "best"):
        """Start the download process using yt-dlp."""
        import yt_dlp
        from pathlib import Path
        import os
        
        # Set up download directory using configured path
        downloads_dir = self._get_configured_download_path()
        downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Debug print to verify path
        print(f"DEBUG: Using download directory: {downloads_dir}")
        print(f"DEBUG: Full absolute path: {downloads_dir.resolve()}")
        print(f"DEBUG: Directory exists: {downloads_dir.exists()}")
        print(f"DEBUG: Directory is writable: {os.access(downloads_dir, os.W_OK)}")
        
        # Configure yt-dlp options
        output_template = str(downloads_dir / '%(title)s.%(ext)s')
        print(f"DEBUG: yt-dlp output template: {output_template}")
        
        if download_type == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'outtmpl': output_template,
                'progress_hooks': [self._progress_hook],
            }
        else:  # video
            format_map = {
                "best": "best[ext=mp4]/best",
                "1080p": "best[height<=1080][ext=mp4]/best[height<=1080]/best",
                "720p": "best[height<=720][ext=mp4]/best[height<=720]/best", 
                "480p": "best[height<=480][ext=mp4]/best[height<=480]/best"
            }
            ydl_opts = {
                'format': format_map.get(quality, format_map["best"]),
                'outtmpl': output_template,
                'progress_hooks': [self._progress_hook],
            }
        
        print(f"DEBUG: Complete yt-dlp options: {ydl_opts}")
        
        # Start download in a separate thread
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class DownloadWorker(QThread):
            download_complete = pyqtSignal(str)
            download_error = pyqtSignal(str)
            
            def __init__(self, url, opts):
                super().__init__()
                self.url = url
                self.opts = opts
                
            def run(self):
                try:
                    with yt_dlp.YoutubeDL(self.opts) as ydl:
                        ydl.download([self.url])
                    self.download_complete.emit("Download completed successfully!")
                except Exception as e:
                    self.download_error.emit(str(e))
        
        # Create and start worker
        self.download_worker = DownloadWorker(url, ydl_opts)
        self.download_worker.download_complete.connect(self._on_download_complete)
        self.download_worker.download_error.connect(self._on_download_error)
        self.download_worker.start()
        
        # Disable buttons during download
        self.audio_button.setEnabled(False)
        self.video_button.setEnabled(False)
    
    def _progress_hook(self, d):
        """Handle download progress updates from yt-dlp."""
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                self.progress_bar.setValue(progress)
                self.progress_label.setText(f"Downloading... {progress}%")
            elif '_percent_str' in d:
                # Extract percentage from string
                percent_str = d['_percent_str'].strip().replace('%', '')
                try:
                    progress = int(float(percent_str))
                    self.progress_bar.setValue(progress)
                    self.progress_label.setText(f"Downloading... {progress}%")
                except:
                    self.progress_label.setText("Downloading...")
        elif d['status'] == 'finished':
            self.progress_bar.setValue(100)
            self.progress_label.setText("Processing...")
    
    def _on_download_complete(self, message):
        """Handle successful download completion."""
        self.progress_bar.setValue(100)
        self.progress_label.setText("Download completed!")
        self.audio_button.setEnabled(True) 
        self.video_button.setEnabled(True)
        
        # Update download counter (removed from status bar)
        self.download_count += 1
        
        # Show custom success dialog with download path and folder button
        downloads_path = self._get_configured_download_path()
        
        # Create custom message box with Show Folder button
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Download Complete")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("Download completed successfully!")
        msg_box.setInformativeText(f"File saved to:\n{downloads_path}")
        
        # Style the message box for proper layout
        msg_box.setStyleSheet("""
            QMessageBox {
                min-width: 400px;
                max-width: 500px;
            }
            QLabel {
                max-width: 450px;
                word-wrap: true;
            }
        """)
        
        # Add custom buttons
        show_folder_button = msg_box.addButton("Show Folder", QMessageBox.ButtonRole.ActionRole)
        ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        # Execute dialog and handle button clicks
        msg_box.exec()
        
        # Check which button was clicked
        if msg_box.clickedButton() == show_folder_button:
            self._open_downloads_folder_utility()
        
        # Hide progress bar after a delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))
    
    def _get_configured_download_path(self):
        """Get the configured download path from settings."""
        settings = QSettings('YTDownloaderGUI', 'Settings')
        
        print(f"DEBUG: _get_configured_download_path() called")
        
        # Check QSettings first
        configured_path = settings.value("default_download_path", "")
        print(f"DEBUG: QSettings path: '{configured_path}'")
        if configured_path:
            path = Path(configured_path)
            path.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Using QSettings path: {path}")
            return path
        
        # Check JSON config file
        try:
            config_file = self.app_root / "config" / "app_config.json"
            print(f"DEBUG: Checking config file: {config_file}")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    config_path = config.get("downloads", {}).get("default_path", "")
                    print(f"DEBUG: Config file path: '{config_path}'")
                    if config_path:
                        if config_path.startswith("~/"):
                            # On Windows, use the proper Windows user directory
                            if sys.platform == 'win32':
                                config_path = str(Path.home() / config_path[2:])
                            else:
                                # If running in WSL or from Windows Python, use Windows user directory
                                windows_user = os.environ.get('USERPROFILE')
                                if windows_user:
                                    config_path = str(Path(windows_user) / config_path[2:])
                                else:
                                    config_path = str(Path.home() / config_path[2:])
                            print(f"DEBUG: Expanded ~ path: {config_path}")
                        path = Path(config_path)
                        path.mkdir(parents=True, exist_ok=True)
                        print(f"DEBUG: Using config file path: {path}")
                        return path
        except Exception as e:
            print(f"DEBUG: Config file error: {e}")
        
        # Fall back to user's Downloads folder, then app downloads folder
        try:
            # Use Windows user directory if available
            if sys.platform == 'win32':
                downloads_path = Path.home() / "Downloads"
            else:
                windows_user = os.environ.get('USERPROFILE')
                if windows_user:
                    downloads_path = Path(windows_user) / "Downloads"
                else:
                    downloads_path = Path.home() / "Downloads"
            
            downloads_path.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Using fallback Downloads path: {downloads_path}")
            return downloads_path
        except Exception as e:
            print(f"DEBUG: Downloads fallback error: {e}")
            # Final fallback to app directory
            default_path = self.app_root / "downloads"
            default_path.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Using final fallback path: {default_path}")
            return default_path
    
    def _load_settings(self):
        """Load application settings."""
        # This method is called after settings are changed
        # You can add any settings reload logic here
        pass
    
    def _on_download_error(self, error_message):
        """Handle download errors."""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Download failed")
        self.audio_button.setEnabled(True)
        self.video_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", f"Download failed:\n{error_message}")
    
    def _fetch_video_info(self, url: str):
        """Fetch video information for preview."""
        from PyQt6.QtCore import QThread, pyqtSignal
        import yt_dlp
        
        class VideoInfoWorker(QThread):
            info_ready = pyqtSignal(dict)
            info_error = pyqtSignal(str)
            thumbnail_ready = pyqtSignal(str)  # Signal for thumbnail path
            
            def __init__(self, url):
                super().__init__()
                self.url = url
                
            def run(self):
                try:
                    print(f"DEBUG: Fetching video info for URL: {self.url}")
                    ydl_opts = {
                        'quiet': False,  # Enable output to see what's happening
                        'no_warnings': False,
                        'skip_download': True,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        print("DEBUG: Calling extract_info...")
                        info = ydl.extract_info(self.url, download=False)
                        print(f"DEBUG: Info extracted successfully, title: {info.get('title', 'Unknown')}")
                        
                        # Extract relevant info
                        video_info = {
                            'title': info.get('title', 'Unknown Title'),
                            'uploader': info.get('uploader', 'Unknown Channel'),
                            'duration_string': info.get('duration_string', 'Unknown'),
                            'view_count': info.get('view_count', 0),
                            'upload_date': info.get('upload_date', 'Unknown'),
                            'description': info.get('description', '')[:200] + '...' if info.get('description') else 'No description',
                            'thumbnail': info.get('thumbnail', None)
                        }
                        
                        print(f"DEBUG: Emitting info_ready signal with data: {video_info}")
                        self.info_ready.emit(video_info)
                        
                        # Download thumbnail if available
                        thumbnail_url = video_info.get('thumbnail')
                        if thumbnail_url:
                            try:
                                import requests
                                import tempfile
                                import os
                                
                                print(f"DEBUG: Downloading thumbnail from: {thumbnail_url}")
                                response = requests.get(thumbnail_url, timeout=10)
                                if response.status_code == 200:
                                    # Save thumbnail to temp directory
                                    temp_dir = tempfile.gettempdir()
                                    thumbnail_path = os.path.join(temp_dir, f"yt_thumbnail_{hash(self.url)}.jpg")
                                    
                                    with open(thumbnail_path, 'wb') as f:
                                        f.write(response.content)
                                    
                                    print(f"DEBUG: Thumbnail saved to: {thumbnail_path}")
                                    self.thumbnail_ready.emit(thumbnail_path)
                                else:
                                    print(f"DEBUG: Failed to download thumbnail, status: {response.status_code}")
                            except Exception as thumb_error:
                                print(f"DEBUG: Error downloading thumbnail: {str(thumb_error)}")
                        
                except Exception as e:
                    print(f"DEBUG: Error in video info extraction: {str(e)}")
                    self.info_error.emit(str(e))
        
        # Create and start worker
        self.info_worker = VideoInfoWorker(url)
        self.info_worker.info_ready.connect(self._on_video_info_ready)
        self.info_worker.info_error.connect(self._on_video_info_error)
        self.info_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.info_worker.start()
    
    def _on_video_info_ready(self, info):
        """Handle successful video info extraction."""
        print(f"DEBUG: _on_video_info_ready called with info: {info}")
        self.video_title.setText(info['title'])
        self.channel_label.setText(f"Channel: {info['uploader']}")
        self.duration_label.setText(f"Duration: {info['duration_string']}")
        
        # Format view count
        views = info['view_count']
        if views >= 1000000:
            view_text = f"{views/1000000:.1f}M views"
        elif views >= 1000:
            view_text = f"{views/1000:.1f}K views"
        else:
            view_text = f"{views} views"
        self.views_label.setText(view_text)
        
        # Format upload date
        upload_date = info['upload_date']
        if len(upload_date) == 8:  # YYYYMMDD format
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            self.upload_label.setText(f"Uploaded: {formatted_date}")
        else:
            self.upload_label.setText(f"Uploaded: {upload_date}")
        
        self.preview_status.setText("Video info loaded")
        print("DEBUG: Video info UI updated successfully")
    
    def _on_video_info_error(self, error):
        """Handle video info extraction errors."""
        print(f"DEBUG: _on_video_info_error called with error: {error}")
        self.preview_status.setText("Failed to load video info")
        self.video_title.setText("Failed to load video information")
        self.channel_label.setText("Channel: Unknown")
        self.duration_label.setText("Duration: Unknown")
        self.views_label.setText("Views: Unknown")
        self.upload_label.setText("Uploaded: Unknown")
        
        # Download buttons remain enabled since they work independently
    
    def _open_downloads_folder_utility(self):
        """Open the downloads folder in the system file manager."""
        downloads_path = self._get_configured_download_path()
        
        # Ensure downloads folder exists
        downloads_path.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"DEBUG: Opening downloads folder: {downloads_path}")
            if sys.platform == 'win32':
                os.startfile(str(downloads_path))
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.call(['open', str(downloads_path)])
            else:
                import subprocess
                subprocess.call(['xdg-open', str(downloads_path)])
        except Exception as e:
            print(f"Error opening downloads folder: {e}")
            QMessageBox.warning(self, 'Open Folder Error', f'Failed to open downloads folder: {str(e)}')
    
    def _on_thumbnail_ready(self, thumbnail_path):
        """Handle successful thumbnail download."""
        try:
            print(f"DEBUG: _on_thumbnail_ready called with path: {thumbnail_path}")
            
            # Load and display thumbnail
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                # Scale pixmap to fit the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail_label.setPixmap(scaled_pixmap)
                self.thumbnail_label.setText("")  # Clear placeholder text
                print("DEBUG: Thumbnail displayed successfully")
            else:
                print("DEBUG: Failed to load thumbnail pixmap")
                self.thumbnail_label.setText("Failed to load thumbnail")
                
        except Exception as e:
            print(f"DEBUG: Error displaying thumbnail: {str(e)}")
            self.thumbnail_label.setText("Error loading thumbnail")