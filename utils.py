# utils.py
import os
from typing import List, Union
from config_manager import COOKIE_FILE_PATH, FFMPEG_PATH, VIDEO_DIR # Import paths from config_manager

# Configuration paths (now imported)
LOGO_PATH = os.path.join(os.path.dirname(__file__), "Res", "logo.png")
ICON_PATH = os.path.join(os.path.dirname(__file__), "Res", "icon.ico")

def check_dependencies() -> List[str]:
    """Check for required files"""
    errors = []
    if not os.path.exists(COOKIE_FILE_PATH):
        errors.append(f"Cookie file not found: {COOKIE_FILE_PATH}\nPlease export YouTube cookies.")
    if not os.path.exists(FFMPEG_PATH):
        errors.append(f"FFmpeg not found: {FFMPEG_PATH}\nPlease place ffmpeg.exe next to the program.")
    if not os.path.exists(LOGO_PATH):
        errors.append(f"Logo not found: {LOGO_PATH}\nPlease place logo.png in Res folder.")
    if not os.path.exists(ICON_PATH):
        errors.append(f"Icon not found: {ICON_PATH}\nPlease place icon.ico in Res folder.")
    return errors

def format_bytes(bytes_value: Union[int, float]) -> str:
    """Format bytes to human readable format (e.g., KB, MB, GB)"""
    if bytes_value is None or bytes_value == 0:
        return "0.00 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

# Define a custom exception for cancellation
class DownloadCanceledException(Exception):
    pass