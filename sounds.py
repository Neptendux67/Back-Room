import math
import pygame
import os
import unicodedata
from datetime import date, datetime
from array import array
import state

sound_available = False
sounds = {}
foot_channel = None
foot_is_playing = False
sound_enabled = True
sound_volume = 0.6


def make_tone(frequency, duration_ms, volume=0.4, wobble=0.0):
    if not sound_available:
        return None

    sample_rate = pygame.mixer.get_init()[0]
    sample_count = int(sample_rate * duration_ms / 1000)
    samples = array("h")
    amplitude = int(32767 * volume)

    for i in range(sample_count):
        t = i / sample_rate
        current_frequency = frequency + math.sin(t * 35) * wobble
        fade_in = min(1.0, i / max(1, sample_rate * 0.015))
        fade_out = min(1.0, (sample_count - i) / max(1, sample_rate * 0.06))
        fade = min(fade_in, fade_out)
        value = int(math.sin(2 * math.pi * current_frequency * t) * amplitude * fade)
        samples.append(value)

    return pygame.mixer.Sound(buffer=samples.tobytes())


def load_sounds():
    if not sound_available:
        return

    sounds["click"] = make_tone(520, 80, 0.25)
    sounds["bang"] = make_tone(75, 650, 0.65, 55)
    sounds["interact"] = make_tone(360, 120, 0.25)
    sounds["repair"] = make_tone(720, 280, 0.35, 20)
    load_downloaded_sounds()


def normalized_name(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def downloads_folders():
    home = os.path.expanduser("~")
    return [
        os.path.join(home, "Downloads"),
        os.path.join(home, "T\u00e9l\u00e9chargements"),
        os.path.join(home, "Telechargements"),
    ]


def find_download_audio(keywords):
    extensions = (".wav", ".mp3", ".ogg", ".flac")
    matches = []
    today = date.today()

    for folder in downloads_folders():
        if not os.path.isdir(folder):
            continue

        try:
            filenames = os.listdir(folder)
        except OSError:
            continue

        for filename in filenames:
            path = os.path.join(folder, filename)
            if not os.path.isfile(path):
                continue
            if not filename.lower().endswith(extensions):
                continue

            clean = normalized_name(os.path.splitext(filename)[0])
            if not any(keyword in clean for keyword in keywords):
                continue

            try:
                modified = datetime.fromtimestamp(os.path.getmtime(path))
            except OSError:
                modified = datetime.min

            matches.append((modified.date() == today, modified.timestamp(), path))

    if not matches:
        return None

    matches.sort(reverse=True)
    return matches[0][2]


def load_downloaded_sounds():
    audio_files = {
        "electricite": ["electricite", "electrique", "elec"],
        "door": ["door", "porte"],
        "clef": ["clef", "cle", "key"],
        "foot": ["foot", "pas", "marche"],
    }

    for sound_name, keywords in audio_files.items():
        path = find_download_audio(keywords)
        if not path:
            continue

        try:
            sounds[sound_name] = pygame.mixer.Sound(path)
        except pygame.error:
            pass


def play_sound(name):
    if not sound_enabled or not sound_available:
        return

    sound = sounds.get(name)
    if sound:
        sound.set_volume(sound_volume)
        sound.play()


def update_footsteps(is_walking):
    global foot_channel, foot_is_playing

    sound = sounds.get("foot")
    should_play = (
        is_walking
        and sound_enabled
        and sound_available
        and sound is not None
        and state.game_state == "playing"
        and not state.game_finished
        and not state.cable_panel_open
        and not state.safe_panel_open
    )

    if should_play and not foot_is_playing:
        sound.set_volume(sound_volume)
        foot_channel = sound.play(loops=-1)
        foot_is_playing = True
    elif not should_play and foot_is_playing:
        if foot_channel:
            foot_channel.stop()
        foot_channel = None
        foot_is_playing = False
    elif should_play and foot_channel:
        foot_channel.set_volume(sound_volume)
