"""
Progress monitoring and management system.

This module provides centralized tracking of download progress,
statistics aggregation, and event-based notifications for the GUI.
"""

import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from .validation import ProgressInfo, ProgressStatus

logger = logging.getLogger(__name__)


class ProgressEventType(str, Enum):
    """Types of progress events."""
    STARTED = "started"
    UPDATED = "updated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SPEED_UPDATED = "speed_updated"
    ETA_UPDATED = "eta_updated"


@dataclass
class ProgressEvent:
    """Progress event data."""
    event_type: ProgressEventType
    request_id: str
    progress: ProgressInfo
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressStatistics:
    """Aggregated progress statistics."""
    total_downloads: int = 0
    active_downloads: int = 0
    completed_downloads: int = 0
    failed_downloads: int = 0
    cancelled_downloads: int = 0
    
    total_bytes_downloaded: int = 0
    total_bytes_to_download: int = 0
    overall_progress: float = 0.0
    
    average_speed: float = 0.0
    peak_speed: float = 0.0
    estimated_time_remaining: int = 0
    
    session_start_time: datetime = field(default_factory=datetime.now)
    session_duration: timedelta = field(default_factory=timedelta)
    
    def update_session_duration(self):
        """Update session duration from start time."""
        self.session_duration = datetime.now() - self.session_start_time


