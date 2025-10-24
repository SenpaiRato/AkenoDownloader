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
from PIL import Image  # Import PIL for logo handling

# Initial settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Download directories
DOWNLOAD_DIR = os.path.join(os.getcwd(), "YouTube_Downloads")
VIDEO_DIR = os.path.join(DOWNLOAD_DIR, "Videos")
AUDIO_DIR = os.path.join(DOWNLOAD_DIR, "Audios")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Configuration paths
COOKIE_FILE_PATH = os.path.join(os.getcwd(), "cookies.txt")
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
CONFIG_FILE = os.path.join(os.getcwd(), "config.json")
# Path to the logo file
LOGO_PATH = os.path.join(os.path.dirname(__file__), "Res", "logo.png")

def check_dependencies():
    """Check for required files"""
    errors = []
    if not os.path.exists(COOKIE_FILE_PATH):
        errors.append(f"Cookie file not found: {COOKIE_FILE_PATH}\nPlease export YouTube cookies.")
    if not os.path.exists(FFMPEG_PATH):
        errors.append(f"FFmpeg not found: {FFMPEG_PATH}\nPlease place ffmpeg.exe next to the program.")
    if not os.path.exists(LOGO_PATH):
        errors.append(f"Logo not found: {LOGO_PATH}\nPlease place logo.png in Res folder.")
    return errors

