"""
Video preview panel for YouTube Downloader GUI.

This module provides the preview panel that displays video thumbnails,
metadata, and loading states when URLs are processed.
"""

import sys
import os
import requests
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
        QScrollArea, QProgressBar, QTextEdit, QGroupBox, QSizePolicy
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QSize
    from PyQt6.QtGui import QPixmap, QFont, QPalette, QMovie
except ImportError as e:
    print(f"PyQt6 not available: {e}")
    print("Run setup.py to install dependencies.")
    sys.exit(1)

from ..downloader.validation import VideoInfo

logger = logging.getLogger(__name__)


class ThumbnailLabel(QLabel):
    """
    Custom QLabel for displaying video thumbnails with loading states.
    
    Supports loading animations, error states, and proper scaling.
    """
    
    def __init__(self):
        """Initialize thumbnail label."""
        super().__init__()
        
        # Setup properties
        self.setMinimumSize(300, 200)
        self.setMaximumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 8px;
                background-color: #f5f5f5;
                padding: 10px;
            }
        """)
        
        # Loading animation
        self.loading_movie = None
        self._setup_loading_animation()
        
        # Default state
        self.show_placeholder()
    
    def _setup_loading_animation(self):
        """Setup loading animation for thumbnail."""
        # Create a simple loading animation
        # In a real implementation, you'd use a GIF or create animated frames
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading)
        self.loading_dots = 0
    
    def show_placeholder(self):
        """Show placeholder when no video is loaded."""
        self.clear()
        self.setText("📺\n\nPaste a YouTube URL to see video preview")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                background-color: #f9f9f9;
                color: #888888;
                font-size: 14px;
                padding: 20px;
            }
        """)
    
    def show_loading(self):
        """Show loading state."""
        self.clear()
        self.setText("🔄 Loading video preview...")
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #e8f5e8;
                color: #2e7d2e;
                font-size: 14px;
                padding: 20px;
            }
        """)
        
        # Start loading animation
        self.loading_timer.start(500)
        self.loading_dots = 0
    
    def show_error(self, error_message: str):
        """Show error state."""
        self.clear()
        self.loading_timer.stop()
        self.setText(f"❌ Error loading preview\n\n{error_message}")
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #f44336;
                border-radius: 8px;
                background-color: #ffebee;
                color: #c62828;
                font-size: 12px;
                padding: 20px;
            }
        """)
    
    def show_thumbnail(self, thumbnail_path: Path):
        """
        Show video thumbnail.
        
        Args:
            thumbnail_path: Path to thumbnail image file
        """
        self.loading_timer.stop()
        
        try:
            pixmap = QPixmap(str(thumbnail_path))
            
            if pixmap.isNull():
                self.show_error("Failed to load thumbnail image")
                return
            
            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.setPixmap(scaled_pixmap)
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    background-color: white;
                    padding: 5px;
                }
            """)
            
        except Exception as e:
            logger.error(f"Error displaying thumbnail: {e}")
            self.show_error(f"Display error: {str(e)}")
    
    def _update_loading(self):
        """Update loading animation."""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.setText(f"🔄 Loading video preview{dots}")


class VideoInfoWidget(QWidget):
    """
    Widget for displaying detailed video information.
    
    Shows title, description, duration, channel info, and other metadata.
    """
    
    def __init__(self):
        """Initialize video info widget."""
        super().__init__()
        
        self.video_info = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel("No video selected")
        self.title_label.setWordWrap(True)
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #333333; padding: 5px;")
        layout.addWidget(self.title_label)
        
        # Basic info group
        info_group = QGroupBox("Video Information")
        info_layout = QVBoxLayout(info_group)
        
        # Duration and views row
        stats_layout = QHBoxLayout()
        
        self.duration_label = QLabel("Duration: --")
        self.duration_label.setStyleSheet("color: #666666;")
        stats_layout.addWidget(self.duration_label)
        
        stats_layout.addStretch()
        
        self.views_label = QLabel("Views: --")
        self.views_label.setStyleSheet("color: #666666;")
        stats_layout.addWidget(self.views_label)
        
        info_layout.addLayout(stats_layout)
        
        # Channel info
        self.channel_label = QLabel("Channel: --")
        self.channel_label.setStyleSheet("color: #666666; font-weight: bold;")
        info_layout.addWidget(self.channel_label)
        
        # Upload date
        self.upload_date_label = QLabel("Uploaded: --")
        self.upload_date_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(self.upload_date_label)
        
        layout.addWidget(info_group)
        
        # Quality info group
        quality_group = QGroupBox("Available Qualities")
        quality_layout = QVBoxLayout(quality_group)
        
        self.quality_label = QLabel("No quality information available")
        self.quality_label.setWordWrap(True)
        self.quality_label.setStyleSheet("color: #666666;")
        quality_layout.addWidget(self.quality_label)
        
        layout.addWidget(quality_group)
        
        # Description group
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(100)
        self.description_text.setReadOnly(True)
        self.description_text.setPlainText("No description available")
        self.description_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #fafafa;
                color: #333333;
                font-size: 11px;
            }
        """)
        desc_layout.addWidget(self.description_text)
        
        layout.addWidget(desc_group)
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def update_video_info(self, video_info: VideoInfo):
        """
        Update displayed video information.
        
        Args:
            video_info: VideoInfo object with metadata
        """
        self.video_info = video_info
        
        # Update title
        self.title_label.setText(video_info.title or "Unknown Title")
        
        # Update duration
        if video_info.duration_string:
            self.duration_label.setText(f"Duration: {video_info.duration_string}")
        elif video_info.duration:
            self.duration_label.setText(f"Duration: {video_info.duration}s")
        else:
            self.duration_label.setText("Duration: Unknown")
        
        # Update views
        if video_info.view_count:
            views_formatted = self._format_number(video_info.view_count)
            self.views_label.setText(f"Views: {views_formatted}")
        else:
            self.views_label.setText("Views: --")
        
        # Update channel
        channel = video_info.channel or video_info.uploader or "Unknown Channel"
        self.channel_label.setText(f"Channel: {channel}")
        
        # Update upload date
        if video_info.upload_date:
            # Format YYYYMMDD to readable date
            try:
                year = video_info.upload_date[:4]
                month = video_info.upload_date[4:6]
                day = video_info.upload_date[6:8]
                formatted_date = f"{year}-{month}-{day}"
                self.upload_date_label.setText(f"Uploaded: {formatted_date}")
            except:
                self.upload_date_label.setText(f"Uploaded: {video_info.upload_date}")
        else:
            self.upload_date_label.setText("Uploaded: --")
        
        # Update quality info
        if video_info.available_qualities:
            qualities = ", ".join(video_info.available_qualities[:8])  # Show first 8
            if len(video_info.available_qualities) > 8:
                qualities += f" (+{len(video_info.available_qualities) - 8} more)"
            self.quality_label.setText(f"Available: {qualities}")
        else:
            self.quality_label.setText("No quality information available")
        
        # Update description
        if video_info.description:
            # Truncate long descriptions
            desc = video_info.description
            if len(desc) > 500:
                desc = desc[:500] + "..."
            self.description_text.setPlainText(desc)
        else:
            self.description_text.setPlainText("No description available")
    
    def clear_info(self):
        """Clear all displayed information."""
        self.video_info = None
        self.title_label.setText("No video selected")
        self.duration_label.setText("Duration: --")
        self.views_label.setText("Views: --")
        self.channel_label.setText("Channel: --")
        self.upload_date_label.setText("Uploaded: --")
        self.quality_label.setText("No quality information available")
        self.description_text.setPlainText("No description available")
    
    def _format_number(self, num: int) -> str:
        """
        Format large numbers with K, M, B suffixes.
        
        Args:
            num: Number to format
            
        Returns:
            Formatted number string
        """
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)


