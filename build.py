"""
build.py — Compiles Keyify into a standalone Keyify.exe using Nuitka.

Purpose: Automates the exact Nuitka invocation needed so contributors (or CI)
don't have to remember all the flags by hand.
Documentation: Produces a single-file, windowed (no console) executable with
the custom icon bundled in, matching the README's "download and run" flow.
Maintenance: If new data files (icons, assets) are added, update the
--include-data-dir flag below.
"""

import subprocess
import sys
import os

SRC_ENTRY = os.path.join("src", "main.py")
ICON_PATH = os.path.join("assets", "icon.ico")

NUITKA_CMD = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--onefile",
    "--assume-yes-for-downloads",
    "--enable-plugin=tk-inter",
    "--windows-console-mode=disable",
    f"--windows-icon-from-ico={ICON_PATH}",
    "--include-data-dir=assets=assets",
    "--output-filename=Keyify.exe",
    "--output-dir=dist",
    SRC_ENTRY,
]

if __name__ == "__main__":
    print("Running:", " ".join(NUITKA_CMD))
    subprocess.run(NUITKA_CMD, check=True)