def load_config():
    """Load settings from config.json"""
    default_config = {
        "theme": "dark",
        "proxy_enabled": False,
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

def save_config(config):
    """Save settings to config.json"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

class YouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load configuration
        self.config = load_config()
        ctk.set_appearance_mode(self.config.get("theme", "dark"))

        # Window setup
        self.title("🎥 Akeno Downloader")  # Program name
        self.geometry("700x650")
        self.resizable(False, False)
        self.current_download_process: Optional[yt_dlp.YoutubeDL] = None
        self.use_proxy = False
        self.current_proxy: Optional[str] = None

        # Check dependencies
        deps_errors = check_dependencies()
        if deps_errors:
            self.show_startup_errors(deps_errors)

        # --- Header ---
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(pady=20, padx=40, fill="x")

        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                logo_label = ctk.CTkLabel(
                    header_frame,
                    text="",
                    image=ctk.CTkImage(
                        light_image=Image.open(LOGO_PATH),
                        dark_image=Image.open(LOGO_PATH),
                        size=(50, 50)
                    ),
                    width=50,
                    height=50
                )
                logo_label.pack(side="left", padx=5)
            except Exception as e:
                print(f"Error loading logo: {e}")
        else:
            print(f"Logo file not found at {LOGO_PATH}")

        # Program name label
        title_label = ctk.CTkLabel(
            header_frame,
            text="Akeno Downloader",
            font=("Segoe UI", 16, "bold"),
            text_color="white"
        )
        title_label.pack(side="left", padx=10)

        coffee_btn = ctk.CTkButton(
            header_frame,
            text="☕ Buy Me a Coffee",
            font=("Segoe UI", 12, "bold"),
            width=200,
            height=40,
            command=self.open_coffee_page,
            fg_color="#FFA500",
            hover_color="#FF8C00",
            text_color="black"
        )
        coffee_btn.pack(side="left", padx=5)

        self.mode_button = ctk.CTkButton(
            header_frame,
            text="☀️ Light Mode" if self.config.get("theme", "dark") == "dark" else "🌙 Dark Mode",
            width=120,
            font=("Segoe UI", 10),
            command=self.toggle_mode
        )
        self.mode_button.pack(side="right")

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(pady=10, padx=40, fill="x")

        self.url_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Paste YouTube URL here...",
            font=("Segoe UI", 12),
            height=40
        )
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.setup_definitive_shortcuts()

        self.download_btn = ctk.CTkButton(
            input_frame,
            text="⬇️ Download",
            width=120,
            font=("Segoe UI", 12, "bold"),
            command=self.ask_format
        )
        self.download_btn.pack(side="left", padx=5)

        # --- Selection Frame ---
        self.selection_frame = ctk.CTkFrame(self)
        self.selection_frame.pack(pady=10, padx=40, fill="x")

        self.selection_label = ctk.CTkLabel(
            self.selection_frame,
            text="Enter URL and click Download to start",
            text_color="gray",
            font=("Segoe UI", 12)
        )
        self.selection_label.pack(pady=20)

        # --- Info Frame ---
        self.info_frame = ctk.CTkFrame(self, corner_radius=10)
        self.info_frame.pack(pady=15, padx=40, fill="x")

        self.title_label = ctk.CTkLabel(
            self.info_frame,
            text="No video loaded",
            font=("Segoe UI", 14),
            wraplength=600
        )
        self.title_label.pack(pady=5)

        # --- Progress Bar ---
        self.progress_bar = ctk.CTkProgressBar(self, width=500)
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#32CD32")
        self.progress_bar.pack(pady=20)

        self.download_info_label = ctk.CTkLabel(
            self,
            text="0.0 MB / 0.0 MB | 0%",
            text_color="white",
            font=("Segoe UI", 10),
            anchor="center"
        )
        self.download_info_label.pack(pady=5)

        self.speed_label = ctk.CTkLabel(
            self,
            text="Speed: - | ETA: -",
            text_color="gray",
            font=("Segoe UI", 12)
        )
        self.speed_label.pack()

        # --- Buttons ---
        btn_frame_bottom = ctk.CTkFrame(self)
        btn_frame_bottom.pack(pady=20)

        self.open_folder_btn = ctk.CTkButton(
            btn_frame_bottom,
            text="📂 Open Folder",
            font=("Segoe UI", 12, "bold"),
            width=120,
            height=40,
            command=self.open_download_folder
        )
        self.open_folder_btn.pack(side="left", padx=10)

        self.proxy_btn = ctk.CTkButton(
            btn_frame_bottom,
            text="🔌 Proxy: OFF",
            font=("Segoe UI", 12, "bold"),
            width=120,
            height=40,
            fg_color="#666666",
            hover_color="#555555",
            command=self.toggle_proxy
        )
        self.proxy_btn.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(
            btn_frame_bottom,
            text="🗑️ Clear All",
            font=("Segoe UI", 14, "bold"),
            width=150,
            height=40,
            command=self.clear_all
        )
        self.clear_btn.pack(side="left", padx=10)

        # --- Status ---
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            text_color="green",
            font=("Segoe UI", 12)
        )
        self.status_label.pack(side="bottom", pady=10)

        # --- Footer ---
        footer_label = ctk.CTkLabel(
            self,
            text="Made by SenpaiRato",
            font=("Segoe UI", 8),
            text_color="gray",
            anchor="sw"
        )
        footer_label.place(x=10, y=620)

        # Apply initial settings
        if self.config.get("proxy_enabled", False):
            self.use_proxy = True
            self.current_proxy = self.detect_system_proxy()
            if self.current_proxy:
                self.proxy_btn.configure(
                    text="🔌 Proxy: ON",
                    fg_color="#0066cc",
                    hover_color="#0052a3"
                )
                self.status_label.configure(text=f"Proxy enabled - Using: {self.current_proxy}")
            else:
                self.proxy_btn.configure(
                    text="🔌 Proxy: ON*",
                    fg_color="#ff9900",
                    hover_color="#cc7a00"
                )
                self.status_label.configure(text="Proxy enabled - No system proxy found (will use direct connection)")

    def show_startup_errors(self, errors):
        """Display startup error messages"""
        error_msg = "\n\n".join(errors)
        messagebox.showerror("Startup Error", error_msg)

    def open_download_folder(self):
        """Open the downloads folder"""
        try:
            os.startfile(DOWNLOAD_DIR)
        except:
            try:
                import subprocess
                subprocess.Popen(['xdg-open', DOWNLOAD_DIR])
            except:
                try:
                    import subprocess
                    subprocess.Popen(['open', DOWNLOAD_DIR])
                except:
                    messagebox.showerror("Error", "Could not open folder. Please check manually.")

    def toggle_proxy(self):
        """Toggle proxy settings on or off"""
        self.use_proxy = not self.use_proxy
        self.config["proxy_enabled"] = self.use_proxy
        if self.use_proxy:
            self.current_proxy = self.detect_system_proxy()
            if self.current_proxy:
                self.proxy_btn.configure(
                    text="🔌 Proxy: ON",
                    fg_color="#0066cc",
                    hover_color="#0052a3"
                )
                self.status_label.configure(text=f"Proxy enabled - Using: {self.current_proxy}")
            else:
                self.proxy_btn.configure(
                    text="🔌 Proxy: ON*",
                    fg_color="#ff9900",
                    hover_color="#cc7a00"
                )
                self.status_label.configure(text="Proxy enabled - No system proxy found (will use direct connection)")
        else:
            self.current_proxy = None
            self.proxy_btn.configure(
                text="🔌 Proxy: OFF",
                fg_color="#666666",
                hover_color="#555555"
            )
            self.status_label.configure(text="Proxy disabled - Using direct connection")
        save_config(self.config)

    def detect_system_proxy(self):
        """Detect system proxy settings"""
        proxies = []
        env_vars = [
            'HTTP_PROXY', 'http_proxy',
            'HTTPS_PROXY', 'https_proxy',
            'ALL_PROXY', 'all_proxy',
            'SOCKS_PROXY', 'socks_proxy'
        ]
        for var in env_vars:
            proxy = os.environ.get(var)
            if proxy and proxy not in proxies:
                proxies.append(proxy)
        try:
            if sys.platform.startswith('win'):
                proxy = self.get_windows_proxy()
                if proxy and proxy not in proxies:
                    proxies.append(proxy)
        except:
            pass
        return proxies[0] if proxies else None

    def get_windows_proxy(self):
        """Get Windows proxy settings"""
        try:
            import winreg
            internet_settings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
            )
            proxy_enable = winreg.QueryValueEx(internet_settings, 'ProxyEnable')[0]
            if proxy_enable:
                proxy_server = winreg.QueryValueEx(internet_settings, 'ProxyServer')[0]
                if proxy_server:
                    if not proxy_server.startswith(('http://', 'https://', 'socks')):
                        return f"http://{proxy_server}"
                    return proxy_server
        except:
            pass
        return None

    def setup_definitive_shortcuts(self):
        """Setup keyboard shortcuts for the URL entry"""
        try:
            inner_entry = self.url_entry._entry
            inner_entry.bind("<Control-v>", self.paste_text)
            inner_entry.bind("<Control-V>", self.paste_text)
            inner_entry.bind("<Control-a>", self.select_all_text)
            inner_entry.bind("<Control-A>", self.select_all_text)
        except:
            pass
        paste_btn = ctk.CTkButton(
            self.url_entry.master,
            text="📋",
            width=30,
            height=30,
            font=("Segoe UI", 10),
            command=self.manual_paste
        )
        paste_btn.pack(side="left", padx=(5, 0))

    def paste_text(self, event=None):
        """Paste text from clipboard into the URL entry"""
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_content)
                self.url_entry.focus()
        except:
            pass
        return "break"

    def select_all_text(self, event=None):
        """Select all text in the URL entry"""
        self.url_entry.select_range(0, tk.END)
        self.url_entry.icursor(tk.END)
        return "break"

    def manual_paste(self):
        """Manual paste function triggered by the paste button"""
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_content)
                self.url_entry.focus()
        except:
            messagebox.showwarning("Warning", "Clipboard is empty!")

    def toggle_mode(self):
        """Toggle between light and dark mode"""
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            ctk.set_appearance_mode("Light")
            self.mode_button.configure(text="🌙 Dark Mode")
            self.config["theme"] = "light"
        else:
            ctk.set_appearance_mode("Dark")
            self.mode_button.configure(text="☀️ Light Mode")
            self.config["theme"] = "dark"
        save_config(self.config)

    def clear_all(self):
        """Clear all downloads and reset the UI"""
        # Cannot stop the yt_dlp process, just set the variable to None
        self.current_download_process = None
        
        try:
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(file_path) and filename.endswith('.part'):
                    os.remove(file_path)
        except Exception as e:
            pass

        self.url_entry.delete(0, tk.END)
        self.reset_selection_frame()
        self.reset_info()
        self.reset_progress()
        self.current_proxy = None
        self.use_proxy = False
        self.proxy_btn.configure(
            text="🔌 Proxy: OFF",
            fg_color="#666666",
            hover_color="#555555"
        )
        self.status_label.configure(text="Cleared")

    def show_info_message(self, title, message):
        """Show an information message in a popup window"""
        info_window = ctk.CTkToplevel(self)
        info_window.title(title)
        info_window.geometry("400x150")
        info_window.resizable(False, False)
        info_window.transient(self)
        info_window.grab_set()
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (info_window.winfo_screenheight() // 2) - (150 // 2)
        info_window.geometry(f"400x150+{x}+{y}")
        msg_label = ctk.CTkLabel(
            info_window,
            text=message,
            wraplength=350,
            font=("Segoe UI", 12)
        )
        msg_label.pack(pady=20)
        ok_btn = ctk.CTkButton(
            info_window,
            text="OK",
            width=80,
            command=info_window.destroy
        )
        ok_btn.pack(pady=10)

    def reset_selection_frame(self):
        """Reset the selection frame UI"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()
        self.selection_label = ctk.CTkLabel(
            self.selection_frame,
            text="Enter URL and click Download to start",
            text_color="gray",
            font=("Segoe UI", 12)
        )
        self.selection_label.pack(pady=20)

    def reset_info(self):
        """Reset the info label text"""
        self.title_label.configure(text="No video loaded")

    def reset_progress(self):
        """Reset the progress bar and related labels"""
        self.progress_bar.set(0)
        self.speed_label.configure(text="Speed: - | ETA: -")
        self.download_info_label.configure(text="0.0 MB / 0.0 MB | 0%")

    def ask_format(self):
        """Ask the user for the download format (MP3 or MP4)"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL!")
            return

        self.reset_progress()
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(self.selection_frame, text="Fetching video info...", font=("Segoe UI", 12))
        loading_label.pack(pady=20)

        threading.Thread(target=self.fetch_video_info, args=(url,), daemon=True).start()

    def darken_color(self, color, factor=0.7):
        """Darken a color by a specified factor"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        dark_rgb = tuple(int(c * factor) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*dark_rgb)

    def fetch_video_info(self, url):
        """Fetch video information using yt_dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'cookiefile': COOKIE_FILE_PATH,
                'nocheckcertificate': True,
                'ffmpeg_location': FFMPEG_PATH
            }

            if self.use_proxy and self.current_proxy:
                ydl_opts['proxy'] = self.current_proxy

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
            filesize = info.get('filesize_approx', 0)

            self.after(0, lambda: self.title_label.configure(
                text=f"{title[:60]}..." if len(title) > 60 else title
            ))

            self.after(0, lambda: self.show_format_options(info, filesize))

        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if the error is related to cookies
            if 'cookie' in error_msg or 'invalid' in error_msg or 'expired' in error_msg or 'sign in' in error_msg:
                warning_msg = (
                    "⚠️ Your YouTube cookies might be invalid or expired.\n"
                    "Please re-export your cookies from your browser and replace the 'cookies.txt' file."
                )
                def show_warning_callback():
                    messagebox.showwarning("Cookie Warning", warning_msg)
                self.after(0, show_warning_callback)
            else:
                # If it's a different error, show the standard error message
                def show_error_callback():
                    self.show_error(str(e))
                self.after(0, show_error_callback)

    def show_error(self, msg):
        """Show an error message in the selection frame"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()
        error_label = ctk.CTkLabel(self.selection_frame, text=f"Error: {msg}", text_color="red", font=("Segoe UI", 12))
        error_label.pack(pady=20)

    def show_format_options(self, info, main_filesize):
        """Show format selection options (MP3 or MP4)"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.selection_frame,
            text="Choose Format:",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(self.selection_frame)
        btn_frame.pack(pady=10)

        mp3_btn = ctk.CTkButton(
            btn_frame,
            text="🎵 MP3 (Best Quality)",
            width=200,
            height=50,
            font=("Segoe UI", 14, "bold"),
            fg_color="#0066cc",
            hover_color="#0052a3",
            command=lambda: self.start_download("mp3", info)
        )
        mp3_btn.pack(side="left", padx=10)

        mp4_btn = ctk.CTkButton(
            btn_frame,
            text="🎬 MP4 (Select Quality)",
            width=200,
            height=50,
            font=("Segoe UI", 14, "bold"),
            fg_color="#0099ff",
            hover_color="#0077bb",
            command=lambda: self.show_quality_options(info, main_filesize)
        )
        mp4_btn.pack(side="left", padx=10)

    def show_quality_options(self, info, main_filesize):
        """Show video quality options for MP4 download"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.selection_frame,
            text="Select Video Quality:",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(self.selection_frame)
        btn_frame.pack(pady=10)

        colors = {
            1080: "#1e88e5",
            720: "#4caf50",
            480: "#f44336"
        }

        quality_sizes = {
            1080: main_filesize,
            720: main_filesize * 0.6,
            480: main_filesize * 0.3
        }

        for res in [1080, 720, 480]:
            size = quality_sizes.get(res, 0)
            size_text = f"~{self.format_bytes(size)}" if size > 0 else "N/A"

            btn = ctk.CTkButton(
                btn_frame,
                text=f"{res}p",
                width=120,
                height=50,
                font=("Segoe UI", 14, "bold"),
                fg_color=colors[res],
                hover_color=self.darken_color(colors[res], 0.7),
                command=lambda r=res: self.start_download("mp4", info, r)
            )
            btn.pack(side="left", padx=5)

            size_label = ctk.CTkLabel(
                btn_frame,
                text=size_text,
                font=("Segoe UI", 10),
                text_color="white",
                anchor="center"
            )
            size_label.pack(side="left", padx=5, pady=2)

    def start_download(self, media_type, info, resolution=None):
        """Start the download process in a separate thread"""
        self.reset_selection_frame()

        title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
        if media_type == "mp3":
            filename = f"{title}_audio"
        else:
            filename = f"{title}_{resolution}p"

        if self.use_proxy:
            if self.current_proxy:
                connection_type = f"Proxy ({self.current_proxy})"
            else:
                connection_type = "Direct (Proxy enabled but not found)"
        else:
            connection_type = "Direct"
        self.status_label.configure(text=f"Starting download via {connection_type}...")

        target_dir = AUDIO_DIR if media_type == "mp3" else VIDEO_DIR

        ydl_opts = {
            'format': 'bestaudio/best' if media_type == "mp3" else f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]',
            'outtmpl': os.path.join(target_dir, f'{filename}.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'cookiefile': COOKIE_FILE_PATH,
            'nocheckcertificate': True,
            'ffmpeg_location': FFMPEG_PATH
        }

        if media_type == "mp3":
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            ydl_opts['merge_output_format'] = 'mp4'

        if self.use_proxy and self.current_proxy:
            ydl_opts['proxy'] = self.current_proxy

        download_thread = threading.Thread(target=self.run_download, args=(ydl_opts, info['webpage_url']), daemon=True)
        download_thread.start()

    def run_download(self, ydl_opts, url):
        """Run the download process in the separate thread"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_download_process = ydl
                ydl.download([url])
                self.after(0, lambda: self.status_label.configure(text="Download completed successfully!", text_color="green"))
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if the error is related to cookies
            if 'cookie' in error_msg or 'invalid' in error_msg or 'expired' in error_msg or 'sign in' in error_msg:
                warning_msg = (
                    "⚠️ Your YouTube cookies might be invalid or expired.\n"
                    "Please re-export your cookies from your browser and replace the 'cookies.txt' file."
                )
                def show_warning_callback():
                    messagebox.showwarning("Cookie Warning", warning_msg)
                self.after(0, show_warning_callback)
            else:
                # If it's a different error, show the standard error message
                def show_download_error():
                    messagebox.showerror("Download Failed", str(e))
                    self.after(0, lambda: self.status_label.configure(text="Download failed.", text_color="red"))
                self.after(0, show_download_error)
        finally:
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            self.current_download_process = None

    def progress_hook(self, d: Dict[str, Any]):
        """Handle download progress updates from yt_dlp"""
        # Comprehensive check to ensure d is a valid dictionary
        if not d or not isinstance(d, dict):
            return

        status = d.get('status')
        if status == 'downloading':
            # Safely get values with defaults
            total = d.get('total_bytes_estimate') or d.get('total_bytes') or 1
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            eta = d.get('eta') or 0

            # Prevent division by zero
            percent = downloaded / total if total > 0 else 0
            
            speed_str = f"{self.format_bytes(speed)}/s" if speed else "N/A"
            eta_str = f"{int(eta)}s" if eta else "?"

            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            
            self.after(0, lambda: self.download_info_label.configure(
                text=f"{downloaded_mb:.2f} MB / {total_mb:.2f} MB | {percent:.1%}"
            ))

            self.after(0, lambda: self.progress_bar.set(percent))
            self.after(0, lambda: self.speed_label.configure(text=f"Speed: {speed_str} | ETA: {eta_str}"))

        elif status == 'finished':
            self.after(0, lambda: self.reset_progress())
            self.after(0, lambda: self.status_label.configure(text="Download finished, processing...", text_color="yellow"))

    def format_bytes(self, bytes_value: Union[int, float]) -> str:
        """Format bytes to human readable format (e.g., KB, MB, GB)"""
        if bytes_value is None:
            return "0.00 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} TB"

    def open_coffee_page(self):
        """Open the donation page in a web browser"""
        import webbrowser
        webbrowser.open("https://www.coffeebede.com/senpairato  ")


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()