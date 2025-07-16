"""
Data validation models for the YouTube Downloader GUI.

This module defines Pydantic models for validating video information,
download requests, and progress tracking throughout the application.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator, HttpUrl


class VideoFormat(str, Enum):
    """Supported video download formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"


class AudioFormat(str, Enum):
    """Supported audio download formats."""
    MP3 = "mp3"
    M4A = "m4a"
    OGG = "ogg"
    WAV = "wav"


class QualityOption(str, Enum):
    """Video quality options."""
    BEST = "best"
    WORST = "worst"
    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"
    P240 = "240p"
    P144 = "144p"


class DownloadType(str, Enum):
    """Type of download."""
    VIDEO = "video"
    AUDIO = "audio"
    BOTH = "both"


class ProgressStatus(str, Enum):
    """Download progress status."""
    PENDING = "pending"
    FETCHING_INFO = "fetching_info"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoInfo(BaseModel):
    """
    Model for YouTube video metadata information.
    
    Contains all relevant information about a video including
    title, duration, thumbnail, available formats, etc.
    """
    
    # Core video information
    id: str = Field(..., description="Unique video ID")
    title: str = Field(..., description="Video title")
    url: HttpUrl = Field(..., description="Original video URL")
    webpage_url: Optional[HttpUrl] = Field(None, description="Canonical webpage URL")
    
    # Video metadata
    description: Optional[str] = Field(None, description="Video description")
    duration: Optional[int] = Field(None, description="Video duration in seconds")
    duration_string: Optional[str] = Field(None, description="Human-readable duration")
    upload_date: Optional[str] = Field(None, description="Upload date (YYYYMMDD)")
    view_count: Optional[int] = Field(None, description="Number of views")
    like_count: Optional[int] = Field(None, description="Number of likes")
    
    # Channel information
    channel: Optional[str] = Field(None, description="Channel name")
    channel_id: Optional[str] = Field(None, description="Channel ID")
    channel_url: Optional[str] = Field(None, description="Channel URL")
    uploader: Optional[str] = Field(None, description="Uploader name")
    
    # Thumbnail information
    thumbnail: Optional[HttpUrl] = Field(None, description="Best thumbnail URL")
    thumbnails: Optional[List[Dict[str, Any]]] = Field(None, description="All available thumbnails")
    
    # Format information
    formats: Optional[List[Dict[str, Any]]] = Field(None, description="Available formats")
    available_qualities: List[str] = Field(default_factory=list, description="Available quality options")
    has_video: bool = Field(True, description="Whether video track is available")
    has_audio: bool = Field(True, description="Whether audio track is available")
    
    # File information
    filename: Optional[str] = Field(None, description="Suggested filename")
    ext: Optional[str] = Field(None, description="File extension")
    filesize: Optional[int] = Field(None, description="Estimated file size in bytes")
    filesize_approx: Optional[int] = Field(None, description="Approximate file size")
    
    # Validation and error handling
    is_live: bool = Field(False, description="Whether this is a live stream")
    is_upcoming: bool = Field(False, description="Whether this is an upcoming premiere")
    age_limit: Optional[int] = Field(None, description="Age restriction")
    
    # Metadata timestamps
    fetched_at: datetime = Field(default_factory=datetime.now, description="When metadata was fetched")
    
    @validator('duration_string', pre=True, always=True)
    def format_duration(cls, v, values):
        """Format duration from seconds to readable string."""
        if v is not None:
            return v
        
        duration = values.get('duration')
        if duration is None:
            return None
        
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @validator('available_qualities', pre=True, always=True)
    def extract_qualities(cls, v, values):
        """Extract available quality options from formats."""
        if v:  # If already set, keep it
            return v
        
        formats = values.get('formats', [])
        if not formats:
            return []
        
        qualities = set()
        for fmt in formats:
            if fmt.get('height'):
                qualities.add(f"{fmt['height']}p")
        
        # Sort qualities by resolution (descending)
        quality_order = [2160, 1440, 1080, 720, 480, 360, 240, 144]
        sorted_qualities = []
        
        for q in quality_order:
            if f"{q}p" in qualities:
                sorted_qualities.append(f"{q}p")
        
        # Add special options
        if sorted_qualities:
            sorted_qualities.insert(0, "best")
            sorted_qualities.append("worst")
        
        return sorted_qualities
    
    class Config:
        """Pydantic configuration."""
        # Allow extra fields for future compatibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True


