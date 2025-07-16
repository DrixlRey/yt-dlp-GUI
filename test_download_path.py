#!/usr/bin/env python3
"""
Test script to check download path resolution without GUI dependencies
"""
import sys
import os
import json
from pathlib import Path

# Simulate the path resolution logic
def get_configured_download_path():
    """Get the configured download path from settings."""
    script_dir = Path(__file__).parent
    
    print(f"DEBUG: get_configured_download_path() called")
    print(f"DEBUG: Script directory: {script_dir}")
    
    # Check JSON config file
    try:
        config_file = script_dir / "config" / "app_config.json"
        print(f"DEBUG: Checking config file: {config_file}")
        print(f"DEBUG: Config file exists: {config_file.exists()}")
        
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
                    print(f"DEBUG: Using config file path: {path}")
                    return path
    except Exception as e:
        print(f"DEBUG: Config file error: {e}")
    
    # Fall back to user's Downloads folder
    try:
        downloads_path = Path.home() / "Downloads"
        print(f"DEBUG: Using fallback Downloads path: {downloads_path}")
        return downloads_path
    except Exception as e:
        print(f"DEBUG: Downloads fallback error: {e}")
        # Final fallback to app directory
        default_path = script_dir / "downloads"
        print(f"DEBUG: Using final fallback path: {default_path}")
        return default_path

def main():
    print("Testing download path resolution...")
    print("=" * 50)
    
    # Test path resolution
    download_path = get_configured_download_path()
    
    print(f"\nResults:")
    print(f"Selected path: {download_path}")
    print(f"Absolute path: {download_path.resolve()}")
    print(f"Path exists: {download_path.exists()}")
    print(f"Path is directory: {download_path.is_dir()}")
    
    # Test creating the directory
    try:
        download_path.mkdir(parents=True, exist_ok=True)
        print(f"Directory created/exists: {download_path.exists()}")
        print(f"Directory is writable: {os.access(download_path, os.W_OK)}")
    except Exception as e:
        print(f"Error creating directory: {e}")
    
    # Test yt-dlp template
    output_template = str(download_path / '%(title)s.%(ext)s')
    print(f"yt-dlp output template: {output_template}")

if __name__ == "__main__":
    main()