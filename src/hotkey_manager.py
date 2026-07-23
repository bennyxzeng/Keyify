"""
hotkey_manager.py — Registers/unregisters Windows global hotkeys and maps
them to Keyify actions, using btsdev's global_hotkeys library.

Purpose: Single place where keybind strings from config.py get translated
into actual system-wide key listeners.
Documentation: Called by main.py on startup and by gui.py whenever the user
rebinds a key, so listeners always reflect the latest saved config.
Maintenance: register_hotkey() from this library expects the combo as a
PLAIN STRING like "control+alt+right" (joined with "+"), NOT a Python list.
Passing a list triggers the library's internal _syntax_check() to raise an
exception, which was previously being silently swallowed by our own
try/except -- this is why hotkeys appeared to register with no error but
never actually fired.
"""

from global_hotkeys import (
    register_hotkey,
    start_checking_hotkeys,
    stop_checking_hotkeys,
    clear_hotkeys,
)

_action_bindings = {}


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

    Explanation: keybind_str is already stored in config.json as something
    like "control+alt+right", which matches EXACTLY what register_hotkey()
    expects as its first argument -- no list conversion needed. This was the
    root cause of hotkeys silently not working: we were incorrectly splitting
    this string into a list before passing it in.
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
        action_func = method_map[action_name]
        try:
            register_hotkey(keybind_str, action_func, None)
            _action_bindings[action_name] = keybind_str
        except Exception as e:
            print(f"Failed to register hotkey '{keybind_str}' for {action_name}: {e}")
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
    """
    stop_checking_hotkeys()
    clear_hotkeys()