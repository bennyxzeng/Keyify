"""
main.py — Keyify entry point. Wires together config, Spotify auth, hotkeys,
the tray icon, and the settings window.

Purpose: The only file run directly (or compiled by Nuitka into Keyify.exe).
Documentation: Startup flow: load config -> authenticate with Spotify ->
register hotkeys -> start tray icon -> optionally show settings window.
Maintenance: This file should stay thin — all real logic lives in the
dedicated modules it imports.
"""

import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import config as config_module
import port_utils
import startup
from spotify_client import SpotifyController
from hotkey_manager import register_all, shutdown as shutdown_hotkeys
from tray import TrayIcon
from gui import SettingsWindow


def _resolve_icon_path():
    """
    Purpose: Finds icon.ico reliably whether running as a raw Python script
    or as a compiled Nuitka onefile/standalone executable.
    Parameters: None.
    Returns: str — absolute path to assets/icon.ico, or None if not found.

    Explanation: Nuitka's --include-data-dir=assets=assets places the assets
    folder DIRECTLY inside the onefile temp extraction root at runtime
    (e.g. <temp_dir>/assets/icon.ico) — NOT one level up via "..". The first
    candidate below matches that compiled layout. The second candidate covers
    running main.py directly from source (src/main.py -> ../assets/icon.ico).
    Checking both means this works identically in dev mode and after Nuitka
    compilation without needing to change code between the two.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "assets", "icon.ico"),        # Compiled onefile layout
        os.path.join(base_dir, "..", "assets", "icon.ico"),  # Running from src/ in dev mode
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "assets", "icon.ico"),
    ]
    for path in candidates:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None


ICON_PATH = _resolve_icon_path()


def main():
    """
    Purpose: Boots the full Keyify application.
    Parameters: None (reads --minimized from sys.argv, set by the Registry
        Run key when start-on-boot is enabled).
    Returns: None.

    Explanation: The tray icon runs on a background thread since pystray's
    run() call blocks; Tkinter's mainloop owns the main thread, which is
    required for Tkinter to function correctly on Windows.
    """
    app_config = config_module.load_config()

    settings_window_ref = {"window": None}
    tray_icon_ref = {"tray": None}

    def notify(message):
        """Purpose: Routes error/status messages to the tray balloon notification."""
        if tray_icon_ref.get("tray"):
            tray_icon_ref["tray"].notify(message)

    controller = None
    if app_config["client_id"] and app_config["client_secret"]:
        port = port_utils.find_available_port()
        app_config["redirect_port"] = port
        controller = SpotifyController(
            client_id=app_config["client_id"],
            client_secret=app_config["client_secret"],
            redirect_port=port,
            notify_callback=notify,
        )
        register_all(app_config, controller, on_conflict_error=lambda a, k: notify(
            f"Could not register hotkey '{k}' for {a} — it may be in use by another app."
        ))

    def show_settings():
        """Purpose: Opens (or focuses) the Tkinter settings window from the tray menu."""
        window = settings_window_ref["window"]
        window.deiconify()
        window.lift()

    def window_hide():
        """Purpose: Hides the settings window to tray instead of destroying it."""
        settings_window_ref["window"].withdraw()

    def quit_app():
        """
        Purpose: Fully terminates Keyify — the only action that should stop
        the app entirely, per spec (closing the settings window must NOT quit).
        """
        shutdown_hotkeys()
        if tray_icon_ref["tray"]:
            tray_icon_ref["tray"].stop()
        os._exit(0)

    if ICON_PATH is None:
        print("WARNING: icon.ico not found — tray icon will fail to load.")
    else:
        tray_icon = TrayIcon(ICON_PATH, on_open_settings=show_settings, on_quit=quit_app)
        tray_icon_ref["tray"] = tray_icon
        tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
        tray_thread.start()

    # Build the single Tkinter root window ONCE, up front, on the main thread.
    # Reusing show_settings()/window_hide() against this same instance avoids
    # the earlier bug of trying to create a second SettingsWindow later.
    root = SettingsWindow(app_config, controller, on_hide_to_tray=window_hide)
    settings_window_ref["window"] = root

    start_minimized = "--minimized" in sys.argv or app_config["start_minimized"]
    if start_minimized:
        root.withdraw()

    root.mainloop()


if __name__ == "__main__":
    main()