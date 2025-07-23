"""
QThread worker classes for background processing in YouTube Downloader GUI.

This module provides QThread-based workers for non-blocking operations
including video preview generation, thumbnail downloading, and video downloads.
All workers use thread-safe signals for communication with the main GUI thread.
"""

import sys
import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject, QMutex, QWaitCondition
    from PyQt6.QtGui import QPixmap
    import requests
    from PIL import Image
    from io import BytesIO
except ImportError as e:
    print(f"Required packages not available: {e}")
    print("Run setup.py to install dependencies.")
    sys.exit(1)

from downloader.core import YouTubeDownloader
from downloader.validation import VideoInfo, DownloadRequest, ProgressInfo
from downloader.progress import ProgressManager

logger = logging.getLogger(__name__)


class VideoPreviewWorker(QThread):
    """
    Worker thread for fetching video preview information and thumbnails.
    
    Handles video metadata extraction and thumbnail downloading in background
    without blocking the main GUI thread.
    """
    
    # Signals for thread-safe communication
    preview_ready = pyqtSignal(VideoInfo, QPixmap)  # Video info + thumbnail
    preview_failed = pyqtSignal(str)  # Error message
    progress_update = pyqtSignal(str)  # Status message
    
    def __init__(self, downloader: YouTubeDownloader, cache_dir: Path, parent: QObject = None):
        """
        Initialize video preview worker.
        
        Args:
            downloader: YouTubeDownloader instance for metadata extraction
            cache_dir: Directory for thumbnail caching
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.downloader = downloader
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread control
        self._stop_requested = False
        self._mutex = QMutex()
        
        # Current task
        self.current_url: Optional[str] = None
        
    def set_url(self, url: str):
        """Set the URL to process for video preview."""
        with self._mutex:
            self.current_url = url
            self._stop_requested = False
    
    def stop(self):
        """Request worker to stop current operation."""
        with self._mutex:
            self._stop_requested = True
        
        # Wait for thread to finish with timeout
        if not self.wait(3000):  # 3 second timeout
            logger.warning("VideoPreviewWorker did not stop gracefully")
            self.terminate()
    
    def run(self):
        """Main worker thread execution."""
        try:
            url = self.current_url
            if not url:
                self.preview_failed.emit("No URL provided")
                return
            
            # Check if stop was requested
            if self._stop_requested:
                return
            
            self.progress_update.emit("Fetching video information...")
            logger.info(f"Fetching preview for URL: {url}")
            
            # Extract video information using asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                video_info = loop.run_until_complete(
                    self.downloader.extract_video_info(url)
                )
            finally:
                loop.close()
            
            if not video_info:
                self.preview_failed.emit("Failed to extract video information")
                return
            
            # Check if stop was requested
            if self._stop_requested:
                return
            
            self.progress_update.emit("Downloading thumbnail...")
            
            # Download and process thumbnail
            thumbnail_pixmap = self._download_thumbnail(video_info)
            
            if thumbnail_pixmap and not self._stop_requested:
                self.preview_ready.emit(video_info, thumbnail_pixmap)
                logger.info(f"Preview ready for: {video_info.title}")
            else:
                self.preview_failed.emit("Failed to download thumbnail")
                
        except Exception as e:
            logger.error(f"VideoPreviewWorker error: {e}", exc_info=True)
            self.preview_failed.emit(f"Preview failed: {str(e)}")
    
    def _download_thumbnail(self, video_info: VideoInfo) -> Optional[QPixmap]:
        """
        Download and cache video thumbnail.
        
        Args:
            video_info: Video information containing thumbnail URL
            
        Returns:
            QPixmap of thumbnail or None if failed
        """
        if not video_info.thumbnail:
            logger.warning("No thumbnail URL available")
            return None
        
        try:
            # Generate cache filename
            cache_filename = f"{video_info.id}_thumbnail.jpg"
            cache_path = self.cache_dir / cache_filename
            
            # Check cache first
            if cache_path.exists():
                logger.debug(f"Loading thumbnail from cache: {cache_path}")
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    return self._scale_thumbnail(pixmap)
            
            # Check if stop was requested before download
            if self._stop_requested:
                return None
            
            # Download thumbnail
            response = requests.get(str(video_info.thumbnail), timeout=10)
            response.raise_for_status()
            
            # Check if stop was requested after download
            if self._stop_requested:
                return None
            
            # Process image with PIL for better quality
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Save to cache
            image.save(cache_path, 'JPEG', quality=85)
            logger.debug(f"Thumbnail cached: {cache_path}")
            
            # Convert to QPixmap
            pixmap = QPixmap(str(cache_path))
            if not pixmap.isNull():
                return self._scale_thumbnail(pixmap)
            
        except requests.RequestException as e:
            logger.error(f"Failed to download thumbnail: {e}")
        except Exception as e:
            logger.error(f"Error processing thumbnail: {e}")
        
        return None
    
    def _scale_thumbnail(self, pixmap: QPixmap) -> QPixmap:
        """
        Scale thumbnail to appropriate size for display.
        
        Args:
            pixmap: Original thumbnail pixmap
            
        Returns:
            Scaled pixmap maintaining aspect ratio
        """
        # Target size for thumbnail display
        target_width = 320
        target_height = 180
        
        # Scale maintaining aspect ratio
        scaled = pixmap.scaled(
            target_width, target_height,
            aspectRatioMode=1,  # Qt.KeepAspectRatio
            transformMode=1     # Qt.SmoothTransformation
        )
        
        return scaled


class DownloadWorker(QThread):
    """
    Worker thread for handling video/audio downloads.
    
    Performs downloads in background with progress reporting
    and proper error handling.
    """
    
    # Signals for thread-safe communication
    download_started = pyqtSignal(str)  # Request ID
    progress_updated = pyqtSignal(ProgressInfo)  # Progress information
    download_completed = pyqtSignal(str, str)  # Request ID, output file
    download_failed = pyqtSignal(str, str)  # Request ID, error message
    
    def __init__(self, downloader: YouTubeDownloader, progress_manager: ProgressManager, parent: QObject = None):
        """
        Initialize download worker.
        
        Args:
            downloader: YouTubeDownloader instance
            progress_manager: Progress tracking manager
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.downloader = downloader
        self.progress_manager = progress_manager
        
        # Thread control
        self._stop_requested = False
        self._mutex = QMutex()
        
        # Current download
        self.current_request: Optional[DownloadRequest] = None
        
        # Connect progress manager signals
        self.progress_manager.progress_updated.connect(self.progress_updated.emit)
    
    def set_download_request(self, request: DownloadRequest):
        """Set the download request to process."""
        with self._mutex:
            self.current_request = request
            self._stop_requested = False
    
    def stop(self):
        """Request worker to stop current download."""
        with self._mutex:
            self._stop_requested = True
        
        # Cancel current download if active
        if self.current_request:
            self.progress_manager.cancel_download(self.current_request.request_id)
        
        # Wait for thread to finish with timeout
        if not self.wait(5000):  # 5 second timeout
            logger.warning("DownloadWorker did not stop gracefully")
            self.terminate()
    
    def run(self):
        """Main worker thread execution."""
        try:
            request = self.current_request
            if not request:
                self.download_failed.emit("unknown", "No download request provided")
                return
            
            # Check if stop was requested
            if self._stop_requested:
                return
            
            logger.info(f"Starting download: {request.request_id}")
            self.download_started.emit(request.request_id)
            
            # Set up asyncio loop for download
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Perform download using asyncio
                output_file = loop.run_until_complete(
                    self._perform_download(request)
                )
            finally:
                loop.close()
            
            # Check if download was successful
            if output_file and not self._stop_requested:
                self.download_completed.emit(request.request_id, output_file)
                logger.info(f"Download completed: {request.request_id} -> {output_file}")
            elif self._stop_requested:
                logger.info(f"Download cancelled: {request.request_id}")
            else:
                self.download_failed.emit(request.request_id, "Download failed")
                
        except Exception as e:
            logger.error(f"DownloadWorker error: {e}", exc_info=True)
            request_id = self.current_request.request_id if self.current_request else "unknown"
            self.download_failed.emit(request_id, f"Download error: {str(e)}")
    
    async def _perform_download(self, request: DownloadRequest) -> Optional[str]:
        """
        Perform the actual download operation.
        
        Args:
            request: Download request with all parameters
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Check download type and call appropriate method
            if request.download_type.value == "video":
                return await self.downloader.download_video(request)
            elif request.download_type.value == "audio":
                return await self.downloader.download_audio(request)
            elif request.download_type.value == "both":
                # Download both video and audio
                video_file = await self.downloader.download_video(request)
                if video_file and not self._stop_requested:
                    audio_file = await self.downloader.download_audio(request)
                    return video_file  # Return video file path
                return None
            else:
                logger.error(f"Unknown download type: {request.download_type}")
                return None
                
        except Exception as e:
            logger.error(f"Download operation failed: {e}")
            return None


class DependencyInstallWorker(QThread):
    """
    Worker thread for dependency installation and management.
    
    Handles dependency downloads and installation in background
    with progress reporting for GUI feedback.
    """
    
    # Signals for thread-safe communication
    install_started = pyqtSignal()
    install_progress = pyqtSignal(str, int)  # Message, percentage
    install_completed = pyqtSignal(bool)  # Success status
    install_failed = pyqtSignal(str)  # Error message
    
    def __init__(self, parent: QObject = None):
        """
        Initialize dependency install worker.
        
        Args:
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        
        # Thread control
        self._stop_requested = False
        self._mutex = QMutex()
        
        # Installation parameters
        self.app_root: Optional[Path] = None
        self.force_reinstall: bool = False
    
    def set_installation_params(self, app_root: Path, force_reinstall: bool = False):
        """Set parameters for dependency installation."""
        with self._mutex:
            self.app_root = app_root
            self.force_reinstall = force_reinstall
            self._stop_requested = False
    
    def stop(self):
        """Request worker to stop installation."""
        with self._mutex:
            self._stop_requested = True
        
        # Wait for thread to finish with timeout
        if not self.wait(10000):  # 10 second timeout
            logger.warning("DependencyInstallWorker did not stop gracefully")
            self.terminate()
    
    def run(self):
        """Main worker thread execution."""
        try:
            if not self.app_root:
                self.install_failed.emit("No application root specified")
                return
            
            self.install_started.emit()
            logger.info("Starting dependency installation")
            
            # Import here to avoid circular imports
            from dependencies.downloader import BinaryDownloader
            
            # Create progress callback
            def progress_callback(message: str, percentage: int = 0):
                if not self._stop_requested:
                    self.install_progress.emit(message, percentage)
            
            # Create downloader and perform installation
            downloader = BinaryDownloader(self.app_root, progress_callback)
            
            # Check if stop was requested
            if self._stop_requested:
                return
            
            success = downloader.download_all_dependencies()
            
            if success and not self._stop_requested:
                self.install_completed.emit(True)
                logger.info("Dependency installation completed successfully")
            elif self._stop_requested:
                logger.info("Dependency installation cancelled")
            else:
                self.install_failed.emit("Installation failed")
                logger.error("Dependency installation failed")
                
        except Exception as e:
            logger.error(f"DependencyInstallWorker error: {e}", exc_info=True)
            self.install_failed.emit(f"Installation error: {str(e)}")


