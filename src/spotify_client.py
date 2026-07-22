"""
spotify_client.py — Wraps Spotipy calls for all playback actions Keyify exposes.

Purpose: Isolates every direct Spotify Web API interaction in one place so
hotkey_manager.py and gui.py never call Spotipy directly.
Documentation: Handles OAuth setup, token refresh (automatic via Spotipy),
device targeting (prefers the local Computer device), and volume clamping.
Maintenance: If Spotify changes an endpoint or Spotipy's method signatures,
only this file needs updating — callers are unaffected.
"""

import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

SCOPES = "user-modify-playback-state user-read-playback-state"

# Purpose: Simple in-memory rate limiter to stop runaway hotkey spam (e.g. a
# key stuck under a book) from hammering Spotify's API and getting Keyify
# rate-limited or banned temporarily.
# Explanation: Tracks the last call timestamp per action; calls made faster
# than MIN_INTERVAL are silently dropped rather than queued, since dropping a
# few skips during accidental key-holds is the desired UX (per spec).
MIN_INTERVAL_SECONDS = 0.35
_last_call_times = {}


def _is_rate_limited(action_name):
    """
    Purpose: Checks whether an action was invoked too recently to allow again.
    Parameters: action_name (str) — unique key identifying the hotkey action.
    Returns: bool — True if the call should be dropped (too soon), else False.
    """
    now = time.monotonic()
    last = _last_call_times.get(action_name, 0)
    if now - last < MIN_INTERVAL_SECONDS:
        return True
    _last_call_times[action_name] = now
    return False


