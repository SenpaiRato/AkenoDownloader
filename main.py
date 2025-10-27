import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import yt_dlp
import os
import re
import threading
import sys
import json
from typing import Any, Dict, Optional, Union
from PIL import Image
import logging

# Suppress verbose yt-dlp logging to reduce console spam from warnings
logging.getLogger("yt_dlp").setLevel(logging.ERROR)

# --- Resource Helper (for .exe compatibility) ---
def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Paths ---
DOWNLOAD_DIR = os.path.join(os.getcwd(), "YouTube_Downloads")
VIDEO_DIR = os.path.join(DOWNLOAD_DIR, "Videos")
COOKIE_FILE_PATH = os.path.join(os.getcwd(), "cookies.txt")
FFMPEG_PATH = get_resource_path("ffmpeg.exe")
LOGO_PATH = get_resource_path(os.path.join("Res", "logo.png"))
CONFIG_FILE = os.path.join(os.getcwd(), "config.json")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

# --- Config ---
def load_config():
    default = {"theme": "dark"}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return {k: cfg.get(k, v) for k, v in default.items()}
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return default

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except:
        pass # Silently fail on config save error to prevent app crash

# --- Main App ---
class YouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        ctk.set_appearance_mode(self.config["theme"])
        self.title("🎥 Akeno Downloader")
        self.geometry("700x650")
        self.resizable(False, False)
        self.current_download_process: Optional[yt_dlp.YoutubeDL] = None
        self._last_progress = (-1, "", "") # Track last update to avoid redundant updates
        self._is_downloading = False # Flag to track if a download is active
        self._download_thread = None # Reference to the current download thread

        # Check deps
        errors = []
        for path, name in [(COOKIE_FILE_PATH, "cookies.txt"), (FFMPEG_PATH, "ffmpeg.exe"), (LOGO_PATH, "logo.png")]:
            if not os.path.exists(path):
                errors.append(f"{name} not found. Please place it next to the program.")
        if errors:
            messagebox.showerror("Startup Error", "\n\n".join(errors))
            sys.exit(1)

        # --- UI ---
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self)
        header.pack(pady=20, padx=40, fill="x")
        try:
            logo = ctk.CTkImage(Image.open(LOGO_PATH), size=(50, 50))
            ctk.CTkLabel(header, text="", image=logo, width=50, height=50).pack(side="left", padx=5)
        except:
            pass
        ctk.CTkLabel(header, text="Akeno Downloader", font=("Segoe UI", 16, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(header, text="☕ Buy Me a Coffee", font=("Segoe UI", 12, "bold"),
                      fg_color="#FFA500", hover_color="#FF8C00", text_color="black",
                      command=self._open_coffee).pack(side="left", padx=5)
        self.mode_btn = ctk.CTkButton(header, text="☀️ Light Mode" if self.config["theme"] == "dark" else "🌙 Dark Mode",
                                      width=120, font=("Segoe UI", 10), command=self._toggle_mode)
        self.mode_btn.pack(side="right")

        # Input
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(pady=10, padx=40, fill="x")
        self.url_entry = ctk.CTkEntry(input_frame, placeholder_text="Paste YouTube URL here...", height=40)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        self._setup_shortcuts()
        ctk.CTkButton(input_frame, text="⬇️ Download", width=120, font=("Segoe UI", 12, "bold"),
                      command=self._ask_format).pack(side="left", padx=5)

        # Selection
        self.sel_frame = ctk.CTkFrame(self)
        self.sel_frame.pack(pady=10, padx=40, fill="x")
        self.sel_label = ctk.CTkLabel(self.sel_frame, text="Enter URL and click Download to start", text_color="gray")
        self.sel_label.pack(pady=20)

        # Info
        info_frame = ctk.CTkFrame(self, corner_radius=10)
        info_frame.pack(pady=15, padx=40, fill="x")
        self.title_label = ctk.CTkLabel(info_frame, text="No video loaded", wraplength=600)
        self.title_label.pack(pady=5)

        # Progress
        self.progress = ctk.CTkProgressBar(self, width=500, progress_color="#32CD32")
        self.progress.set(0)
        self.progress.pack(pady=20)
        self.info_label = ctk.CTkLabel(self, text="0.0 MB / 0.0 MB | 0%", text_color="white")
        self.info_label.pack(pady=5)
        self.speed_label = ctk.CTkLabel(self, text="Speed: - | ETA: -", text_color="gray")
        self.speed_label.pack()

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="📂 Open Folder", width=120, height=40,
                      command=self._open_folder).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="🗑️ Clear All", width=150, height=40,
                      command=self._clear_all).pack(side="left", padx=10)

        # Status & Footer
        self.status = ctk.CTkLabel(self, text="Ready", text_color="green")
        self.status.pack(side="bottom", pady=10)
        ctk.CTkLabel(self, text="Made by SenpaiRato", font=("Segoe UI", 8), text_color="gray").place(x=10, y=620)

    def _setup_shortcuts(self):
        try:
            e = self.url_entry._entry
            e.bind("<Control-v>", self._paste)
            e.bind("<Control-a>", self._select_all)
        except:
            pass
        ctk.CTkButton(self.url_entry.master, text="📋", width=30, command=self._manual_paste).pack(side="left", padx=(5,0))

    def _paste(self, _=None):
        try:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, self.clipboard_get())
        except:
            pass
        return "break"

    def _select_all(self, _=None):
        self.url_entry.select_range(0, tk.END)
        return "break"

    def _manual_paste(self):
        self._paste()

    def _toggle_mode(self):
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.config["theme"] = new_mode.lower()
        self.mode_btn.configure(text="🌙 Dark Mode" if new_mode == "Light" else "☀️ Light Mode")
        save_config(self.config)

    def _open_folder(self):
        try:
            os.startfile(DOWNLOAD_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder.\n{e}")

    def _clear_all(self):
        # Stop any ongoing download process
        if self.current_download_process:
            # There's no direct way to stop yt-dlp, but setting the variable to None
            # will prevent further interaction. The download might continue in the background
            # until completion or error, but the UI will be reset.
            self.current_download_process = None
            self._is_downloading = False
            # If you have a reference to the thread, you could potentially join it
            # but it's often safer to let it finish or fail naturally.
            # self._download_thread.join(timeout=0.1) # This is usually not recommended

        # Clear temporary files
        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith('.part'):
                try:
                    os.remove(os.path.join(DOWNLOAD_DIR, f))
                except:
                    pass

        # Reset UI elements
        self.url_entry.delete(0, tk.END)
        self._reset_selection_frame()
        self._reset_info()
        self._reset_progress()
        self.status.configure(text="Cleared")

        # Reset internal state
        self._last_progress = (-1, "", "")
        self._is_downloading = False
        self._download_thread = None

    def _reset_selection_frame(self):
        """Reset the selection frame UI."""
        for w in self.sel_frame.winfo_children():
            w.destroy()
        self.sel_label = ctk.CTkLabel(
            self.sel_frame,
            text="Enter URL and click Download to start",
            text_color="gray",
            font=("Segoe UI", 12)
        )
        self.sel_label.pack(pady=20)

    def _reset_info(self):
        """Reset the info label text."""
        self.title_label.configure(text="No video loaded")

    def _reset_progress(self):
        """Reset the progress bar and related labels."""
        self.progress.set(0)
        self.speed_label.configure(text="Speed: - | ETA: -")
        self.info_label.configure(text="0.0 MB / 0.0 MB | 0%")

    def _ask_format(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL!")
            return

        # Prevent multiple downloads simultaneously
        if self._is_downloading:
            messagebox.showwarning("Warning", "A download is already in progress. Please wait or clear all first.")
            return

        self._reset_progress()
        for w in self.sel_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.sel_frame, text="Fetching video info...").pack(pady=20)
        threading.Thread(target=self._fetch_info, args=(url,), daemon=True).start()

    def _fetch_info(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'cookiefile': COOKIE_FILE_PATH,
                'nocheckcertificate': True,
                'ffmpeg_location': FFMPEG_PATH,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
            # Get approximate total filesize for estimation (not used anymore but kept if needed later)
            main_filesize = info.get('filesize_approx', 0) or info.get('filesize', 0)
            self.after(0, lambda: self.title_label.configure(
                text=f"{title[:60]}..." if len(title) > 60 else title
            ))
            
            # Check for available formats before showing options
            formats = info.get('formats', [])
            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            
            # Determine if only images are available
            has_video_audio = bool(video_formats)
            has_only_images = not has_video_audio and any(f.get('ext') == 'jpg' or f.get('ext') == 'webp' for f in formats)

            if has_only_images:
                 self.after(0, lambda: self._show_error("This URL only contains images. Video download is not possible."))
                 self.after(0, lambda: self.status.configure(text="Cannot download video.", text_color="red"))
                 return
            
            # Pass main_filesize for better estimation (kept for potential future use)
            self.after(0, lambda: self._show_quality_options(info))
        except Exception as e:
            # Capture the exception object in the lambda's scope to fix the NameError
            error_message = str(e)
            msg = error_message.lower()
            if any(k in msg for k in ['cookie', 'invalid', 'expired', 'sign in']):
                self.after(0, lambda: messagebox.showwarning(
                    "Cookie Warning",
                    "⚠️ Your YouTube cookies might be invalid or expired.\n"
                    "Please re-export your cookies from your browser."
                ))
            else:
                # Fixed: Pass the error message string directly to _show_error
                self.after(0, lambda msg=error_message: self._show_error(msg))

    def _show_quality_options(self, info):
        """Show video quality options for MP4 download."""
        for widget in self.sel_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.sel_frame,
            text="Select Video Quality:",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(self.sel_frame)
        btn_frame.pack(pady=10)

        colors = {
            1080: "#1e88e5",
            720: "#4caf50",
            480: "#f44336"
        }

        # Removed size estimation and display logic
        for res in [1080, 720, 480]:
            # Use lambda with default argument to capture 'res' correctly
            btn = ctk.CTkButton(
                btn_frame,
                text=f"{res}p",
                width=120,
                height=50,
                font=("Segoe UI", 14, "bold"),
                fg_color=colors[res],
                hover_color=self._darken(colors[res], 0.7),
                command=lambda r=res: self._start_download("mp4", info, r)
            )
            btn.pack(side="left", padx=5)

            # Size label removed as requested


    def _show_error(self, msg):
        for w in self.sel_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.sel_frame, text=f"Error: {msg}", text_color="red").pack(pady=20)
        # Reset status on error
        self.after(0, lambda: self.status.configure(text="Error occurred.", text_color="red"))

    def _darken(self, color, f=0.7):
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        dark = tuple(int(c * f) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*dark)

    def _start_download(self, media_type, info, res=None):
        # Mark download as active
        self._is_downloading = True
        self._download_thread = threading.current_thread() # Store reference to current thread

        self._clear_sel()
        title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
        filename = f"{title}_{res}p" # MP4 filename format
        self.status.configure(text="Starting download...", text_color="orange")
        out_dir = VIDEO_DIR # Always download to VIDEO_DIR

        # For MP4: Prefer merged mp4 up to res, fallback to best mp4, then best available
        # This format string is more flexible and should work better with current YouTube
        # It tries to get the best video up to the specified height, combined with the best audio
        format_string = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best[height<={res}]/best'

        opts = {
            'format': format_string,
            'outtmpl': os.path.join(out_dir, f'{filename}.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'cookiefile': COOKIE_FILE_PATH,
            'nocheckcertificate': True,
            'ffmpeg_location': FFMPEG_PATH
        }
        opts['merge_output_format'] = 'mp4' # Ensure merging happens for mp4

        # Start download in a separate thread
        download_thread = threading.Thread(target=self._download_with_fallback, args=(opts, info['webpage_url']), daemon=True)
        download_thread.start()
        self._download_thread = download_thread # Update reference

    def _clear_sel(self):
        for w in self.sel_frame.winfo_children():
            w.destroy()

    def _download_with_fallback(self, opts, url):
        # Try direct first
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                self.current_download_process = ydl
                ydl.download([url])
            
            # Reset state flags on the main thread before updating UI
            self._is_downloading = False
            self._download_thread = None
            
            self.after(0, lambda: self.status.configure(text="✅ Download completed!", text_color="green"))
            self.after(0, lambda: self._reset_progress()) # Reset progress after successful download
            return
        except Exception as e:
            error_message = str(e)
            if any(k in error_message.lower() for k in ['cookie', 'invalid', 'expired', 'sign in']):
                # Reset state flags on the main thread before updating UI
                self._is_downloading = False
                self._download_thread = None
                
                self.after(0, lambda: messagebox.showwarning("Cookie Warning", "⚠️ Cookies may be expired."))
                return
            # Log the error from the first attempt if fallback is needed
            print(f"First attempt failed: {error_message}")

        # Fallback to proxy
        proxy = self._detect_proxy()
        msg = f"Fallback: Trying via system proxy ({proxy})..." if proxy else "Fallback: Retrying..."
        self.after(0, lambda: self.status.configure(text=msg, text_color="orange"))
        opts2 = {**opts, 'proxy': proxy} if proxy else opts

        try:
            with yt_dlp.YoutubeDL(opts2) as ydl:
                self.current_download_process = ydl
                ydl.download([url])
            
            # Reset state flags on the main thread before updating UI
            self._is_downloading = False
            self._download_thread = None
            
            self.after(0, lambda: self.status.configure(text="✅ Download completed (via fallback)!", text_color="green"))
            self.after(0, lambda: self._reset_progress()) # Reset progress after successful download
        except Exception as e:
            final_error = str(e)
            
            # Reset state flags on the main thread before updating UI
            self._is_downloading = False
            self._download_thread = None
            
            self.after(0, lambda err=final_error: messagebox.showerror("Download Failed", f"Both attempts failed:\n{err}"))
            self.after(0, lambda: self.status.configure(text="❌ Download failed.", text_color="red"))
        finally:
            self.current_download_process = None

    def _detect_proxy(self):
        for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if val := os.environ.get(var):
                return val
        if sys.platform.startswith('win'):
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
                if winreg.QueryValueEx(key, 'ProxyEnable')[0]:
                    server = winreg.QueryValueEx(key, 'ProxyServer')[0]
                    return server if server.startswith(('http://', 'https://')) else f"http://{server}"
            except:
                pass
        return None

    def _progress_hook(self, d: Dict[str, Any]):
        if not d or not isinstance(d, dict):
             return

        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes_estimate') or d.get('total_bytes') or 1
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)

            pct = min(1.0, downloaded / total) if total > 0 else 0
            speed_str = f"{self._fmt_bytes(speed)}/s" if speed else "N/A"
            eta_str = f"{int(eta)}s" if eta else "?"

            # Throttle updates to avoid excessive rapid calls that might cause flickering
            # Only update if there's a significant change in percentage, speed, or ETA
            if (abs(pct - self._last_progress[0]) > 0.001 or
                speed_str != self._last_progress[1] or
                eta_str != self._last_progress[2]):

                # Schedule updates on the main thread
                self.after(0, lambda p=pct: self.progress.set(p))
                self.after(0, lambda: self.info_label.configure(
                    text=f"{downloaded/1e6:.2f} MB / {total/1e6:.2f} MB | {pct:.1%}"
                ))
                self.after(0, lambda: self.speed_label.configure(text=f"Speed: {speed_str} | ETA: {eta_str}"))

                # Update the last known progress state
                self._last_progress = (pct, speed_str, eta_str)

        elif status == 'finished':
            self.after(0, self._reset_progress)
            self.after(0, lambda: self.status.configure(text="Processing...", text_color="orange"))


    def _fmt_bytes(self, b: Union[int, float]) -> str:
        if not b:
            return "0.00 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if b < 1024.0:
                return f"{b:.2f} {unit}"
            b /= 1024.0
        return f"{b:.2f} TB"

    def _open_coffee(self):
        import webbrowser
        webbrowser.open("https://www.coffeebede.com/senpairato")


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
