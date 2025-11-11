# downloader.py
import yt_dlp
import os
import threading
from typing import Dict, Any, Optional, Callable
from utils import DownloadCanceledException, format_bytes # Import exception and util functions
from config_manager import VIDEO_DIR, COOKIE_FILE_PATH, FFMPEG_PATH # Import paths from config_manager

class DownloadManager:
    def __init__(self, progress_hook: Callable[[Dict[str, Any]], None], cancel_event: threading.Event):
        self.progress_hook = progress_hook
        self._download_canceled = cancel_event
        self.current_download_process: Optional[yt_dlp.YoutubeDL] = None

    def fetch_video_info(self, url: str) -> Dict[str, Any]:
        """Fetch video information using yt_dlp"""
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'cookiefile': COOKIE_FILE_PATH,
            'nocheckcertificate': True,
            'ffmpeg_location': FFMPEG_PATH
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info

    def start_download(self, info: Dict[str, Any], resolution: int, filename: str):
        """Start the download process in the current thread"""
        # Clear the cancel flag at the start of a new download (if needed by caller)
        # self._download_canceled.clear() # Typically cleared by the GUI before calling this

        target_dir = VIDEO_DIR

        # Updated format string to prioritize combined formats for smoother progress
        ydl_opts = {
            # Prioritize combined format (b) for smoother progress, fallback to bestvideo+bestaudio (bv+ba)
            # Using 'bv*' and 'ba' tries to get best separate streams, but if they don't exist or cause issues,
            # the '/b[...]' part ensures a combined format is used as a backup, which usually results in smoother progress.
            # This is a good compromise between quality and progress bar stability.
            'format': f'bv*[height<={resolution}][ext=mp4]+ba[ext=m4a]/b[height<={resolution}][ext=mp4]',
            'outtmpl': os.path.join(target_dir, f'{filename}.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'cookiefile': COOKIE_FILE_PATH,
            'nocheckcertificate': True,
            'ffmpeg_location': FFMPEG_PATH
        }

        # Merge video and audio if they are downloaded separately (this is the default behavior if bv+ba is selected)
        # If b (combined) is selected, this step might be skipped by yt-dlp internally as it's already combined.
        # ydl_opts['merge_output_format'] = 'mp4' # This line is often not needed if 'format' specifies ext=mp4 correctly
        # or is handled automatically when bv+ba is muxed.

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_download_process = ydl
                ydl.download([info['webpage_url']])
                # Check the cancel flag after download finishes
                if self._download_canceled.is_set():
                    # If canceled during download, raise exception to be handled by caller
                    raise DownloadCanceledException("Download canceled by user after completion.")
                # Success is handled by the caller
        except DownloadCanceledException:
            # Re-raise to be handled by the caller (GUI)
            raise
        except Exception as e:
            # Raise other exceptions to be handled by the caller (GUI)
            raise e
        finally:
            self.current_download_process = None