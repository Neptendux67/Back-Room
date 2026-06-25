import math
import pygame
import os
from array import array
import state

sound_available = False
sounds = {}
foot_channel = None
foot_is_playing = False
sound_enabled = True
sound_volume = 0.6

AUDIO_FILES = {
    "click": "click.wav",
    "bang": "bang.wav",
    "interact": "interact.wav",
    "repair": "repair.wav",
    "electricite": "electricity.wav",
    "door": "door.wav",
    "clef": "key-collect.wav",
    "foot": "footsteps.wav",
}


def _audio_dir():
    return os.path.join(os.path.dirname(__file__), "assets", "audio")


def _load_audio_file(filename):
    path = os.path.join(_audio_dir(), filename)
    if not os.path.isfile(path):
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        return None


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


def _fallback_sounds():
    sounds["click"] = make_tone(520, 80, 0.25)
    sounds["bang"] = make_tone(75, 650, 0.65, 55)
    sounds["interact"] = make_tone(360, 120, 0.25)
    sounds["repair"] = make_tone(720, 280, 0.35, 20)


def load_sounds():
    if not sound_available:
        return

    loaded_any = False
    for name, filename in AUDIO_FILES.items():
        s = _load_audio_file(filename)
        if s is not None:
            sounds[name] = s
            loaded_any = True

    if not loaded_any:
        _fallback_sounds()


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
