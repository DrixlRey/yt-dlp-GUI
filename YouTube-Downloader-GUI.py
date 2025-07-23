#!/usr/bin/env python3
"""
Main application entry point for YouTube Downloader GUI - System Installation Version.

This module uses system-wide installations of Python, PyQt6, FFmpeg, and yt-dlp
instead of embedded dependencies. All components are expected to be installed
via the NSIS installer.

Usage:
    python YouTube-Downloader-GUI.py
"""

import sys
import os
import json
import traceback
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Hide CMD window on Windows (2-line solution)
try:
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    pass  # Silently fail on non-Windows or if unable to hide

# Get application directory
script_dir = Path(__file__).parent.absolute()

# Add current directory to path for local imports
sys.path.insert(0, str(script_dir))

# Verify PyQt6 availability early
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
except ImportError as e:
    print("=" * 60)
    print("ERROR: PyQt6 not available")
    print("=" * 60)
    print(f"Import error: {e}")
    print()
    print("This application requires PyQt6 to be installed system-wide.")
    print("Please run the YouTube Downloader GUI installer to install all dependencies.")
    print("=" * 60)
    
    # Try to show a basic error dialog if possible
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Dependencies Missing",
            "PyQt6 is not installed system-wide.\n\n"
            "Please run the YouTube Downloader GUI installer to install all dependencies."
        )
    except ImportError:
        pass
    
    sys.exit(1)

# Import application modules after environment setup
try:
    from gui.main_window import MainWindow
    from downloader.core import YouTubeDownloader
    from downloader.progress import ProgressManager
    from gui.workers import WorkerManager
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Please ensure all files are present and the application is properly installed.")
    sys.exit(1)


