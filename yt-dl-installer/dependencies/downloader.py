"""
Binary download utilities for embedded dependencies.

This module provides functionality to download and extract Python runtime,
yt-dlp, FFmpeg, and install Python packages to embedded site-packages.
"""

import requests
import zipfile
import subprocess
import tempfile
import shutil
import logging
import json
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BinaryDownloader:
    """
    Downloads and installs embedded dependencies for the YouTube Downloader GUI.
    
    Handles downloading Python embeddable distribution, yt-dlp executable,
    FFmpeg binaries, and installing Python packages.
    """
    
    def __init__(self, app_root: Path, progress_callback: Optional[Callable] = None):
        """
        Initialize binary downloader.
        
        Args:
            app_root: Root directory of the application
            progress_callback: Optional callback for progress updates
        """
        self.app_root = Path(app_root)
        self.progress_callback = progress_callback
        self.config = self._load_config()
        
        # Set up directories
        self.python_runtime = self.app_root / self.config["embedded_binaries"]["python_runtime"]["local_path"].lstrip("./")
        self.binaries_dir = self.app_root / "binaries"
        self.temp_dir = self.app_root / "temp"
        
        # Ensure directories exist
        self.binaries_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load application configuration."""
        config_file = self.app_root / "config" / "app_config.json"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def _report_progress(self, message: str, percentage: int = 0):
        """Report progress to callback if provided."""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        logger.info(f"Progress: {message} ({percentage}%)")
    
    def _download_file(self, url: str, destination: Path, description: str = "file") -> bool:
        """
        Download a file with progress tracking.
        
        Args:
            url: URL to download from
            destination: Local file path to save to
            description: Description for progress reporting
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            self._report_progress(f"Starting download of {description}...")
            
            # Create destination directory
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percentage = int((downloaded / total_size) * 100)
                            self._report_progress(f"Downloading {description}", percentage)
            
            self._report_progress(f"Completed download of {description}", 100)
            logger.info(f"Successfully downloaded {description} to {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {description} from {url}: {e}")
            if destination.exists():
                destination.unlink()
            return False
    
    def _extract_zip(self, zip_path: Path, extract_to: Path, description: str = "archive") -> bool:
        """
        Extract a ZIP file with progress tracking.
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to
            description: Description for progress reporting
            
        Returns:
            True if extraction successful, False otherwise
        """
        try:
            self._report_progress(f"Extracting {description}...")
            
            extract_to.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                total_files = len(members)
                
                for i, member in enumerate(members):
                    zip_ref.extract(member, extract_to)
                    percentage = int(((i + 1) / total_files) * 100)
                    self._report_progress(f"Extracting {description}", percentage)
            
            self._report_progress(f"Completed extraction of {description}", 100)
            logger.info(f"Successfully extracted {description} to {extract_to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract {description}: {e}")
            return False
    
    def download_python_runtime(self) -> bool:
        """
        Download and extract Python embedded runtime.
        
        Returns:
            True if successful, False otherwise
        """
        config = self.config["embedded_binaries"]["python_runtime"]
        download_url = config["download_url"]
        
        if self.python_runtime.exists():
            self._report_progress("Python runtime already exists", 100)
            return True
        
        # Download Python embedded zip
        zip_path = self.temp_dir / "python_embedded.zip"
        
        if not self._download_file(download_url, zip_path, "Python runtime"):
            return False
        
        # Extract Python runtime
        if not self._extract_zip(zip_path, self.python_runtime, "Python runtime"):
            return False
        
        # Configure Python path file for imports
        if not self._configure_python_path():
            return False
        
        # Clean up zip file
        if zip_path.exists():
            zip_path.unlink()
        
        return True
    
    def _configure_python_path(self) -> bool:
        """
        Configure Python path file for embedded runtime.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the correct .pth file name
            pth_files = list(self.python_runtime.glob("python*._pth"))
            
            if not pth_files:
                logger.error("No Python path file found in embedded runtime")
                return False
            
            pth_file = pth_files[0]
            
            # Configure path for site-packages imports
            pth_content = [
                "python313.zip",
                ".",
                "Lib",
                "Lib/site-packages",
                "",
                "# Uncomment to run site.main() automatically",
                "import site"
            ]
            
            with open(pth_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(pth_content))
            
            logger.info(f"Configured Python path file: {pth_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure Python path: {e}")
            return False
    
    def download_yt_dlp(self) -> bool:
        """
        Download yt-dlp executable.
        
        Returns:
            True if successful, False otherwise
        """
        config = self.config["embedded_binaries"]["yt_dlp"]
        download_url = config["download_url"]
        yt_dlp_path = self.binaries_dir / "yt-dlp.exe"
        
        if yt_dlp_path.exists():
            self._report_progress("yt-dlp already exists", 100)
            return True
        
        return self._download_file(download_url, yt_dlp_path, "yt-dlp executable")
    
    def download_ffmpeg(self) -> bool:
        """
        Download and extract FFmpeg binaries.
        
        Returns:
            True if successful, False otherwise
        """
        config = self.config["embedded_binaries"]["ffmpeg"]
        download_url = config["download_url"]
        ffmpeg_dir = self.binaries_dir / "ffmpeg"
        
        if ffmpeg_dir.exists():
            self._report_progress("FFmpeg already exists", 100)
            return True
        
        # Download FFmpeg zip
        zip_path = self.temp_dir / "ffmpeg.zip"
        
        if not self._download_file(download_url, zip_path, "FFmpeg"):
            return False
        
        # Extract to temporary location first
        temp_extract = self.temp_dir / "ffmpeg_extract"
        if not self._extract_zip(zip_path, temp_extract, "FFmpeg"):
            return False
        
        # Find the actual FFmpeg directory (usually nested)
        ffmpeg_dirs = list(temp_extract.glob("ffmpeg-*"))
        if not ffmpeg_dirs:
            logger.error("No FFmpeg directory found in extracted archive")
            return False
        
        source_dir = ffmpeg_dirs[0]
        
        # Move to final location
        try:
            shutil.move(str(source_dir), str(ffmpeg_dir))
            self._report_progress("FFmpeg installation complete", 100)
        except Exception as e:
            logger.error(f"Failed to move FFmpeg to final location: {e}")
            return False
        
        # Clean up
        if zip_path.exists():
            zip_path.unlink()
        if temp_extract.exists():
            shutil.rmtree(temp_extract, ignore_errors=True)
        
        return True
    
    def install_python_packages(self, package_list: str) -> bool:
        """
        Install Python packages to embedded site-packages.
        
        Args:
            package_list: Either "pyqt6" or "yt_dlp_python" from config
            
        Returns:
            True if successful, False otherwise
        """
        if package_list not in ["pyqt6", "yt_dlp_python"]:
            logger.error(f"Invalid package list: {package_list}")
            return False
        
        # Check if Python runtime exists
        python_exe = self.python_runtime / "python.exe"
        if not python_exe.exists():
            logger.error("Python runtime not found")
            return False
        
        config = self.config["embedded_binaries"][package_list]
        packages = config["wheel_packages"]
        target_dir = self.python_runtime / "Lib" / "site-packages"
        
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            total_packages = len(packages)
            for i, package in enumerate(packages):
                self._report_progress(f"Installing {package}", int((i / total_packages) * 100))
                
                # Install package with pip
                result = subprocess.run([
                    str(python_exe), "-m", "pip", "install",
                    "--target", str(target_dir),
                    "--no-deps" if package_list == "pyqt6" else "",
                    package
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    logger.error(f"Failed to install {package}: {result.stderr}")
                    return False
                
                logger.info(f"Successfully installed {package}")
            
            self._report_progress(f"Completed installing {package_list} packages", 100)
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Package installation timed out for {package_list}")
            return False
        except Exception as e:
            logger.error(f"Failed to install {package_list} packages: {e}")
            return False
    
    def download_all_dependencies(self) -> bool:
        """
        Download and install all required dependencies.
        
        Returns:
            True if all successful, False if any failed
        """
        steps = [
            ("Python runtime", self.download_python_runtime),
            ("yt-dlp executable", self.download_yt_dlp),
            ("FFmpeg binaries", self.download_ffmpeg),
            ("PyQt6 packages", lambda: self.install_python_packages("pyqt6")),
            ("yt-dlp Python packages", lambda: self.install_python_packages("yt_dlp_python"))
        ]
        
        for step_name, step_func in steps:
            self._report_progress(f"Starting {step_name} installation...")
            
            try:
                if not step_func():
                    logger.error(f"Failed to install {step_name}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error installing {step_name}: {e}")
                return False
        
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self._report_progress("All dependencies installed successfully!", 100)
        return True