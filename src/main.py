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

ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")


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
        if window is None or not window.winfo_exists():
            window = SettingsWindow(app_config, controller, on_hide_to_tray=window_hide)
            settings_window_ref["window"] = window
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
        tray_icon_ref["tray"].stop()
        os._exit(0)

    tray_icon_ref = {"tray": None}
    tray_icon = TrayIcon(ICON_PATH, on_open_settings=show_settings, on_quit=quit_app)
    tray_icon_ref["tray"] = tray_icon

    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    start_minimized = "--minimized" in sys.argv or app_config["start_minimized"]
    if not start_minimized:
        show_settings()

    # Tkinter requires a root window/mainloop on the main thread; if we
    # started minimized, we still need an invisible root to keep the process
    # alive and allow show_settings() to work later from the tray thread.
    if settings_window_ref["window"] is None:
        root = SettingsWindow(app_config, controller, on_hide_to_tray=window_hide)
        settings_window_ref["window"] = root
        root.withdraw()
        root.mainloop()
    else:
        settings_window_ref["window"].mainloop()


if __name__ == "__main__":
    main()
