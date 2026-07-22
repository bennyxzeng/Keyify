"""
port_utils.py — Finds a free local port for the Spotify OAuth redirect URI.

Purpose: Avoids OAuth login failures when the default port 8888 is already
in use by another application on the user's machine.
Documentation: Called once during SpotifyController setup in main.py.
Maintenance: Keep the fallback range small and high-numbered to avoid
colliding with common dev ports (3000, 5000, 8000, etc).
"""

import socket

DEFAULT_PORT = 8888
FALLBACK_PORTS = [8888, 8899, 8901, 8923, 8965]


def find_available_port():
    """
    Purpose: Tries each candidate port in order and returns the first one
    that isn't already bound by another process.
    Parameters: None.
    Returns: int — an available local port to use for the OAuth redirect URI.

    Explanation: We bind-and-release a socket on each candidate to test
    availability. This is a lightweight, dependency-free port check.
    """
    for port in FALLBACK_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return DEFAULT_PORT  # Last resort; will surface a clear error if also taken.
