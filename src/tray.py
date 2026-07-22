"""
tray.py — Manages the system tray icon and its right-click menu.

Purpose: Keeps Keyify running in the background (tray-only) after the
settings window is closed, per the requirement that the app only fully
stops when the user selects "Quit Keyify" from the tray.
Documentation: Built with pystray, which handles the Windows tray icon API.
Maintenance: Add new tray menu items here; gui.py stays focused on the
settings window itself.
"""

import pystray
from PIL import Image


class TrayIcon:
    """
    Purpose: Wraps a pystray.Icon instance with Keyify's menu and callbacks.
    """

    def __init__(self, icon_path, on_open_settings, on_quit):
        """
        Purpose: Builds the tray icon and menu.
        Parameters:
            icon_path (str) — path to the .ico/.png used for the tray icon.
            on_open_settings (callable) — invoked when "Open Settings" is clicked.
            on_quit (callable) — invoked when "Quit Keyify" is clicked; must
                fully stop hotkey listeners and exit the process.
        Returns: None.
        """
        image = Image.open(icon_path)
        menu = pystray.Menu(
            pystray.MenuItem("Open Settings", lambda: on_open_settings()),
            pystray.MenuItem("Quit Keyify", lambda: on_quit()),
        )
        self.icon = pystray.Icon("Keyify", image, "Keyify", menu)

    def run(self):
        """
        Purpose: Starts the tray icon's event loop (blocking call).
        Explanation: Should be run on its own thread since it blocks;
        main.py runs this in a background thread while Tkinter owns the
        main thread for the settings window.
        """
        self.icon.run()

    def stop(self):
        """Purpose: Removes the tray icon cleanly on app quit."""
        self.icon.stop()

    def notify(self, message, title="Keyify"):
        """
        Purpose: Shows a Windows tray balloon/toast notification.
        Parameters: message (str) — text to display. title (str) — notification title.
        Returns: None.
        Explanation: Used by spotify_client.py's notify_callback to surface
        errors like "No Spotify device detected" without needing the settings
        window to be open.
        """
        self.icon.notify(message, title)