class SystemDependencyManager:
    """
    Manager for system-wide dependencies (Python, PyQt6, FFmpeg, yt-dlp).
    
    This replaces the EmbeddedDependencyManager for system installations.
    """
    
    def __init__(self, app_root: Path):
        """Initialize system dependency manager."""
        self.app_root = app_root
    
    def check_all_dependencies(self) -> Dict[str, Any]:
        """
        Check if all required system dependencies are available.
        
        Returns:
            Dictionary with dependency status information
        """
        status = {
            "python": self._check_python(),
            "pyqt6": self._check_pyqt6(),
            "ffmpeg": self._check_ffmpeg(),
            "ytdlp": self._check_ytdlp()
        }
        
        # Overall status
        all_available = all(dep["available"] for dep in status.values())
        missing_dependencies = [name for name, dep in status.items() if not dep["available"]]
        
        status["overall"] = {
            "all_available": all_available,
            "missing_dependencies": missing_dependencies
        }
        
        return status
    
    def _check_python(self) -> Dict[str, Any]:
        """Check Python availability."""
        try:
            version = sys.version_info
            return {
                "available": True,
                "version": f"{version.major}.{version.minor}.{version.micro}",
                "path": sys.executable
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_pyqt6(self) -> Dict[str, Any]:
        """Check PyQt6 availability."""
        try:
            import PyQt6.QtCore
            return {
                "available": True,
                "version": PyQt6.QtCore.qVersion(),
                "location": PyQt6.__file__
            }
        except ImportError as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_ffmpeg(self) -> Dict[str, Any]:
        """Check FFmpeg availability in system PATH."""
        try:
            # Check if ffmpeg is in PATH
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                # Get version
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Extract version from first line
                    first_line = result.stdout.split('\n')[0]
                    version = first_line.split()[2] if len(first_line.split()) > 2 else "unknown"
                    return {
                        "available": True,
                        "version": version,
                        "path": ffmpeg_path
                    }
            
            return {
                "available": False,
                "error": "FFmpeg not found in system PATH"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _check_ytdlp(self) -> Dict[str, Any]:
        """Check yt-dlp availability."""
        try:
            import yt_dlp
            return {
                "available": True,
                "version": yt_dlp.version.__version__,
                "location": yt_dlp.__file__
            }
        except ImportError:
            # Try command line version
            try:
                ytdlp_path = shutil.which("yt-dlp")
                if ytdlp_path:
                    result = subprocess.run(
                        ["yt-dlp", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        return {
                            "available": True,
                            "version": result.stdout.strip(),
                            "path": ytdlp_path
                        }
                
                return {
                    "available": False,
                    "error": "yt-dlp not found (neither Python module nor command line)"
                }
            except Exception as e:
                return {
                    "available": False,
                    "error": str(e)
                }


class ApplicationManager:
    """
    Main application manager for YouTube Downloader GUI - System Installation Version.
    
    Handles application lifecycle, configuration loading, and coordination
    between GUI components and download engine using system-wide dependencies.
    """
    
    def __init__(self):
        """Initialize application manager."""
        self.app_root = script_dir
        self.config: Dict[str, Any] = {}
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.downloader: Optional[YouTubeDownloader] = None
        self.progress_manager: Optional[ProgressManager] = None
        self.worker_manager: Optional[WorkerManager] = None
        self.dependency_manager: Optional[SystemDependencyManager] = None
        
        print("ApplicationManager initialized (System Installation)")
    
    def _load_configuration(self) -> bool:
        """
        Load application configuration from JSON file.
        
        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            config_path = self.app_root / "config" / "app_config.json"
            
            if not config_path.exists():
                print(f"Configuration file not found: {config_path}")
                # Create default configuration for system installation
                self._create_default_config(config_path)
            
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            
            # Update configuration for system installation
            self._update_config_for_system_install()
            
            print("Configuration loaded successfully")
            return True
            
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def _create_default_config(self, config_path: Path) -> None:
        """Create default configuration file for system installation."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            "system_binaries": {
                "ffmpeg_exe": "ffmpeg",  # Use system PATH
                "ffprobe_exe": "ffprobe",  # Use system PATH
                "ytdlp_module": "yt_dlp"  # Use Python module
            },
            "download_settings": {
                "default_format": "best[height<=1080]",
                "default_output_dir": str(self.app_root / "downloads"),
                "max_concurrent_downloads": 3,
                "retry_attempts": 3
            },
            "gui_settings": {
                "style": "Fusion",
                "window_size": [1200, 800],
                "remember_window_state": True
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    def _update_config_for_system_install(self) -> None:
        """Update configuration to use system-wide installations."""
        # Replace embedded_binaries with system_binaries
        if "embedded_binaries" in self.config:
            del self.config["embedded_binaries"]
        
        if "system_binaries" not in self.config:
            self.config["system_binaries"] = {
                "ffmpeg_exe": "ffmpeg",
                "ffprobe_exe": "ffprobe", 
                "ytdlp_module": "yt_dlp"
            }
    
    def _check_dependencies(self) -> bool:
        """
        Check if all required system dependencies are available.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            self.dependency_manager = SystemDependencyManager(self.app_root)
            status = self.dependency_manager.check_all_dependencies()
            
            overall_status = status.get("overall", {})
            all_available = overall_status.get("all_available", False)
            
            if not all_available:
                missing = overall_status.get("missing_dependencies", [])
                print(f"Missing system dependencies: {', '.join(missing)}")
                self._show_dependency_error(missing, status)
                return False
            
            print("All system dependencies are available")
            return True
            
        except Exception as e:
            print(f"Error checking system dependencies: {e}")
            return False
    
    def _show_dependency_error(self, missing: list, status: dict) -> None:
        """Show error dialog for missing dependencies."""
        try:
            # Create temporary application for error dialog
            temp_app = QApplication([]) if not QApplication.instance() else None
            
            error_message = "Missing system dependencies:\n\n"
            
            for dep in missing:
                dep_status = status.get(dep, {})
                error = dep_status.get("error", "Not found")
                error_message += f"• {dep.upper()}: {error}\n"
            
            error_message += "\nPlease run the YouTube Downloader GUI installer to install all required dependencies."
            
            QMessageBox.critical(
                None, "System Dependencies Missing", error_message
            )
            
            if temp_app:
                temp_app.quit()
                
        except Exception as e:
            print(f"Error showing dependency error dialog: {e}")
    
    def _initialize_components(self) -> bool:
        """
        Initialize core application components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize progress manager
            self.progress_manager = ProgressManager()
            
            # Initialize downloader with system binaries
            system_config = self.config.get("system_binaries", {})
            self.downloader = YouTubeDownloader(
                app_root=self.app_root,
                config=system_config
            )
            
            # Initialize worker manager
            cache_dir = self.app_root / "cache"
            cache_dir.mkdir(exist_ok=True)
            
            self.worker_manager = WorkerManager(
                self.downloader,
                self.progress_manager,
                cache_dir
            )
            
            print("Core components initialized successfully")
            return True
            
        except Exception as e:
            print(f"Error initializing components: {e}")
            return False
    
    def _create_gui(self) -> bool:
        """
        Create and configure the main GUI application.
        
        Returns:
            True if GUI created successfully, False otherwise
        """
        try:
            # Configure high DPI settings before creating QApplication
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("YouTube Downloader GUI")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("YouTube Downloader")
            
            # Set application icon if available
            icon_path = self.app_root / "app.ico"
            if icon_path.exists():
                self.app.setWindowIcon(QIcon(str(icon_path)))
            
            # Apply application style
            gui_config = self.config.get("gui_settings", {})
            style_name = gui_config.get("style", "Fusion")
            
            from PyQt6.QtWidgets import QStyleFactory
            available_styles = QStyleFactory.keys()
            if style_name in available_styles:
                self.app.setStyle(style_name)
                print(f"Applied style: {style_name}")
            
            # Create main window
            self.main_window = MainWindow(
                config=self.config,
                app_root=self.app_root
            )
            
            # Connect main window to core components
            self.main_window.set_downloader(self.downloader)
            self.main_window.set_progress_manager(self.progress_manager)
            self.main_window.set_worker_manager(self.worker_manager)
            self.main_window.set_dependency_manager(self.dependency_manager)
            
            print("GUI created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating GUI: {e}")
            return False
    
    def run(self) -> int:
        """
        Run the main application.
        
        Returns:
            Application exit code
        """
        try:
            print("Starting YouTube Downloader GUI (System Installation)")
            
            # Load configuration
            if not self._load_configuration():
                self._show_error("Configuration Error", 
                               "Failed to load application configuration.")
                return 1
            
            # Check system dependencies
            if not self._check_dependencies():
                print("System dependencies check failed")
                return 1
            
            # Initialize core components
            if not self._initialize_components():
                self._show_error("Initialization Error",
                               "Failed to initialize application components.")
                return 1
            
            # Create GUI
            if not self._create_gui():
                self._show_error("GUI Error",
                               "Failed to create application interface.")
                return 1
            
            # Show main window and run application
            self.main_window.show()
            print("Application started successfully")
            
            # Run application event loop
            exit_code = self.app.exec()
            
            print(f"Application exiting with code: {exit_code}")
            return exit_code
            
        except KeyboardInterrupt:
            print("Application interrupted by user")
            return 130
        except Exception as e:
            print(f"Unexpected error in application: {e}")
            self._show_error("Application Error", 
                           f"An unexpected error occurred:\n{str(e)}")
            return 1
        finally:
            self._cleanup()
    
    def _show_error(self, title: str, message: str):
        """Show error message to user."""
        try:
            if self.app and self.main_window:
                QMessageBox.critical(self.main_window, title, message)
            else:
                # Create temporary application for error dialog
                temp_app = QApplication([]) if not QApplication.instance() else None
                QMessageBox.critical(None, title, message)
                if temp_app:
                    temp_app.quit()
        except Exception:
            # Fallback to console output
            print(f"ERROR - {title}: {message}")
    
    def _cleanup(self):
        """Clean up application resources."""
        try:
            print("Cleaning up application resources")
            
            # Stop worker manager
            if self.worker_manager:
                self.worker_manager.cleanup()
            
            # Clean up progress manager
            if self.progress_manager:
                self.progress_manager.cleanup()
            
            # Close main window
            if self.main_window:
                self.main_window.close()
            
            # Quit application
            if self.app:
                self.app.quit()
            
            print("Application cleanup completed")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point for the application."""
    # Handle uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        print(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
        
        # Try to show error dialog
        try:
            app = QApplication.instance()
            if app:
                QMessageBox.critical(
                    None, "Unexpected Error",
                    f"An unexpected error occurred:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Please check the log files for more details."
                )
        except Exception:
            pass
    
    sys.excepthook = handle_exception
    
    # Create and run application
    app_manager = ApplicationManager()
    exit_code = app_manager.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()