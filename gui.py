# gui.py
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import re
from typing import Dict, Any
from PIL import Image  # Import PIL for logo handling
import webbrowser # For opening coffee page
import os # For opening folder
import subprocess # For opening folder on non-Windows
import yt_dlp # Import yt_dlp for handling exceptions in GUI

from config_manager import load_config, save_config, ensure_directories, DOWNLOAD_DIR
from utils import check_dependencies, format_bytes, DownloadCanceledException, LOGO_PATH, ICON_PATH
from downloader import DownloadManager

# Set the default color theme for better light mode appearance
ctk.set_default_color_theme("blue")

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
        # Add a flag for canceling downloads
        self._download_canceled = threading.Event()
        # Track if a download is currently running
        self._is_downloading = False

        # Check dependencies
        deps_errors = check_dependencies()
        if deps_errors:
            self.show_startup_errors(deps_errors)

        # Ensure directories exist
        ensure_directories()

        # Set the window icon
        try:
            self.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Could not load window icon: {e}")

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

        # Program name label (Color changes based on theme)
        self.title_label = ctk.CTkLabel(
            header_frame,
            text="Akeno Downloader",
            font=("Segoe UI", 16, "bold"),
            # Color will be set dynamically below
        )
        # Configure text color based on appearance mode
        if ctk.get_appearance_mode() == "Dark":
            self.title_label.configure(text_color="white")
        else:  # Light mode
            self.title_label.configure(text_color="black")
        self.title_label.pack(side="left", padx=10)

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

        self.title_label_info = ctk.CTkLabel(
            self.info_frame,
            text="No video loaded",
            font=("Segoe UI", 14),
            wraplength=600
        )
        self.title_label_info.pack(pady=5)

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

        self.clear_btn = ctk.CTkButton(
            btn_frame_bottom,
            text="🗑️ Clear All",
            font=("Segoe UI", 14, "bold"),
            width=150,
            height=40,
            command=self.clear_all
        )
        self.clear_btn.pack(side="left", padx=10)

        # --- Status Label (Moved to bottom center) ---
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            text_color="green", # Default color
            font=("Segoe UI", 16, "bold"), # Larger font
            anchor="center"
        )
        # Place it at the bottom center of the window
        self.status_label.place(relx=0.5, rely=0.95, anchor="center")

    def show_startup_errors(self, errors):
        """Display startup error messages"""
        error_msg = "\n\n".join(errors)
        messagebox.showerror("Startup Error", error_msg)

    def open_download_folder(self):
        """Open the downloads folder"""
        try:
            os.startfile(self.config.get("download_dir")) # Use the path from config
        except:
            try:
                subprocess.Popen(['xdg-open', self.config.get("download_dir")]) # Use the path from config
            except:
                try:
                    subprocess.Popen(['open', self.config.get("download_dir")]) # Use the path from config
                except:
                    messagebox.showerror("Error", "Could not open folder. Please check manually.")

    def show_cookie_warning(self):
        """Show a cookie warning message"""
        warning_msg = (
            "⚠️ Your YouTube cookies might be invalid or expired.\n"
            "Please re-export your cookies from your browser and replace the 'cookies.txt' file."
        )
        messagebox.showwarning("Cookie Warning", warning_msg)

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
        # Update title label color after changing appearance mode
        if ctk.get_appearance_mode() == "Dark":
            self.title_label.configure(text_color="white")
        else:  # Light mode
            self.title_label.configure(text_color="black")
        save_config(self.config)

    def clear_all(self):
        """Clear all downloads and reset the UI completely"""
        # Set the cancel flag to stop any ongoing download
        if self._is_downloading:
            self._download_canceled.set()
            self.status_label.configure(text="Cancelling download...", text_color="orange") # You can keep "orange" or change to "yellow"
        else:
            # If no download is running, just reset UI
            self._download_canceled.clear()
            self.url_entry.delete(0, tk.END)
            self.reset_selection_frame()
            self.reset_info()
            self.reset_progress()
            self.status_label.configure(text="Ready", text_color="green")
            # Re-enable buttons if they were disabled (e.g., after a failed/canceled download)
            self.set_ui_state("normal")

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
        self.title_label_info.configure(text="No video loaded")

    def reset_progress(self):
        """Reset the progress bar and related labels"""
        self.progress_bar.set(0)
        self.speed_label.configure(text="Speed: - | ETA: -")
        self.download_info_label.configure(text="0.0 MB / 0.0 MB | 0%")

    def set_ui_state(self, state):
        """Enable or disable UI elements during download."""
        self.url_entry.configure(state=state)
        self.download_btn.configure(state=state)
        self.clear_btn.configure(state=state) # Also disable/enable clear button
        # Disable/enable quality buttons if they exist
        for child in self.selection_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for btn in child.winfo_children():
                    if isinstance(btn, ctk.CTkButton):
                        btn.configure(state=state)

    def ask_format(self):
        """Fetch video info and show quality options directly (only for video)"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL!")
            return

        # Disable UI elements before starting to fetch info
        self.set_ui_state("disabled")
        self.status_label.configure(text="Fetching video info...", text_color="yellow") # Change from "blue" to "yellow"

        self.reset_progress()
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(self.selection_frame, text="Fetching video info...", font=("Segoe UI", 12))
        loading_label.pack(pady=20)

        threading.Thread(target=self.fetch_video_info_for_quality, args=(url,), daemon=True).start()

    def fetch_video_info_for_quality(self, url):
        """Fetch video information using yt_dlp to get filesize for quality options"""
        try:
            # Create a temporary DownloadManager instance just for fetching info
            temp_manager = DownloadManager(progress_hook=lambda d: None, cancel_event=threading.Event())
            info = temp_manager.fetch_video_info(url)

            title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
            filesize = info.get('filesize_approx', 0)

            self.after(0, lambda: self.title_label_info.configure(
                text=f"{title[:60]}..." if len(title) > 60 else title
            ))

            # Directly show quality options after fetching info
            self.after(0, lambda: self.show_quality_options(info, filesize))

        except Exception as e:
            error_msg = str(e).lower()

            # Check if the error is related to cookies
            if 'cookie' in error_msg or 'invalid' in error_msg or 'expired' in error_msg or 'sign in' in error_msg:
                def show_warning_callback():
                    self.show_cookie_warning()
                self.after(0, show_warning_callback)
            else:
                # If it's a different error, show the standard error message
                def show_error_callback():
                    self.show_error(str(e))
                self.after(0, show_error_callback)
        finally:
            # Re-enable UI if fetching failed or if user cancelled during fetch
            pass

    def show_error(self, msg):
        """Show an error message in the selection frame"""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()
        error_label = ctk.CTkLabel(self.selection_frame, text=f"Error: {msg}", text_color="red", font=("Segoe UI", 12))
        error_label.pack(pady=20)
        # Re-enable UI as the process failed
        self.set_ui_state("normal")
        self.status_label.configure(text="Error occurred.", text_color="red")

    def show_quality_options(self, info, main_filesize):
        """Show video quality options for MP4 download (without size labels)"""
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

        for res in [1080, 720, 480]:
            btn = ctk.CTkButton(
                btn_frame,
                text=f"{res}p",
                width=120,
                height=50,
                font=("Segoe UI", 14, "bold"),
                fg_color=colors[res],
                hover_color=colors[res],
                command=lambda r=res, i=info: self.start_download_thread(i, r)
            )
            btn.pack(side="left", padx=5)

    def start_download_thread(self, info, resolution):
        """Start the download process in a separate thread (only video now)"""
        # Ensure UI is disabled when download actually starts
        self.set_ui_state("disabled")
        self._is_downloading = True # Set the flag

        self.reset_selection_frame()

        title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', info['title'])
        filename = f"{title}_{resolution}p"

        self.status_label.configure(text=f"Starting download...", text_color="yellow") # Change from "blue" to "yellow"

        # Create the DownloadManager instance for this download
        download_manager = DownloadManager(progress_hook=self.progress_hook, cancel_event=self._download_canceled)

        download_thread = threading.Thread(target=self.run_download, args=(download_manager, info, resolution, filename), daemon=True)
        download_thread.start()

    def run_download(self, download_manager, info, resolution, filename):
        """Run the download process in the separate thread using DownloadManager"""
        try:
            download_manager.start_download(info, resolution, filename)
            # Check the cancel flag after download finishes
            if self._download_canceled.is_set():
                # If canceled during download, do not show success message
                self.after(0, lambda: self.status_label.configure(text="Download canceled.", text_color="red"))
            else:
                self.after(0, lambda: self.status_label.configure(text="Download completed successfully!", text_color="green"))
        except DownloadCanceledException:
            # Handle the specific cancellation exception
            self.after(0, lambda: self.status_label.configure(text="Download canceled.", text_color="red"))
        except yt_dlp.DownloadError as e:
            # Check if the error is due to cancellation
            if "This playlist has been removed or is private" in str(e) or "canceled" in str(e).lower():
                 # This might catch generic cancellation errors from yt_dlp if it propagates them
                 self.after(0, lambda: self.status_label.configure(text="Download canceled.", text_color="red"))
            else:
                error_msg = str(e).lower()
                # Check if the error is related to cookies
                if 'cookie' in error_msg or 'invalid' in error_msg or 'expired' in error_msg or 'sign in' in error_msg:
                    def show_warning_callback():
                        self.show_cookie_warning()
                    self.after(0, show_warning_callback)
                else:
                    # If it's a different error, show the standard error message
                    def show_download_error():
                        messagebox.showerror("Download Failed", str(e))
                        self.after(0, lambda: self.status_label.configure(text="Download failed.", text_color="red"))
                    self.after(0, show_download_error)
        except Exception as e:
            # Handle other unexpected exceptions
            def show_download_error():
                messagebox.showerror("Download Failed", str(e))
                self.after(0, lambda: self.status_label.configure(text="Download failed.", text_color="red"))
            self.after(0, show_download_error)
        finally:
            # Always clear the download flag and re-enable UI
            self._is_downloading = False
            self._download_canceled.clear() # Reset the event for future downloads
            self.after(0, lambda: self.download_btn.configure(state="normal")) # Ensure download button is re-enabled
            self.after(0, lambda: self.set_ui_state("normal")) # Re-enable all UI elements

    def progress_hook(self, d: Dict[str, Any]):
        """Handle download progress updates from yt_dlp via DownloadManager"""
        # Check the cancel flag first
        if self._download_canceled.is_set():
            # Raise the custom exception to stop yt_dlp
            raise DownloadCanceledException("Download canceled by user.")

        # Comprehensive check to ensure d is a valid dictionary
        if not d or not isinstance(d, dict):
            return

        status = d.get('status')
        if status == 'downloading':
            # Safely get values with defaults
            total = d.get('total_bytes_estimate') or d.get('total_bytes') or d.get('_total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            eta = d.get('eta') or 0

            # Prevent division by zero
            percent = downloaded / total if total > 0 else 0

            speed_str = f"{format_bytes(speed)}/s" if speed else "N/A"
            eta_str = f"{int(eta)}s" if eta else "?"

            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)

            self.after(0, lambda: self.download_info_label.configure(
                text=f"{downloaded_mb:.2f} MB / {total_mb:.2f} MB | {percent:.1%}"
            ))

            self.after(0, lambda: self.progress_bar.set(percent))
            self.after(0, lambda: self.speed_label.configure(text=f"Speed: {speed_str} | ETA: {eta_str}"))

        elif status == 'finished':
            # Check the cancel flag again just before finishing
            if self._download_canceled.is_set():
                self.after(0, lambda: self.status_label.configure(text="Download canceled.", text_color="red"))
            else:
                self.after(0, lambda: self.reset_progress())
                self.after(0, lambda: self.status_label.configure(text="Download finished, processing...", text_color="yellow"))

    def open_coffee_page(self):
        """Open the donation page in a web browser"""
        webbrowser.open("https://www.coffeebede.com/senpairato")
