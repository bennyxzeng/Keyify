"""
startup.py — Manages the "Start Keyify on Windows boot" toggle via the
Windows Registry Run key.

Purpose: Adds/removes a single registry value so Keyify launches automatically
when Windows starts, without leaving stray shortcut files behind.
Documentation: Uses HKEY_CURRENT_USER so no admin rights are required.
Maintenance: If Keyify.exe's install location changes, RUN_KEY_VALUE must
point to the correct final path (handled automatically via sys.executable
when running as a compiled Nuitka exe).
"""

import sys
import winreg

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_KEY_NAME = "Keyify"


def set_start_on_boot(enabled):
    """
    Purpose: Enables or disables Keyify auto-launch at Windows login.
    Parameters: enabled (bool) — True to add the registry entry, False to remove it.
    Returns: None.

    Explanation: sys.executable resolves to Keyify.exe's actual path when
    running as a compiled binary, so this works correctly post-Nuitka build
    without hardcoding any install path.
    """
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            exe_path = sys.executable
            winreg.SetValueEx(key, RUN_KEY_NAME, 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
        else:
            try:
                winreg.DeleteValue(key, RUN_KEY_NAME)
            except FileNotFoundError:
                pass  # Already disabled; nothing to remove.
    finally:
        winreg.CloseKey(key)


def is_start_on_boot_enabled():
    """
    Purpose: Checks whether the registry Run key entry currently exists.
    Parameters: None.
    Returns: bool — True if Keyify is registered to start on boot.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, RUN_KEY_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
