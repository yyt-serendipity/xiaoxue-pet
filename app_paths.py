"""Separate read-only bundled assets from per-user installed-app settings."""
import os
from pathlib import Path


def settings_directory(source_directory, frozen=False):
    if not frozen:
        return Path(source_directory)
    base = Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local'))
    directory = base/'XiaoxuePet'
    directory.mkdir(parents=True, exist_ok=True)
    return directory
