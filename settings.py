import json
import os
import pygame
import config
import sounds

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

RESOLUTIONS = [(1920, 1080), (1280, 720), (2560, 1440), (1600, 900), (1366, 768)]

DEFAULTS = {
    "sound_volume": 1.0,
    "music_volume": 1.0,
    "fullscreen": True,
    "resolution_index": 0,
    "fps_cap": 144,
    "music_track": "ambient-music",
}

_current = dict(DEFAULTS)


def get():
    return _current


def resolution():
    return RESOLUTIONS[_current["resolution_index"]]


def apply():
    w, h = resolution()
    flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if _current["fullscreen"] else 0
    config.WIDTH = w
    config.HEIGHT = h
    config.FPS_CAP = _current["fps_cap"]
    config.screen = pygame.display.set_mode((w, h), flags)
    sounds.sound_volume = _current["sound_volume"]
    sounds.music_volume = _current["music_volume"]

    import render
    render.WIDTH = w
    render.HEIGHT = h
    render.clear_pause_bg()
    render._BODY_OVERLAY = None
    render._SHADE_PANEL = None
    render._MENU_VIGNETTE = None
    render._MENU_BG = None
    render._DUST = None
    render._VIGNETTE_SURF = None

    logo_path = os.path.join(os.path.dirname(__file__), "assets", "ui", "logo.png")
    if os.path.isfile(logo_path):
        try:
            icon = pygame.image.load(logo_path)
            pygame.display.set_icon(icon)
        except pygame.error:
            pass


def save():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(_current, f, indent=2)
    except OSError:
        pass


def load():
    global _current
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        for k in DEFAULTS:
            if k in data:
                _current[k] = data[k]
    except (OSError, json.JSONDecodeError):
        _current = dict(DEFAULTS)
