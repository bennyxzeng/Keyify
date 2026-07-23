# Keyify

Keyify lets you control Spotify playback on Windows using **global hotkeys** — skip tracks, play/pause, adjust volume, and toggle shuffle/repeat, even while Spotify is minimized or running in the background.

## Features

- **Next Track** — skip to the next song
- **Previous Track** — go back to the previous song
- **Play / Pause** — toggle playback
- **Volume Up** — increase volume by 5 (e.g. 15 -> 20)
- **Volume Down** — decrease volume by 5 (e.g. 20 -> 15)
- **Toggle Shuffle** — turn shuffle on/off
- **Toggle Repeat** — cycle repeat mode on/off
- Runs quietly in the **system tray** — right-click for Settings or to Quit
- Fully **customizable keybinds**, saved automatically and restored on every launch
- One-click **Reset to Default Keybinds**
- Optional **Start on Windows boot** and **Start minimized to tray**

## Default Keybinds

| Action | Default Keybind |
|---|---|
| Next Track | Ctrl + Alt + Right Arrow |
| Previous Track | Ctrl + Alt + Left Arrow |
| Play / Pause | Ctrl + Alt + Space |
| Volume Up (+5) | Ctrl + Alt + Up Arrow |
| Volume Down (-5) | Ctrl + Alt + Down Arrow |
| Toggle Shuffle | Ctrl + Alt + S |
| Toggle Repeat | Ctrl + Alt + R |

All keybinds can be changed at any time from the Settings window (right-click the tray icon -> **Open Settings**). Custom keybinds are saved automatically and will not reset when you close or reopen Keyify.

## Requirements

- Windows 10 or later
- A Spotify Premium account
- An active internet connection

## Setup Guide

Keyify needs a Spotify Developer app to talk to your Spotify account. This is a one-time setup.

1. Go to [Spotify for Developers](https://developer.spotify.com/dashboard) and log in with your Spotify account.
2. Click **Create App**, give it any name/description (e.g. "Keyify"), and set the **Redirect URI** to `http://127.0.0.1:8888/callback`.
3. Once created, open the app's settings page and copy the **Client ID** and **Client Secret**.
4. Go to the **User Management** tab on your app's settings page and add your own name and email address. As of February 2026, Spotify requires every account that will authorize the app to be explicitly added here (up to 5 users), even if you're the only person using it. Skipping this step will cause Keyify's login to silently fail.
5. Make sure the Spotify account you used to create the app has an active **Spotify Premium** subscription — required for both the app owner and playback control in general.
6. Open Keyify, right-click the tray icon, and select **Open Settings**.
7. Paste your Client ID and Client Secret into the corresponding fields and click **Save Settings**.
8. A browser tab will briefly open to complete login — if you're already logged into Spotify in your browser, it may close automatically within a second, which is expected and means authorization succeeded.

## Installation

1. Go to the [Releases](../../releases) page and download the most recent `Keyify-vX.X.X-windows.zip`.
2. Extract the zip file to any folder.
3. Run `Keyify.exe`.
4. Follow the **Setup Guide** above to connect your Spotify account.

> **Note:** Since Keyify is not code-signed, Windows SmartScreen may show a warning the first time you run it. Click **More info -> Run anyway** to proceed. This is expected for small, independently distributed apps.

## Notes on Behavior

- Keyify always targets **this computer's** Spotify app, even if another device (phone, speaker) is currently active — this keeps background control consistent with the app's purpose.
- If Spotify isn't open on this computer, Keyify will show a tray notification asking you to open it.
- Volume changes are clamped between 0 and 100.
- Closing the Settings window does **not** quit Keyify — it keeps running in the tray. Use **Quit Keyify** from the tray menu to fully exit.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details. Third-party dependency licenses are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Built With

- [Spotipy](https://spotipy.readthedocs.io/) — Python client for the Spotify Web API
- [Spotify Web API](https://developer.spotify.com/documentation/web-api) — playback control (play/pause, skip, volume, shuffle, repeat)
- [global_hotkeys](https://github.com/btsdev/global_hotkeys) by btsdev — Windows global hotkey registration
- [pystray](https://github.com/moses-palmer/pystray) — system tray icon and menu
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — settings GUI
- [Nuitka](https://nuitka.net/) — compiles Keyify into a standalone Windows executable
- [GitHub Actions](https://github.com/features/actions) — automated build and release pipeline
