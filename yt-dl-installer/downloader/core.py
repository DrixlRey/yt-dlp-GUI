"""
Core YouTube downloader implementation using yt-dlp.

This module provides the main downloader functionality including
metadata extraction, video downloading, and progress tracking.
"""

import os
import sys
import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from urllib.parse import urlparse
from datetime import datetime

# Add embedded Python path for imports
script_dir = Path(__file__).parent.parent
python_runtime = script_dir / "python_runtime"
if python_runtime.exists():
    sys.path.insert(0, str(python_runtime / "Lib" / "site-packages"))

try:
    import yt_dlp
    from yt_dlp.utils import DownloadError, ExtractorError
except ImportError as e:
    yt_dlp = None
    DownloadError = Exception
    ExtractorError = Exception

from .validation import (
    VideoInfo, DownloadRequest, ProgressInfo,
    ProgressStatus, DownloadType, QualityOption
)

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """
    Core YouTube downloader using yt-dlp.
    
    Handles video metadata extraction, downloading, and progress tracking
    with support for various formats and quality options.
    """
    
    def __init__(self, app_root: Path, config: Dict[str, Any]):
        """
        Initialize YouTube downloader.
        
        Args:
            app_root: Root directory of the application
            config: Application configuration dictionary
        """
        self.app_root = Path(app_root)
        self.config = config
        self.active_downloads: Dict[str, Any] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
        
        # Set up paths
        self.cache_dir = self.app_root / "cache"
        self.temp_dir = self.app_root / "temp"
        self.binaries_dir = self.app_root / "binaries"
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp paths
        self.ffmpeg_path = self.binaries_dir / "ffmpeg" / "bin" / "ffmpeg.exe"
        self.ffprobe_path = self.binaries_dir / "ffmpeg" / "bin" / "ffprobe.exe"
        
        if not yt_dlp:
            logger.error("yt-dlp not available. Run setup.py to install dependencies.")
    
    def _get_ydl_opts(self, request: DownloadRequest, for_info: bool = False) -> Dict[str, Any]:
        """
        Get yt-dlp options for download or info extraction.
        
        Args:
            request: Download request parameters
            for_info: Whether options are for info extraction only
            
        Returns:
            Dictionary of yt-dlp options
        """
        opts = {
            # Paths and executables
            'ffmpeg_location': str(self.ffmpeg_path.parent) if self.ffmpeg_path.exists() else None,
            'cachedir': str(self.cache_dir),
            
            # Output template and format
            'outtmpl': self._get_output_template(request),
            'restrictfilenames': True,
            'windowsfilenames': True,
            
            # Quality and format selection
            'format': self._get_format_selector(request),
            
            # Extraction options
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'writedescription': False,
            'writesubtitles': request.embed_subs,
            'writeautomaticsub': request.embed_subs,
            'subtitleslangs': request.subtitle_langs if request.subtitle_langs else ['en'],
            
            # Download behavior
            'ignoreerrors': False,
            'no_warnings': False,
            'continuedl': request.continue_partial,
            'retries': request.retry_count,
            'fragment_retries': request.retry_count,
            
            # Networking
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks
            
            # Logging
            'logger': logger,
            'no_color': True,
        }
        
        if for_info:
            # For info extraction, don't download anything
            opts.update({
                'simulate': True,
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            })
        else:
            # For actual downloads, add progress hook
            opts['progress_hooks'] = [self._progress_hook]
            
            # Handle audio extraction
            if request.download_type == DownloadType.AUDIO or request.extract_audio:
                opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': request.audio_format.value if request.audio_format else 'mp3',
                        'preferredquality': '192',
                        'nopostoverwrites': not request.overwrite,
                    }]
                })
                
                if not request.keep_video and request.download_type != DownloadType.AUDIO:
                    opts['postprocessors'][0]['nopostoverwrites'] = False
        
        return opts
    
    def _get_output_template(self, request: DownloadRequest) -> str:
        """
        Generate output template for yt-dlp.
        
        Args:
            request: Download request parameters
            
        Returns:
            Output template string
        """
        output_dir = request.output_path
        
        if request.filename_template:
            template = request.filename_template
        else:
            # Default template with safe filename
            template = "%(title)s.%(ext)s"
        
        return str(output_dir / template)
    
    def _get_format_selector(self, request: DownloadRequest) -> str:
        """
        Generate format selector for yt-dlp based on request parameters.
        
        Args:
            request: Download request parameters
            
        Returns:
            Format selector string
        """
        if request.download_type == DownloadType.AUDIO:
            return "bestaudio/best"
        
        quality = request.quality
        video_format = request.video_format.value if request.video_format else "mp4"
        
        if quality == QualityOption.BEST:
            return f"best[ext={video_format}]/best"
        elif quality == QualityOption.WORST:
            return f"worst[ext={video_format}]/worst"
        else:
            # Extract height from quality (e.g., "720p" -> "720")
            height = quality.value.rstrip('p')
            return f"best[height<={height}][ext={video_format}]/best[height<={height}]/best"
    
    def _progress_hook(self, d: Dict[str, Any]):
        """
        Progress hook for yt-dlp downloads.
        
        Args:
            d: Progress dictionary from yt-dlp
        """
        if 'info_dict' not in d:
            return
        
        # Find associated request
        request_id = None
        for rid, download_info in self.active_downloads.items():
            if download_info.get('temp_filename') == d.get('tmpfilename'):
                request_id = rid
                break
        
        if not request_id:
            return
        
        # Create progress info
        progress = self._create_progress_from_ydl(d, request_id)
        
        # Update active download info
        self.active_downloads[request_id]['progress'] = progress
        
        # Call progress callback if registered
        if request_id in self.progress_callbacks:
            try:
                self.progress_callbacks[request_id](progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _create_progress_from_ydl(self, d: Dict[str, Any], request_id: str) -> ProgressInfo:
        """
        Create ProgressInfo from yt-dlp progress dictionary.
        
        Args:
            d: Progress dictionary from yt-dlp
            request_id: Associated request ID
            
        Returns:
            ProgressInfo object
        """
        status_map = {
            'downloading': ProgressStatus.DOWNLOADING,
            'finished': ProgressStatus.COMPLETED,
            'error': ProgressStatus.FAILED,
        }
        
        status = status_map.get(d.get('status', 'downloading'), ProgressStatus.DOWNLOADING)
        
        # Extract progress information
        downloaded_bytes = d.get('downloaded_bytes', 0)
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        speed = d.get('speed')
        eta = d.get('eta')
        
        # Calculate percentage
        percentage = 0.0
        if total_bytes and total_bytes > 0:
            percentage = min(100.0, (downloaded_bytes / total_bytes) * 100.0)
        
        # Get current operation
        current_operation = None
        if d.get('status') == 'downloading':
            current_operation = f"Downloading {d.get('filename', 'video')}"
        elif d.get('status') == 'finished':
            current_operation = "Download completed"
        
        return ProgressInfo(
            request_id=request_id,
            status=status,
            percentage=percentage,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            speed=speed,
            eta=eta,
            filename=d.get('filename'),
            temp_filename=d.get('tmpfilename'),
            current_operation=current_operation,
            fragment_index=d.get('fragment_index'),
            fragment_count=d.get('fragment_count'),
            updated_at=datetime.now()
        )
    
    async def extract_video_info(self, url: str) -> VideoInfo:
        """
        Extract video metadata from URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            VideoInfo object with metadata
            
        Raises:
            Exception: If extraction fails
        """
        if not yt_dlp:
            raise Exception("yt-dlp not available. Run setup.py to install dependencies.")
        
        logger.info(f"Extracting video info for: {url}")
        
        # Create temporary request for options
        temp_request = DownloadRequest(
            url=url,
            download_type=DownloadType.VIDEO,
            output_path=self.temp_dir,
            request_id="temp_info"
        )
        
        ydl_opts = self._get_ydl_opts(temp_request, for_info=True)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise Exception("Failed to extract video information")
                
                # Convert to VideoInfo model
                video_info = self._convert_to_video_info(info)
                
                logger.info(f"Successfully extracted info for: {video_info.title}")
                return video_info
                
        except ExtractorError as e:
            logger.error(f"Extractor error: {e}")
            raise Exception(f"Failed to extract video info: {str(e)}")
        except DownloadError as e:
            logger.error(f"Download error during info extraction: {e}")
            raise Exception(f"Failed to extract video info: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during info extraction: {e}")
            raise Exception(f"Failed to extract video info: {str(e)}")
    
    def _convert_to_video_info(self, info: Dict[str, Any]) -> VideoInfo:
        """
        Convert yt-dlp info dict to VideoInfo model.
        
        Args:
            info: yt-dlp info dictionary
            
        Returns:
            VideoInfo object
        """
        # Extract basic information
        video_data = {
            'id': info.get('id', ''),
            'title': info.get('title', 'Unknown Title'),
            'url': info.get('webpage_url', info.get('original_url', '')),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'upload_date': info.get('upload_date'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'channel': info.get('channel', info.get('uploader')),
            'channel_id': info.get('channel_id'),
            'channel_url': info.get('channel_url'),
            'uploader': info.get('uploader'),
            'thumbnail': info.get('thumbnail'),
            'thumbnails': info.get('thumbnails', []),
            'formats': info.get('formats', []),
            'filename': info.get('filename'),
            'ext': info.get('ext'),
            'filesize': info.get('filesize'),
            'filesize_approx': info.get('filesize_approx'),
            'is_live': info.get('is_live', False),
            'age_limit': info.get('age_limit'),
        }
        
        # Determine if video/audio tracks are available
        formats = info.get('formats', [])
        has_video = any(f.get('vcodec') != 'none' for f in formats)
        has_audio = any(f.get('acodec') != 'none' for f in formats)
        
        video_data.update({
            'has_video': has_video,
            'has_audio': has_audio,
        })
        
        return VideoInfo(**video_data)
    
    def start_download(self, request: DownloadRequest, 
                      progress_callback: Optional[Callable[[ProgressInfo], None]] = None) -> str:
        """
        Start a download asynchronously.
        
        Args:
            request: Download request parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            Request ID for tracking the download
        """
        if not yt_dlp:
            raise Exception("yt-dlp not available. Run setup.py to install dependencies.")
        
        logger.info(f"Starting download: {request.url}")
        
        # Register progress callback
        if progress_callback:
            self.progress_callbacks[request.request_id] = progress_callback
        
        # Initialize download tracking
        self.active_downloads[request.request_id] = {
            'request': request,
            'started_at': datetime.now(),
            'progress': ProgressInfo(
                request_id=request.request_id,
                status=ProgressStatus.PENDING,
                started_at=datetime.now()
            )
        }
        
        # Start download in separate thread
        download_thread = threading.Thread(
            target=self._download_worker,
            args=(request,),
            daemon=True
        )
        download_thread.start()
        
        return request.request_id
    
    def _download_worker(self, request: DownloadRequest):
        """
        Worker function for downloading in separate thread.
        
        Args:
            request: Download request parameters
        """
        try:
            # Update status to downloading
            self._update_progress(request.request_id, status=ProgressStatus.DOWNLOADING)
            
            # Get yt-dlp options
            ydl_opts = self._get_ydl_opts(request, for_info=False)
            
            # Perform download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([str(request.url)])
            
            # Update status to completed
            self._update_progress(
                request.request_id,
                status=ProgressStatus.COMPLETED,
                percentage=100.0,
                completed_at=datetime.now()
            )
            
            logger.info(f"Download completed: {request.request_id}")
            
        except Exception as e:
            logger.error(f"Download failed for {request.request_id}: {e}")
            self._update_progress(
                request.request_id,
                status=ProgressStatus.FAILED,
                error_message=str(e)
            )
        finally:
            # Clean up
            if request.request_id in self.progress_callbacks:
                del self.progress_callbacks[request.request_id]
    
    def _update_progress(self, request_id: str, **kwargs):
        """
        Update progress information for a download.
        
        Args:
            request_id: Request ID to update
            **kwargs: Progress fields to update
        """
        if request_id not in self.active_downloads:
            return
        
        current_progress = self.active_downloads[request_id]['progress']
        updated_progress = current_progress.update_progress(**kwargs)
        
        self.active_downloads[request_id]['progress'] = updated_progress
        
        # Call progress callback
        if request_id in self.progress_callbacks:
            try:
                self.progress_callbacks[request_id](updated_progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def cancel_download(self, request_id: str) -> bool:
        """
        Cancel an active download.
        
        Args:
            request_id: Request ID to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if request_id not in self.active_downloads:
            return False
        
        logger.info(f"Cancelling download: {request_id}")
        
        # Update status
        self._update_progress(request_id, status=ProgressStatus.CANCELLED)
        
        # Clean up
        if request_id in self.progress_callbacks:
            del self.progress_callbacks[request_id]
        
        return True
    
    def get_download_progress(self, request_id: str) -> Optional[ProgressInfo]:
        """
        Get current progress for a download.
        
        Args:
            request_id: Request ID to check
            
        Returns:
            ProgressInfo object or None if not found
        """
        if request_id not in self.active_downloads:
            return None
        
        return self.active_downloads[request_id]['progress']
    
    def get_active_downloads(self) -> List[str]:
        """
        Get list of active download IDs.
        
        Returns:
            List of active request IDs
        """
        return list(self.active_downloads.keys())
    
    def cleanup_completed_downloads(self):
        """Remove completed downloads from active tracking."""
        completed_ids = []
        
        for request_id, download_info in self.active_downloads.items():
            progress = download_info['progress']
            if progress.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
                completed_ids.append(request_id)
        
        for request_id in completed_ids:
            if request_id in self.active_downloads:
                del self.active_downloads[request_id]
            if request_id in self.progress_callbacks:
                del self.progress_callbacks[request_id]
        
        logger.info(f"Cleaned up {len(completed_ids)} completed downloads")