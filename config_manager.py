# config_manager.py
import json
import os
from typing import Dict, Any

# Configuration paths
DOWNLOAD_DIR = os.path.join(os.getcwd(), "YouTube_Downloads")
VIDEO_DIR = os.path.join(DOWNLOAD_DIR, "Videos")
AUDIO_DIR = os.path.join(DOWNLOAD_DIR, "Audios") # Still defined for potential future use or checks

COOKIE_FILE_PATH = os.path.join(os.getcwd(), "cookies.txt")
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
CONFIG_FILE = os.path.join(os.getcwd(), "config.json")

def ensure_directories():
    """Create necessary directories."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    # os.makedirs(AUDIO_DIR, exist_ok=True) # Only VIDEO_DIR is used now

def load_config() -> Dict[str, Any]:
    """Load settings from config.json"""
    default_config = {
        "theme": "dark",
        "download_dir": DOWNLOAD_DIR
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        else:
            return default_config
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_config

def save_config(config: Dict[str, Any]) -> None:
    """Save settings to config.json"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")