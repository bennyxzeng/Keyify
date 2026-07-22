"""
config.py — Handles loading, saving, and resetting Keyify's persistent settings.

Purpose: Centralizes all user-configurable state (keybinds, Spotify credentials,
startup toggles) so the rest of the app never touches the filesystem directly.
Documentation: Settings live in %APPDATA%\Keyify\config.json as plaintext JSON.
Maintenance: If new settings fields are added later, DEFAULT_CONFIG should be
updated and load_config() will automatically backfill missing keys on old files.
"""

import json
import os
import copy

# Purpose: Central location for the app's folder name so it's not hardcoded
# in multiple places. Ties into startup.py and main.py for consistency.
APP_FOLDER_NAME = "Keyify"

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_FOLDER_NAME)
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.json")

# Purpose: Defines the default keybinds and settings shipped with Keyify.
# Explanation: Ctrl+Alt combos were chosen because they don't collide with
# built-in Windows shortcuts (Ctrl+Alt+Delete/Esc/Tab are the only reserved ones).
# Documentation: This dict is the single source of truth for "factory defaults"
# used both on first run and when the user clicks "Reset to Defaults."
DEFAULT_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "redirect_port": 8888,
    "start_on_boot": False,
    "start_minimized": True,
    "keybinds": {
        "next_track": "control+alt+right",
        "previous_track": "control+alt+left",
        "play_pause": "control+alt+space",
        "volume_up": "control+alt+up",
        "volume_down": "control+alt+down",
        "toggle_shuffle": "control+alt+s",
        "toggle_repeat": "control+alt+r",
    },
}


def _ensure_appdata_dir():
    """
    Purpose: Makes sure %APPDATA%\Keyify exists before any read/write attempt.
    Parameters: None.
    Returns: None.

    Explanation: os.makedirs with exist_ok avoids race conditions/errors if the
    folder was already created in a previous run.
    """
    os.makedirs(APPDATA_DIR, exist_ok=True)


def load_config():
    """
    Purpose: Loads the user's saved config, falling back to defaults if the
    file is missing, corrupted, or missing keys.
    Parameters: None.
    Returns: dict — the fully-populated config (guaranteed to have every key
    present in DEFAULT_CONFIG, even on a corrupted or partial file).

    Explanation: We deep-copy DEFAULT_CONFIG first, then overlay whatever valid
    keys exist in the saved file on top of it. This means a corrupted file (or
    one from an older Keyify version missing new fields) never crashes the app —
    it just silently falls back to defaults for the broken/missing parts.
    Maintenance: Any new top-level or nested "keybinds" key added to
    DEFAULT_CONFIG automatically gets backfilled for existing users.
    """
    _ensure_appdata_dir()
    config = copy.deepcopy(DEFAULT_CONFIG)

    if not os.path.exists(CONFIG_PATH):
        save_config(config)
        return config

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        for key, value in saved.items():
            if key == "keybinds" and isinstance(value, dict):
                config["keybinds"].update(value)
            elif key in config:
                config[key] = value
    except (json.JSONDecodeError, OSError):
        # Corrupted file: fall back to defaults and overwrite the bad file.
        save_config(config)

    return config


def save_config(config):
    """
    Purpose: Persists the given config dict to disk as JSON.
    Parameters: config (dict) — the full config object to save.
    Returns: None.

    Explanation: Called after any settings change (keybind rebind, credential
    entry, toggle change) so changes survive app restarts, per the requirement
    that user customizations are never reset on relaunch.
    """
    _ensure_appdata_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def reset_keybinds_to_default(config):
    """
    Purpose: Resets only the keybinds portion of the config back to factory
    defaults, leaving credentials and toggles untouched.
    Parameters: config (dict) — the current in-memory config.
    Returns: dict — the updated config with default keybinds restored.

    Explanation: This backs the "Reset to Default Keybinds" button in the GUI.
    We intentionally scope the reset to just "keybinds" so users don't lose
    their Spotify credentials or boot/minimize preferences by accident.
    """
    config["keybinds"] = copy.deepcopy(DEFAULT_CONFIG["keybinds"])
    save_config(config)
    return config


def wipe_config():
    """
    Purpose: Fully deletes the Keyify config file and folder — used for the
    "uninstall means all user data is gone" requirement.
    Parameters: None.
    Returns: None.

    Explanation: Called from the uninstall helper script, not from the running
    app itself, so a redownload of Keyify is treated as a brand-new user with
    no leftover credentials or keybinds.
    """
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    try:
        os.rmdir(APPDATA_DIR)
    except OSError:
        pass  # Folder not empty or already gone; safe to ignore.
