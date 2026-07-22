"""
hotkey_manager.py — Registers/unregisters Windows global hotkeys and maps
them to Keyify actions, using btsdev's global_hotkeys library.

Purpose: Single place where keybind strings from config.py get translated
into actual system-wide key listeners.
Documentation: Called by main.py on startup and by gui.py whenever the user
rebinds a key, so listeners always reflect the latest saved config.
Maintenance: If we ever swap out the underlying hotkey library, only this
file needs to change — gui.py and main.py just call register_all()/rebind().
"""

from global_hotkeys import (
    register_hotkey,
    start_checking_hotkeys,
    stop_checking_hotkeys,
    clear_hotkeys,
)

# Purpose: Maps each Keyify action name to the SpotifyController method that
# should run when its hotkey fires. Populated at runtime in register_all().
_action_bindings = {}


def _parse_keybind(keybind_str):
    """
    Purpose: Converts a stored keybind string like "control+alt+right" into
    the (modifier_list, key) format global_hotkeys expects.
    Parameters: keybind_str (str) — e.g. "control+alt+s".
    Returns: tuple(list[str], str) — modifiers list and the final key.

    Explanation: Config stores keybinds as lowercase "+"-joined strings for
    easy JSON storage and GUI display; this is the one place that translates
    that format into what the hotkey library actually needs.
    """
    parts = keybind_str.lower().split("+")
    modifiers, key = parts[:-1], parts[-1]
    return modifiers, key


def register_all(config, controller, on_conflict_error=None):
    """
    Purpose: Clears any existing hotkeys and re-registers every action from
    the current config against the given SpotifyController.
    Parameters:
        config (dict) — full app config (from config.load_config()).
        controller (SpotifyController) — provides the actual action methods.
        on_conflict_error (callable, optional) — called with (action_name, keybind)
            if a hotkey fails to register (e.g. combo already claimed by
            another running application).
    Returns: None.

    Explanation: This is called once at startup and again any time the user
    saves a keybind change in the GUI, so the whole hotkey table stays in
    sync with config.json without needing a full app restart.
    """
    clear_hotkeys()
    _action_bindings.clear()

    method_map = {
        "next_track": controller.next_track,
        "previous_track": controller.previous_track,
        "play_pause": controller.play_pause,
        "volume_up": controller.volume_up,
        "volume_down": controller.volume_down,
        "toggle_shuffle": controller.toggle_shuffle,
        "toggle_repeat": controller.toggle_repeat,
    }

    for action_name, keybind_str in config["keybinds"].items():
        modifiers, key = _parse_keybind(keybind_str)
        action_func = method_map[action_name]
        try:
            # global_hotkeys expects: register_hotkey(key_combo_list, on_press, on_release)
            register_hotkey(modifiers + [key], action_func, None)
            _action_bindings[action_name] = keybind_str
        except Exception:
            if on_conflict_error:
                on_conflict_error(action_name, keybind_str)

    start_checking_hotkeys()


def find_conflicting_action(config, new_keybind, action_being_set):
    """
    Purpose: Checks whether new_keybind is already assigned to a different
    action, to support the "override or cancel" prompt in the GUI.
    Parameters:
        config (dict) — current app config.
        new_keybind (str) — the keybind the user is trying to assign.
        action_being_set (str) — the action currently being rebound (excluded
            from the conflict check against itself).
    Returns: str or None — the name of the conflicting action, or None if free.
    """
    for action_name, keybind_str in config["keybinds"].items():
        if action_name != action_being_set and keybind_str == new_keybind:
            return action_name
    return None


def shutdown():
    """
    Purpose: Stops the hotkey listener thread cleanly on app quit.
    Parameters: None. Returns: None.
    Explanation: Called from the tray "Quit Keyify" handler so the background
    listener thread doesn't linger after the process should have exited.
    """
    stop_checking_hotkeys()
    clear_hotkeys()