class DownloadRequest(BaseModel):
    """
    Model for download request parameters.
    
    Contains all user-specified options for downloading a video
    including format, quality, output location, etc.
    """
    
    # Required fields
    url: HttpUrl = Field(..., description="Video URL to download")
    download_type: DownloadType = Field(..., description="Type of download (video/audio/both)")
    
    # Output configuration
    output_path: Path = Field(..., description="Directory to save downloaded files")
    filename_template: Optional[str] = Field(None, description="Custom filename template")
    
    # Format options
    video_format: Optional[VideoFormat] = Field(None, description="Video container format")
    audio_format: Optional[AudioFormat] = Field(None, description="Audio format for audio-only downloads")
    quality: QualityOption = Field(QualityOption.BEST, description="Video quality preference")
    
    # Advanced options
    extract_audio: bool = Field(False, description="Extract audio from video")
    keep_video: bool = Field(True, description="Keep video file when extracting audio")
    embed_subs: bool = Field(False, description="Embed subtitles if available")
    subtitle_langs: List[str] = Field(default_factory=list, description="Subtitle languages to download")
    
    # Download behavior
    overwrite: bool = Field(False, description="Overwrite existing files")
    continue_partial: bool = Field(True, description="Continue partial downloads")
    retry_count: int = Field(3, description="Number of retry attempts")
    
    # Metadata
    request_id: str = Field(..., description="Unique identifier for this request")
    created_at: datetime = Field(default_factory=datetime.now, description="When request was created")
    
    @validator('url')
    def validate_youtube_url(cls, v):
        """Validate that URL is a supported YouTube URL."""
        url_str = str(v)
        
        # YouTube URL patterns
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+',
        ]
        
        if not any(re.match(pattern, url_str, re.IGNORECASE) for pattern in youtube_patterns):
            raise ValueError('URL must be a valid YouTube URL')
        
        return v
    
    @validator('output_path')
    def validate_output_path(cls, v):
        """Validate output path is accessible."""
        path = Path(v)
        
        # Create directory if it doesn't exist
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f'Cannot create output directory: {e}')
        
        # Check if directory is writable
        if not path.is_dir():
            raise ValueError('Output path must be a directory')
        
        test_file = path / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
        except Exception:
            raise ValueError('Output directory is not writable')
        
        return path
    
    @validator('filename_template')
    def validate_filename_template(cls, v):
        """Validate filename template doesn't contain invalid characters."""
        if v is None:
            return v
        
        # Check for invalid filename characters
        invalid_chars = '<>:"|?*'
        if any(char in v for char in invalid_chars):
            raise ValueError(f'Filename template contains invalid characters: {invalid_chars}')
        
        return v
    
    @validator('subtitle_langs')
    def validate_subtitle_langs(cls, v):
        """Validate subtitle language codes."""
        if not v:
            return v
        
        # Basic validation for language codes (2-3 letter codes)
        valid_pattern = re.compile(r'^[a-z]{2,3}(-[A-Z]{2})?$')
        
        for lang in v:
            if not valid_pattern.match(lang):
                raise ValueError(f'Invalid language code: {lang}')
        
        return v
    
    class Config:
        """Pydantic configuration."""
        # Use enum values for serialization
        use_enum_values = True
        # Support Path objects
        arbitrary_types_allowed = True