class PreviewPanel(QWidget):
    """
    Main preview panel widget for displaying video information.
    
    Combines thumbnail display and video information in a scrollable layout.
    Integrates with the main window and handles preview updates.
    """
    
    # Signals
    thumbnail_loaded = pyqtSignal(str)  # Emitted when thumbnail is loaded
    info_updated = pyqtSignal(VideoInfo)  # Emitted when video info is updated
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    
    def __init__(self, app_root: Path):
        """
        Initialize preview panel.
        
        Args:
            app_root: Root directory of the application
        """
        super().__init__()
        
        self.app_root = Path(app_root)
        self.cache_dir = self.app_root / "cache" / "previews"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_video_info = None
        self.current_url = None
        
        self._setup_ui()
        
        logger.info("Preview panel initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Video Preview")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333; padding: 5px;")
        layout.addWidget(title_label)
        
        # Thumbnail display
        self.thumbnail_widget = ThumbnailLabel()
        layout.addWidget(self.thumbnail_widget)
        
        # Scroll area for video info
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Video info widget
        self.info_widget = VideoInfoWidget()
        scroll_area.setWidget(self.info_widget)
        
        layout.addWidget(scroll_area)
        
        # Set layout stretch factors
        layout.setStretchFactor(self.thumbnail_widget, 0)  # Fixed size
        layout.setStretchFactor(scroll_area, 1)  # Expandable
    
    @pyqtSlot(VideoInfo)
    def update_preview(self, video_info: VideoInfo):
        """
        Update preview with new video information.
        
        Args:
            video_info: VideoInfo object containing metadata
        """
        try:
            self.current_video_info = video_info
            self.current_url = str(video_info.url)
            
            # Update video info display
            self.info_widget.update_video_info(video_info)
            
            # Download and display thumbnail
            if video_info.thumbnail:
                self._download_thumbnail(str(video_info.thumbnail), video_info.id)
            else:
                self.thumbnail_widget.show_error("No thumbnail available")
            
            # Emit signal
            self.info_updated.emit(video_info)
            
            logger.info(f"Updated preview for: {video_info.title}")
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.show_error(f"Preview update failed: {str(e)}")
    
    def show_loading(self):
        """Show loading state for preview."""
        self.thumbnail_widget.show_loading()
        self.info_widget.clear_info()
    
    def show_error(self, error_message: str):
        """
        Show error state in preview.
        
        Args:
            error_message: Error message to display
        """
        self.thumbnail_widget.show_error(error_message)
        self.info_widget.clear_info()
        self.error_occurred.emit(error_message)
    
    def clear_preview(self):
        """Clear preview and return to placeholder state."""
        self.current_video_info = None
        self.current_url = None
        self.thumbnail_widget.show_placeholder()
        self.info_widget.clear_info()
    
    def _download_thumbnail(self, thumbnail_url: str, video_id: str):
        """
        Download and cache video thumbnail.
        
        Args:
            thumbnail_url: URL of the thumbnail image
            video_id: Video ID for cache naming
        """
        try:
            # Check if thumbnail is already cached
            cache_path = self.cache_dir / f"{video_id}.jpg"
            
            if cache_path.exists():
                self.thumbnail_widget.show_thumbnail(cache_path)
                self.thumbnail_loaded.emit(str(cache_path))
                return
            
            # Download thumbnail
            self.thumbnail_widget.show_loading()
            
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            # Display thumbnail
            self.thumbnail_widget.show_thumbnail(cache_path)
            self.thumbnail_loaded.emit(str(cache_path))
            
            logger.info(f"Downloaded thumbnail for video: {video_id}")
            
        except requests.RequestException as e:
            logger.error(f"Failed to download thumbnail: {e}")
            self.thumbnail_widget.show_error(f"Thumbnail download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing thumbnail: {e}")
            self.thumbnail_widget.show_error(f"Thumbnail error: {str(e)}")
    
    def get_current_video_info(self) -> Optional[VideoInfo]:
        """
        Get current video information.
        
        Returns:
            Current VideoInfo object or None
        """
        return self.current_video_info
    
    def get_current_url(self) -> Optional[str]:
        """
        Get current video URL.
        
        Returns:
            Current video URL or None
        """
        return self.current_url
    
    def cleanup_cache(self):
        """Clean up old cached thumbnails."""
        try:
            import time
            
            # Remove cache files older than 24 hours
            cutoff_time = time.time() - (24 * 60 * 60)
            
            for cache_file in self.cache_dir.glob("*.jpg"):
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    logger.info(f"Removed old cache file: {cache_file.name}")
            
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    def get_cache_size(self) -> int:
        """
        Get total size of cached thumbnails.
        
        Returns:
            Total cache size in bytes
        """
        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.jpg"):
                total_size += cache_file.stat().st_size
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
        
        return total_size