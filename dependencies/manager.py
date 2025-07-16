"""
Embedded dependency management system.

This module provides functionality to check and manage embedded Python runtime,
PyQt6, yt-dlp, FFmpeg and other required dependencies for the portable application.
"""

import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class EmbeddedDependencyManager:
    """
    Manages embedded dependencies for the YouTube Downloader GUI.
    
    Handles checking, installing, and configuring embedded Python runtime,
    PyQt6, yt-dlp, FFmpeg and related dependencies.
    """
    
    def __init__(self, app_root: Path):
        """
        Initialize dependency manager.
        
        Args:
            app_root: Root directory of the application
        """
        self.app_root = Path(app_root)
        self.config_file = self.app_root / "config" / "app_config.json"
        self.config = self._load_config()
        
        # Set up paths from configuration
        self.python_runtime = self.app_root / self.config["embedded_binaries"]["python_runtime"]["local_path"].lstrip("./")
        self.binaries_dir = self.app_root / "binaries"
        self.site_packages = self.python_runtime / "Lib" / "site-packages"
        
    def _load_config(self) -> Dict:
        """Load application configuration."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def check_python_runtime(self) -> Dict:
        """
        Check if embedded Python runtime is available and functional.
        
        Returns:
            Dict containing availability status, version, and path information
        """
        python_exe = self.python_runtime / "python.exe"
        
        if not python_exe.exists():
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": f"Python executable not found at {python_exe}"
            }
        
        try:
            # Test Python execution
            result = subprocess.run(
                [str(python_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "available": True,
                    "version": version,
                    "path": str(python_exe),
                    "reason": "Python runtime is functional"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": str(python_exe),
                    "reason": f"Python failed to execute: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "path": str(python_exe),
                "reason": "Python execution timed out"
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": str(python_exe),
                "reason": f"Error testing Python: {str(e)}"
            }
    
    def check_yt_dlp_executable(self) -> Dict:
        """
        Check if embedded yt-dlp.exe is available and functional.
        
        Returns:
            Dict containing availability status, version, and path information
        """
        yt_dlp_exe = self.binaries_dir / "yt-dlp.exe"
        
        if not yt_dlp_exe.exists():
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": f"yt-dlp.exe not found at {yt_dlp_exe}"
            }
        
        try:
            # Test yt-dlp execution
            result = subprocess.run(
                [str(yt_dlp_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "available": True,
                    "version": version,
                    "path": str(yt_dlp_exe),
                    "reason": "yt-dlp executable is functional"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": str(yt_dlp_exe),
                    "reason": f"yt-dlp failed to execute: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "path": str(yt_dlp_exe),
                "reason": "yt-dlp execution timed out"
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": str(yt_dlp_exe),
                "reason": f"Error testing yt-dlp: {str(e)}"
            }
    
    def check_ffmpeg(self) -> Dict:
        """
        Check if embedded FFmpeg binaries are available and functional.
        
        Returns:
            Dict containing availability status, version, and path information
        """
        ffmpeg_exe = self.binaries_dir / "ffmpeg" / "bin" / "ffmpeg.exe"
        ffprobe_exe = self.binaries_dir / "ffmpeg" / "bin" / "ffprobe.exe"
        
        if not ffmpeg_exe.exists():
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": f"ffmpeg.exe not found at {ffmpeg_exe}"
            }
        
        if not ffprobe_exe.exists():
            return {
                "available": False,
                "version": None,
                "path": str(ffmpeg_exe),
                "reason": f"ffprobe.exe not found at {ffprobe_exe}"
            }
        
        try:
            # Test FFmpeg execution
            result = subprocess.run(
                [str(ffmpeg_exe), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extract version from output
                output_lines = result.stdout.split('\n')
                version_line = next((line for line in output_lines if 'ffmpeg version' in line), '')
                version = version_line.split(' ')[2] if version_line else "Unknown"
                
                return {
                    "available": True,
                    "version": version,
                    "path": str(ffmpeg_exe),
                    "ffprobe_path": str(ffprobe_exe),
                    "reason": "FFmpeg binaries are functional"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": str(ffmpeg_exe),
                    "reason": f"FFmpeg failed to execute: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "path": str(ffmpeg_exe),
                "reason": "FFmpeg execution timed out"
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": str(ffmpeg_exe),
                "reason": f"Error testing FFmpeg: {str(e)}"
            }
    
    def check_pyqt6(self) -> Dict:
        """
        Check if PyQt6 is installed in embedded Python environment.
        
        Returns:
            Dict containing availability status and installation information
        """
        python_status = self.check_python_runtime()
        if not python_status["available"]:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": "Python runtime not available"
            }
        
        python_exe = Path(python_status["path"])
        
        try:
            # Check if PyQt6 can be imported
            result = subprocess.run(
                [str(python_exe), "-c", "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "available": True,
                    "version": version,
                    "path": str(self.site_packages / "PyQt6"),
                    "reason": "PyQt6 is installed and importable"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": None,
                    "reason": f"PyQt6 import failed: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": "PyQt6 import test timed out"
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": f"Error testing PyQt6: {str(e)}"
            }
    
    def check_yt_dlp_python(self) -> Dict:
        """
        Check if yt-dlp Python library is installed in embedded environment.
        
        Returns:
            Dict containing availability status and installation information
        """
        python_status = self.check_python_runtime()
        if not python_status["available"]:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": "Python runtime not available"
            }
        
        python_exe = Path(python_status["path"])
        
        try:
            # Check if yt-dlp can be imported
            result = subprocess.run(
                [str(python_exe), "-c", "import yt_dlp; print(yt_dlp.version.__version__)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "available": True,
                    "version": version,
                    "path": str(self.site_packages / "yt_dlp"),
                    "reason": "yt-dlp Python library is installed and importable"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": None,
                    "reason": f"yt-dlp import failed: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": "yt-dlp import test timed out"
            }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": None,
                "reason": f"Error testing yt-dlp: {str(e)}"
            }
    
    def check_all_dependencies(self) -> Dict:
        """
        Check all embedded dependencies.
        
        Returns:
            Dict containing status of all dependencies
        """
        results = {
            "python_runtime": self.check_python_runtime(),
            "yt_dlp_executable": self.check_yt_dlp_executable(),
            "ffmpeg": self.check_ffmpeg(),
            "pyqt6": self.check_pyqt6(),
            "yt_dlp_python": self.check_yt_dlp_python()
        }
        
        # Calculate overall status
        all_available = all(dep["available"] for dep in results.values())
        missing_deps = [name for name, dep in results.items() if not dep["available"]]
        
        results["overall"] = {
            "all_available": all_available,
            "missing_dependencies": missing_deps,
            "ready_to_run": all_available
        }
        
        return results
    
    def get_missing_dependencies(self) -> List[str]:
        """
        Get list of missing dependencies.
        
        Returns:
            List of missing dependency names
        """
        status = self.check_all_dependencies()
        return status["overall"]["missing_dependencies"]
    
    def is_ready(self) -> bool:
        """
        Check if all dependencies are available and application is ready to run.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        status = self.check_all_dependencies()
        return status["overall"]["ready_to_run"]