class SpotifyController:
    """
    Purpose: Wraps a single authenticated Spotipy client and exposes one
    method per Keyify action (next, previous, play/pause, volume, shuffle,
    repeat), each handling errors and device targeting consistently.
    """

    def __init__(self, client_id, client_secret, redirect_port, notify_callback):
        """
        Purpose: Builds the Spotipy client using Authorization Code flow with
        a local redirect URI, and stores a callback for surfacing user-facing
        error/status messages (e.g. tray notifications).
        Parameters:
            client_id (str) — Spotify app Client ID from the user's config.
            client_secret (str) — Spotify app Client Secret from the user's config.
            redirect_port (int) — local port for the OAuth redirect (default 8888,
                with fallback handled by caller if the port is taken).
            notify_callback (callable) — function taking a str message, used to
                show tray/GUI notifications for errors (no internet, no device, etc).
        Returns: None.

        Explanation: Spotipy's SpotifyOAuth handles token exchange AND silent
        refresh internally via its cache — we never manually manage tokens.
        """
        self.notify = notify_callback
        redirect_uri = f"http://127.0.0.1:{redirect_port}/callback"
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SCOPES,
            cache_path=None,  # caller supplies a cache path in %APPDATA%\Keyify
            open_browser=True,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def _get_target_device_id(self):
        """
        Purpose: Determines which Spotify device Keyify should send commands to.
        Parameters: None.
        Returns: str or None — device_id of the local computer if found among
        available devices, else None if Spotify isn't open anywhere reachable.

        Explanation: Per spec, Keyify should always prefer controlling THIS
        computer's Spotify instance even if a phone/speaker is the "active"
        device, since that's the app's whole purpose (background control on
        the PC). We match on device type "Computer" rather than is_active.
        """
        try:
            devices = self.sp.devices().get("devices", [])
        except (SpotifyException, ConnectionError):
            self.notify("Unable to reach Spotify. Check your internet connection.")
            return None

        if not devices:
            self.notify("No Spotify device detected. Please open Spotify.")
            return None

        for device in devices:
            if device.get("type") == "Computer":
                return device["id"]

        # No computer device found among available devices.
        self.notify("No Spotify device detected. Please open Spotify.")
        return None

    def _safe_call(self, action_name, func, *args, **kwargs):
        """
        Purpose: Shared error-handling wrapper for every playback action below.
        Parameters:
            action_name (str) — label used for rate-limit tracking and errors.
            func (callable) — the Spotipy method to invoke.
            *args/**kwargs — forwarded to func.
        Returns: bool — True if the call succeeded, False if skipped/failed.

        Explanation: Centralizes rate limiting, device-not-found handling, and
        network/API error catching so each public method below stays a one-liner.
        """
        if _is_rate_limited(action_name):
            return False
        device_id = self._get_target_device_id()
        if device_id is None:
            return False
        try:
            func(*args, device_id=device_id, **kwargs)
            return True
        except SpotifyException as e:
            if e.http_status == 429:
                self.notify("Spotify API rate limit reached. Slow down a bit.")
            elif e.http_status >= 500:
                self.notify("Spotify servers are unavailable. Try again shortly.")
            else:
                self.notify(f"Spotify error: {e.msg}")
            return False
        except ConnectionError:
            self.notify("No internet connection. Keyify actions are paused.")
            return False

    def next_track(self):
        """Purpose: Skips to the next track on the target device. Returns: bool success."""
        return self._safe_call("next_track", self.sp.next_track)

    def previous_track(self):
        """Purpose: Goes back to the previous track on the target device. Returns: bool success."""
        return self._safe_call("previous_track", self.sp.previous_track)

    def play_pause(self):
        """
        Purpose: Toggles play/pause based on current playback state.
        Returns: bool success.
        Explanation: Spotify has no single "toggle" endpoint, so we check
        is_playing first, then call pause or start/resume accordingly.
        """
        if _is_rate_limited("play_pause"):
            return False
        device_id = self._get_target_device_id()
        if device_id is None:
            return False
        try:
            playback = self.sp.current_playback()
            is_playing = playback.get("is_playing", False) if playback else False
            if is_playing:
                self.sp.pause_playback(device_id=device_id)
            else:
                self.sp.start_playback(device_id=device_id)
            return True
        except SpotifyException as e:
            self.notify(f"Spotify error: {e.msg}")
            return False
        except ConnectionError:
            self.notify("No internet connection. Keyify actions are paused.")
            return False

    def _adjust_volume(self, delta):
        """
        Purpose: Shared logic for volume up/down, clamping to 0-100 and
        skipping the call entirely if already at the boundary (per spec, this
        avoids wasted/rate-limited API calls at 0 or 100).
        Parameters: delta (int) — +5 or -5.
        Returns: bool success.
        """
        action_name = "volume_up" if delta > 0 else "volume_down"
        if _is_rate_limited(action_name):
            return False
        device_id = self._get_target_device_id()
        if device_id is None:
            return False
        try:
            playback = self.sp.current_playback()
            current_volume = playback["device"]["volume_percent"] if playback else 50
            new_volume = max(0, min(100, current_volume + delta))
            if new_volume == current_volume:
                return False  # Already at 0 or 100; nothing to do.
            self.sp.volume(new_volume, device_id=device_id)
            return True
        except SpotifyException as e:
            self.notify(f"Spotify error: {e.msg}")
            return False
        except ConnectionError:
            self.notify("No internet connection. Keyify actions are paused.")
            return False

    def volume_up(self):
        """Purpose: Increases volume by 5, clamped at 100. Returns: bool success."""
        return self._adjust_volume(5)

    def volume_down(self):
        """Purpose: Decreases volume by 5, clamped at 0. Returns: bool success."""
        return self._adjust_volume(-5)

    def toggle_shuffle(self):
        """
        Purpose: Flips the current shuffle state (on->off or off->on).
        Returns: bool success.
        """
        if _is_rate_limited("toggle_shuffle"):
            return False
        device_id = self._get_target_device_id()
        if device_id is None:
            return False
        try:
            playback = self.sp.current_playback()
            currently_shuffled = playback.get("shuffle_state", False) if playback else False
            self.sp.shuffle(not currently_shuffled, device_id=device_id)
            return True
        except SpotifyException as e:
            self.notify(f"Spotify error: {e.msg}")
            return False
        except ConnectionError:
            self.notify("No internet connection. Keyify actions are paused.")
            return False

    def toggle_repeat(self):
        """
        Purpose: Cycles repeat mode between 'off' and 'context' (repeat playlist/album).
        Returns: bool success.
        Explanation: Spotify supports 'track' repeat too, but Keyify only
        toggles between off/context to keep the single-hotkey UX simple.
        """
        if _is_rate_limited("toggle_repeat"):
            return False
        device_id = self._get_target_device_id()
        if device_id is None:
            return False
        try:
            playback = self.sp.current_playback()
            current_state = playback.get("repeat_state", "off") if playback else "off"
            new_state = "off" if current_state != "off" else "context"
            self.sp.repeat(new_state, device_id=device_id)
            return True
        except SpotifyException as e:
            self.notify(f"Spotify error: {e.msg}")
            return False
        except ConnectionError:
            self.notify("No internet connection. Keyify actions are paused.")
            return False