class ProgressManager:
    """
    Centralized progress monitoring and management system.
    
    Tracks multiple download progress, provides statistics,
    and handles event-based notifications for the GUI.
    """
    
    def __init__(self):
        """Initialize progress manager."""
        self.active_progress: Dict[str, ProgressInfo] = {}
        self.progress_history: Dict[str, List[ProgressInfo]] = defaultdict(list)
        self.event_listeners: List[Callable[[ProgressEvent], None]] = []
        self.statistics = ProgressStatistics()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Speed tracking
        self._speed_history: Dict[str, List[tuple]] = defaultdict(list)  # (timestamp, bytes)
        self._speed_window = 10  # seconds for speed calculation
        
        logger.info("Progress manager initialized")
    
    def register_progress(self, request_id: str, initial_progress: Optional[ProgressInfo] = None):
        """
        Register a new download for progress tracking.
        
        Args:
            request_id: Unique identifier for the download
            initial_progress: Optional initial progress state
        """
        with self._lock:
            if initial_progress is None:
                initial_progress = ProgressInfo(
                    request_id=request_id,
                    status=ProgressStatus.PENDING
                )
            
            self.active_progress[request_id] = initial_progress
            self.progress_history[request_id] = [initial_progress]
            
            # Update statistics
            self.statistics.total_downloads += 1
            self.statistics.active_downloads += 1
            self._update_statistics()
            
            # Fire event
            event = ProgressEvent(
                event_type=ProgressEventType.STARTED,
                request_id=request_id,
                progress=initial_progress
            )
            self._fire_event(event)
            
            logger.info(f"Registered progress tracking for: {request_id}")
    
    def update_progress(self, request_id: str, progress: ProgressInfo):
        """
        Update progress for a download.
        
        Args:
            request_id: Download identifier
            progress: Updated progress information
        """
        with self._lock:
            if request_id not in self.active_progress:
                logger.warning(f"Received progress for unregistered download: {request_id}")
                return
            
            previous_progress = self.active_progress[request_id]
            self.active_progress[request_id] = progress
            self.progress_history[request_id].append(progress)
            
            # Update speed tracking
            self._update_speed_tracking(request_id, progress)
            
            # Update statistics
            self._update_statistics()
            
            # Determine event type
            event_type = self._determine_event_type(previous_progress, progress)
            
            # Fire appropriate events
            event = ProgressEvent(
                event_type=event_type,
                request_id=request_id,
                progress=progress,
                data=self._get_event_data(previous_progress, progress)
            )
            self._fire_event(event)
            
            # Handle completion/failure
            if progress.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
                self._handle_download_completion(request_id, progress)
    
    def _update_speed_tracking(self, request_id: str, progress: ProgressInfo):
        """
        Update speed tracking history for a download.
        
        Args:
            request_id: Download identifier
            progress: Current progress information
        """
        now = datetime.now()
        speed_history = self._speed_history[request_id]
        
        # Add current data point
        speed_history.append((now, progress.downloaded_bytes))
        
        # Clean old data points (keep only last 'speed_window' seconds)
        cutoff_time = now - timedelta(seconds=self._speed_window)
        self._speed_history[request_id] = [
            (timestamp, bytes_downloaded) 
            for timestamp, bytes_downloaded in speed_history
            if timestamp > cutoff_time
        ]
        
        # Calculate current speed if we have enough data points
        if len(speed_history) >= 2:
            recent_points = self._speed_history[request_id][-5:]  # Last 5 points
            if len(recent_points) >= 2:
                time_diff = (recent_points[-1][0] - recent_points[0][0]).total_seconds()
                bytes_diff = recent_points[-1][1] - recent_points[0][1]
                
                if time_diff > 0:
                    calculated_speed = bytes_diff / time_diff
                    # Update progress with calculated speed if not provided
                    if progress.speed is None or abs(progress.speed - calculated_speed) > progress.speed * 0.5:
                        progress.speed = calculated_speed
    
    def _determine_event_type(self, previous: ProgressInfo, current: ProgressInfo) -> ProgressEventType:
        """
        Determine the type of event based on progress changes.
        
        Args:
            previous: Previous progress state
            current: Current progress state
            
        Returns:
            Appropriate event type
        """
        # Status change events
        if previous.status != current.status:
            if current.status == ProgressStatus.COMPLETED:
                return ProgressEventType.COMPLETED
            elif current.status == ProgressStatus.FAILED:
                return ProgressEventType.FAILED
            elif current.status == ProgressStatus.CANCELLED:
                return ProgressEventType.CANCELLED
        
        # Speed change events
        if (previous.speed != current.speed and 
            current.speed is not None and 
            abs((current.speed or 0) - (previous.speed or 0)) > 1024 * 100):  # 100 KB/s change
            return ProgressEventType.SPEED_UPDATED
        
        # ETA change events
        if (previous.eta != current.eta and 
            current.eta is not None and
            abs((current.eta or 0) - (previous.eta or 0)) > 5):  # 5 second change
            return ProgressEventType.ETA_UPDATED
        
        # Default update event
        return ProgressEventType.UPDATED
    
    def _get_event_data(self, previous: ProgressInfo, current: ProgressInfo) -> Dict[str, Any]:
        """
        Get additional data for progress events.
        
        Args:
            previous: Previous progress state
            current: Current progress state
            
        Returns:
            Dictionary of event-specific data
        """
        data = {}
        
        # Speed change data
        if previous.speed != current.speed:
            data['speed_change'] = {
                'previous': previous.speed,
                'current': current.speed,
                'difference': (current.speed or 0) - (previous.speed or 0)
            }
        
        # Progress change data
        if previous.percentage != current.percentage:
            data['progress_change'] = {
                'previous': previous.percentage,
                'current': current.percentage,
                'difference': current.percentage - previous.percentage
            }
        
        # ETA change data
        if previous.eta != current.eta:
            data['eta_change'] = {
                'previous': previous.eta,
                'current': current.eta
            }
        
        return data
    
    def _handle_download_completion(self, request_id: str, progress: ProgressInfo):
        """
        Handle download completion, failure, or cancellation.
        
        Args:
            request_id: Download identifier
            progress: Final progress state
        """
        # Update statistics based on final status
        if progress.status == ProgressStatus.COMPLETED:
            self.statistics.completed_downloads += 1
        elif progress.status == ProgressStatus.FAILED:
            self.statistics.failed_downloads += 1
        elif progress.status == ProgressStatus.CANCELLED:
            self.statistics.cancelled_downloads += 1
        
        self.statistics.active_downloads = max(0, self.statistics.active_downloads - 1)
        
        # Clean up speed tracking
        if request_id in self._speed_history:
            del self._speed_history[request_id]
        
        logger.info(f"Download completed with status {progress.status}: {request_id}")
    
    def _update_statistics(self):
        """Update aggregated statistics."""
        with self._lock:
            # Reset calculated fields
            self.statistics.total_bytes_downloaded = 0
            self.statistics.total_bytes_to_download = 0
            speeds = []
            
            # Aggregate data from active downloads
            for progress in self.active_progress.values():
                self.statistics.total_bytes_downloaded += progress.downloaded_bytes
                
                if progress.total_bytes:
                    self.statistics.total_bytes_to_download += progress.total_bytes
                elif progress.total_bytes_estimate:
                    self.statistics.total_bytes_to_download += progress.total_bytes_estimate
                
                if progress.speed and progress.speed > 0:
                    speeds.append(progress.speed)
            
            # Calculate overall progress
            if self.statistics.total_bytes_to_download > 0:
                self.statistics.overall_progress = (
                    self.statistics.total_bytes_downloaded / 
                    self.statistics.total_bytes_to_download
                ) * 100.0
            else:
                self.statistics.overall_progress = 0.0
            
            # Calculate average and peak speeds
            if speeds:
                self.statistics.average_speed = sum(speeds) / len(speeds)
                self.statistics.peak_speed = max(self.statistics.peak_speed, max(speeds))
                
                # Estimate remaining time
                remaining_bytes = self.statistics.total_bytes_to_download - self.statistics.total_bytes_downloaded
                if remaining_bytes > 0 and self.statistics.average_speed > 0:
                    self.statistics.estimated_time_remaining = int(remaining_bytes / self.statistics.average_speed)
                else:
                    self.statistics.estimated_time_remaining = 0
            else:
                self.statistics.average_speed = 0.0
                self.statistics.estimated_time_remaining = 0
            
            # Update session duration
            self.statistics.update_session_duration()
    
    def _fire_event(self, event: ProgressEvent):
        """
        Fire progress event to all registered listeners.
        
        Args:
            event: Progress event to fire
        """
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in progress event listener: {e}")
    
    def add_event_listener(self, listener: Callable[[ProgressEvent], None]):
        """
        Add progress event listener.
        
        Args:
            listener: Callback function for progress events
        """
        if listener not in self.event_listeners:
            self.event_listeners.append(listener)
            logger.info(f"Added progress event listener: {listener.__name__}")
    
    def remove_event_listener(self, listener: Callable[[ProgressEvent], None]):
        """
        Remove progress event listener.
        
        Args:
            listener: Callback function to remove
        """
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
            logger.info(f"Removed progress event listener: {listener.__name__}")
    
    def get_progress(self, request_id: str) -> Optional[ProgressInfo]:
        """
        Get current progress for a download.
        
        Args:
            request_id: Download identifier
            
        Returns:
            Current progress or None if not found
        """
        with self._lock:
            return self.active_progress.get(request_id)
    
    def get_all_progress(self) -> Dict[str, ProgressInfo]:
        """
        Get current progress for all active downloads.
        
        Returns:
            Dictionary mapping request IDs to progress info
        """
        with self._lock:
            return self.active_progress.copy()
    
    def get_progress_history(self, request_id: str) -> List[ProgressInfo]:
        """
        Get progress history for a download.
        
        Args:
            request_id: Download identifier
            
        Returns:
            List of progress updates in chronological order
        """
        with self._lock:
            return self.progress_history.get(request_id, []).copy()
    
    def get_statistics(self) -> ProgressStatistics:
        """
        Get current aggregated statistics.
        
        Returns:
            Current statistics snapshot
        """
        with self._lock:
            return ProgressStatistics(
                total_downloads=self.statistics.total_downloads,
                active_downloads=self.statistics.active_downloads,
                completed_downloads=self.statistics.completed_downloads,
                failed_downloads=self.statistics.failed_downloads,
                cancelled_downloads=self.statistics.cancelled_downloads,
                total_bytes_downloaded=self.statistics.total_bytes_downloaded,
                total_bytes_to_download=self.statistics.total_bytes_to_download,
                overall_progress=self.statistics.overall_progress,
                average_speed=self.statistics.average_speed,
                peak_speed=self.statistics.peak_speed,
                estimated_time_remaining=self.statistics.estimated_time_remaining,
                session_start_time=self.statistics.session_start_time,
                session_duration=self.statistics.session_duration
            )
    
    def get_active_download_ids(self) -> List[str]:
        """
        Get list of active download IDs.
        
        Returns:
            List of request IDs for active downloads
        """
        with self._lock:
            return [
                request_id for request_id, progress in self.active_progress.items()
                if progress.status not in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]
            ]
    
    def unregister_progress(self, request_id: str):
        """
        Unregister progress tracking for a completed download.
        
        Args:
            request_id: Download identifier to unregister
        """
        with self._lock:
            if request_id in self.active_progress:
                progress = self.active_progress[request_id]
                
                # Only remove if completed/failed/cancelled
                if progress.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]:
                    del self.active_progress[request_id]
                    
                    # Clean up speed tracking
                    if request_id in self._speed_history:
                        del self._speed_history[request_id]
                    
                    logger.info(f"Unregistered progress tracking for: {request_id}")
                else:
                    logger.warning(f"Cannot unregister active download: {request_id}")
    
    def cleanup_completed(self):
        """Remove all completed downloads from active tracking."""
        with self._lock:
            completed_ids = [
                request_id for request_id, progress in self.active_progress.items()
                if progress.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]
            ]
            
            for request_id in completed_ids:
                self.unregister_progress(request_id)
            
            logger.info(f"Cleaned up {len(completed_ids)} completed downloads")
    
    def reset_statistics(self):
        """Reset all statistics and tracking data."""
        with self._lock:
            self.active_progress.clear()
            self.progress_history.clear()
            self._speed_history.clear()
            self.statistics = ProgressStatistics()
            
            logger.info("Reset all progress statistics and tracking data")
    
    def cleanup(self):
        """Clean up progress manager resources."""
        self.reset_statistics()
        logger.info("Progress manager cleanup completed")