class ProgressInfo(BaseModel):
    """
    Model for download progress information.
    
    Tracks the current state and progress of a download operation
    including percentage, speed, ETA, and error information.
    """
    
    # Request identification
    request_id: str = Field(..., description="Associated download request ID")
    
    # Progress information
    status: ProgressStatus = Field(..., description="Current download status")
    percentage: float = Field(0.0, description="Download percentage (0.0-100.0)")
    
    # Size information
    downloaded_bytes: int = Field(0, description="Bytes downloaded so far")
    total_bytes: Optional[int] = Field(None, description="Total file size in bytes")
    total_bytes_estimate: Optional[int] = Field(None, description="Estimated total size")
    
    # Speed and timing
    speed: Optional[float] = Field(None, description="Download speed in bytes/second")
    eta: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    elapsed: float = Field(0.0, description="Elapsed time in seconds")
    
    # File information
    filename: Optional[str] = Field(None, description="Current file being downloaded")
    temp_filename: Optional[str] = Field(None, description="Temporary download filename")
    final_filename: Optional[str] = Field(None, description="Final output filename")
    
    # Status information
    current_operation: Optional[str] = Field(None, description="Current operation description")
    fragment_index: Optional[int] = Field(None, description="Current fragment index")
    fragment_count: Optional[int] = Field(None, description="Total fragment count")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warning_messages: List[str] = Field(default_factory=list, description="Warning messages")
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Metadata
    started_at: Optional[datetime] = Field(None, description="When download started")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="When download completed")
    
    @validator('percentage')
    def validate_percentage(cls, v):
        """Ensure percentage is between 0 and 100."""
        if not (0.0 <= v <= 100.0):
            raise ValueError('Percentage must be between 0.0 and 100.0')
        return v
    
    @validator('speed')
    def validate_speed(cls, v):
        """Ensure speed is non-negative."""
        if v is not None and v < 0:
            raise ValueError('Speed cannot be negative')
        return v
    
    @validator('eta')
    def validate_eta(cls, v):
        """Ensure ETA is non-negative."""
        if v is not None and v < 0:
            raise ValueError('ETA cannot be negative')
        return v
    
    @property
    def speed_str(self) -> Optional[str]:
        """Format speed as human-readable string."""
        if self.speed is None:
            return None
        
        if self.speed < 1024:
            return f"{self.speed:.1f} B/s"
        elif self.speed < 1024 * 1024:
            return f"{self.speed / 1024:.1f} KB/s"
        elif self.speed < 1024 * 1024 * 1024:
            return f"{self.speed / (1024 * 1024):.1f} MB/s"
        else:
            return f"{self.speed / (1024 * 1024 * 1024):.1f} GB/s"
    
    @property
    def eta_str(self) -> Optional[str]:
        """Format ETA as human-readable string."""
        if self.eta is None:
            return None
        
        if self.eta < 60:
            return f"{self.eta}s"
        elif self.eta < 3600:
            minutes = self.eta // 60
            seconds = self.eta % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = self.eta // 3600
            minutes = (self.eta % 3600) // 60
            return f"{hours}h {minutes}m"
    
    @property
    def size_str(self) -> str:
        """Format downloaded/total size as human-readable string."""
        def format_bytes(bytes_val):
            if bytes_val < 1024:
                return f"{bytes_val} B"
            elif bytes_val < 1024 * 1024:
                return f"{bytes_val / 1024:.1f} KB"
            elif bytes_val < 1024 * 1024 * 1024:
                return f"{bytes_val / (1024 * 1024):.1f} MB"
            else:
                return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB"
        
        downloaded = format_bytes(self.downloaded_bytes)
        
        if self.total_bytes:
            total = format_bytes(self.total_bytes)
            return f"{downloaded} / {total}"
        elif self.total_bytes_estimate:
            total = format_bytes(self.total_bytes_estimate)
            return f"{downloaded} / ~{total}"
        else:
            return downloaded
    
    def update_progress(self, **kwargs) -> 'ProgressInfo':
        """Create updated progress info with new values."""
        update_data = dict(self.dict())
        update_data.update(kwargs)
        update_data['updated_at'] = datetime.now()
        
        return ProgressInfo(**update_data)
    
    class Config:
        """Pydantic configuration."""
        # Use enum values for serialization
        use_enum_values = True