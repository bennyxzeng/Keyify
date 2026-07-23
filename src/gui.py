"""
gui.py — Tkinter settings window: keybind rebinding, credentials entry,
and startup toggles.

Purpose: The only user-facing window in Keyify. Reachable via the tray icon's
"Open Settings" item; closing it hides to tray rather than quitting the app.
Documentation: Reads/writes through config.py exclusively — never touches
the JSON file directly — so persistence logic stays in one place.
Maintenance: Each keybind row is built generically from config["keybinds"]
so adding a new action later only requires updating config.DEFAULT_CONFIG
and method_map in hotkey_manager.py; no GUI code changes needed.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import config as config_module
import hotkey_manager
import startup


ACTION_LABELS = {
    "next_track": "Next Track",
    "previous_track": "Previous Track",
    "play_pause": "Play / Pause",
    "volume_up": "Volume Up (+5)",
    "volume_down": "Volume Down (-5)",
    "toggle_shuffle": "Toggle Shuffle",
    "toggle_repeat": "Toggle Repeat",
}


class SettingsWindow(tk.Tk):
    """
    Purpose: Main settings GUI. Holds live references to the shared config
    dict and re-registers hotkeys whenever a change is saved.
    """

    def __init__(self, config, get_controller, on_hide_to_tray):
        """
        Purpose: Builds the full settings window layout.
        Parameters:
            config (dict) — current app config (mutated in place, then saved).
            get_controller (callable) — function that returns a live, valid
                SpotifyController (creating one lazily if credentials were
                just entered), or None if credentials are still missing.
            on_hide_to_tray (callable) — called instead of destroying the window
                when the user clicks the window's close (X) button, per the
                requirement that closing the window doesn't quit the app.
        Returns: None.
        """
        super().__init__()
        self.config_data = config
        self.get_controller = get_controller
        self.title("Keyify Settings")
        self.geometry("480x560")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", on_hide_to_tray)

        self._keybind_vars = {}
        self._listening_for_action = None  # Tracks which row is capturing a new combo.

        self._build_credentials_section()
        self._build_keybinds_section()
        self._build_toggles_section()
        self._build_action_buttons()

    def _build_credentials_section(self):
        """Purpose: Client ID/Secret entry fields, pre-filled from saved config."""
        frame = ttk.LabelFrame(self, text="Spotify Developer Credentials")
        frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(frame, text="Client ID:").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.client_id_var = tk.StringVar(value=self.config_data["client_id"])
        ttk.Entry(frame, textvariable=self.client_id_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="Client Secret:").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        self.client_secret_var = tk.StringVar(value=self.config_data["client_secret"])
        ttk.Entry(frame, textvariable=self.client_secret_var, width=40, show="*").grid(row=1, column=1, padx=5)

    def _build_keybinds_section(self):
        """
        Purpose: Renders one row per action with its current keybind and a
        "Change" button that starts capture mode.
        Explanation: Rows are generated from ACTION_LABELS/config["keybinds"]
        rather than hardcoded, so the layout stays correct if actions are
        added/removed in future versions.
        """
        frame = ttk.LabelFrame(self, text="Keybinds")
        frame.pack(fill="both", expand=True, padx=10, pady=8)

        for i, (action_name, label) in enumerate(ACTION_LABELS.items()):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=3)

            display_var = tk.StringVar(value=self.config_data["keybinds"][action_name])
            self._keybind_vars[action_name] = display_var
            ttk.Label(frame, textvariable=display_var, width=22, relief="sunken").grid(
                row=i, column=1, padx=5
            )

            ttk.Button(
                frame, text="Change",
                command=lambda a=action_name: self._start_capture(a)
            ).grid(row=i, column=2, padx=5)

    def _build_toggles_section(self):
        """Purpose: Start-on-boot and start-minimized checkboxes."""
        frame = ttk.LabelFrame(self, text="Startup Options")
        frame.pack(fill="x", padx=10, pady=8)

        self.start_on_boot_var = tk.BooleanVar(value=self.config_data["start_on_boot"])
        ttk.Checkbutton(
            frame, text="Start Keyify when Windows starts", variable=self.start_on_boot_var
        ).pack(anchor="w", padx=5, pady=2)

        self.start_minimized_var = tk.BooleanVar(value=self.config_data["start_minimized"])
        ttk.Checkbutton(
            frame, text="Start minimized to tray", variable=self.start_minimized_var
        ).pack(anchor="w", padx=5, pady=2)

    def _build_action_buttons(self):
        """Purpose: Save and Reset-to-Default buttons at the bottom of the window."""
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(frame, text="Reset Keybinds to Default", command=self._reset_defaults).pack(
            side="left"
        )
        ttk.Button(frame, text="Save Settings", command=self._save_settings).pack(side="right")

    def _start_capture(self, action_name):
        """
        Purpose: Puts the given row into "listening" mode so the next key
        combo pressed becomes the new binding for that action.
        Parameters: action_name (str) — which action's row triggered capture.
        Returns: None.

        Explanation: Uses Tkinter's bind("<KeyPress>") temporarily on the
        window itself, combined with checking modifier key state, to capture
        a live combo without needing a separate library during GUI-only capture.
        """
        self._listening_for_action = action_name
        self._keybind_vars[action_name].set("Press new combo...")
        self.bind("<KeyPress>", self._on_capture_keypress)

    def _on_capture_keypress(self, event):
        """
        Purpose: Builds a keybind string from the captured Tkinter key event
        and hands it off to conflict checking / saving.
        Parameters: event (tk.Event) — Tkinter key press event.
        Returns: None.
        """
        if not self._listening_for_action:
            return

        modifiers = []
        if event.state & 0x4:
            modifiers.append("control")
        if event.state & 0x20000 or event.state & 0x8:
            modifiers.append("alt")
        if event.state & 0x1:
            modifiers.append("shift")

        key = event.keysym.lower()
        if key in ("control_l", "control_r", "alt_l", "alt_r", "shift_l", "shift_r"):
            return  # Ignore standalone modifier presses; wait for the full combo.

        new_keybind = "+".join(modifiers + [key]) if modifiers else key
        action_name = self._listening_for_action
        self.unbind("<KeyPress>")
        self._listening_for_action = None

        self._apply_new_keybind(action_name, new_keybind)

    def _apply_new_keybind(self, action_name, new_keybind):
        """
        Purpose: Checks for conflicts before committing a captured keybind,
        prompting the user to override if another action already uses it.
        Parameters:
            action_name (str) — the action being rebound.
            new_keybind (str) — the newly captured combo string.
        Returns: None.

        Explanation: Implements the spec'd behavior: if new_keybind collides
        with another action, ask to override; if confirmed, the OLD action
        reverts to its factory default rather than being left unbound.
        """
        conflicting_action = hotkey_manager.find_conflicting_action(
            self.config_data, new_keybind, action_name
        )
        if conflicting_action:
            confirmed = messagebox.askyesno(
                "Keybind Already In Use",
                f"'{new_keybind}' is already assigned to "
                f"'{ACTION_LABELS[conflicting_action]}'.\n\n"
                "Do you want to reassign it here? The other action will be "
                "reset to its default keybind.",
            )
            if not confirmed:
                self._keybind_vars[action_name].set(self.config_data["keybinds"][action_name])
                return
            default_for_conflict = config_module.DEFAULT_CONFIG["keybinds"][conflicting_action]
            self.config_data["keybinds"][conflicting_action] = default_for_conflict
            self._keybind_vars[conflicting_action].set(default_for_conflict)

        self.config_data["keybinds"][action_name] = new_keybind
        self._keybind_vars[action_name].set(new_keybind)

    def _reset_defaults(self):
        """Purpose: Restores all keybinds to factory defaults and refreshes the UI."""
        config_module.reset_keybinds_to_default(self.config_data)
        for action_name, var in self._keybind_vars.items():
            var.set(self.config_data["keybinds"][action_name])
        controller = self.get_controller()
        if controller is not None:
            hotkey_manager.register_all(self.config_data, controller)
        messagebox.showinfo("Keyify", "Keybinds reset to default.")

    def _save_settings(self):
        """
        Purpose: Writes all current GUI field values back into config_data,
        persists to disk, applies the start-on-boot registry change, and
        re-registers hotkeys so changes take effect immediately.
        Returns: None.
        """
        self.config_data["client_id"] = self.client_id_var.get().strip()
        self.config_data["client_secret"] = self.client_secret_var.get().strip()
        self.config_data["start_on_boot"] = self.start_on_boot_var.get()
        self.config_data["start_minimized"] = self.start_minimized_var.get()

        config_module.save_config(self.config_data)
        startup.set_start_on_boot(self.config_data["start_on_boot"])

        controller = self.get_controller()
        if controller is not None:
            hotkey_manager.register_all(self.config_data, controller)
        else:
            messagebox.showwarning(
                "Keyify",
                "Settings saved, but hotkeys were not activated — "
                "please double-check your Client ID and Client Secret."
            )
            return

        messagebox.showinfo("Keyify", "Settings saved.")