class WorkerManager(QObject):
    """
    Manager class for coordinating multiple worker threads.
    
    Provides centralized management of all background workers
    with proper lifecycle management and cleanup.
    """
    
    def __init__(self, downloader: YouTubeDownloader, progress_manager: ProgressManager, 
                 cache_dir: Path, parent: QObject = None):
        """
        Initialize worker manager.
        
        Args:
            downloader: YouTubeDownloader instance
            progress_manager: Progress tracking manager
            cache_dir: Directory for caching
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        
        self.downloader = downloader
        self.progress_manager = progress_manager
        self.cache_dir = cache_dir
        
        # Worker instances
        self.preview_worker: Optional[VideoPreviewWorker] = None
        self.download_worker: Optional[DownloadWorker] = None
        self.install_worker: Optional[DependencyInstallWorker] = None
        
        logger.info("WorkerManager initialized")
    
    def get_preview_worker(self) -> VideoPreviewWorker:
        """Get or create video preview worker."""
        if self.preview_worker is None or not self.preview_worker.isRunning():
            if self.preview_worker:
                self.preview_worker.deleteLater()
            
            self.preview_worker = VideoPreviewWorker(
                self.downloader, self.cache_dir, self
            )
        
        return self.preview_worker
    
    def get_download_worker(self) -> DownloadWorker:
        """Get or create download worker."""
        if self.download_worker is None or not self.download_worker.isRunning():
            if self.download_worker:
                self.download_worker.deleteLater()
            
            self.download_worker = DownloadWorker(
                self.downloader, self.progress_manager, self
            )
        
        return self.download_worker
    
    def get_install_worker(self) -> DependencyInstallWorker:
        """Get or create dependency install worker."""
        if self.install_worker is None or not self.install_worker.isRunning():
            if self.install_worker:
                self.install_worker.deleteLater()
            
            self.install_worker = DependencyInstallWorker(self)
        
        return self.install_worker
    
    def stop_all_workers(self):
        """Stop all active workers gracefully."""
        logger.info("Stopping all workers")
        
        workers = [
            self.preview_worker,
            self.download_worker,
            self.install_worker
        ]
        
        for worker in workers:
            if worker and worker.isRunning():
                worker.stop()
        
        logger.info("All workers stopped")
    
    def cleanup(self):
        """Clean up all worker resources."""
        self.stop_all_workers()
        
        # Delete worker instances
        for worker in [self.preview_worker, self.download_worker, self.install_worker]:
            if worker:
                worker.deleteLater()
        
        self.preview_worker = None
        self.download_worker = None
        self.install_worker = None
        
        logger.info("WorkerManager cleanup completed")