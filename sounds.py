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
sound_volume = 1.0
music_volume = 1.0

AUDIO_FILES = {
    "click": "click.wav",
    "bang": "bang.wav",
    "interact": "interact.wav",
    "repair": "repair.wav",
    "electricite": "electricity.wav",
    "door": "door-opening.wav",
    "clef": "key-collect.wav",
    "foot": "footsteps.wav",
    "ending": "ending.wav",
    "main_menu": "main_menu.wav",
    "monster_scream": "monstre_cri.mp3",
    "pickup_item": "pickup-item.wav",
    "shredder": "broyeur.wav",
    "level1": "level1.wav",
    "tick": "tick.wav",
    "screamer": "screamer.wav",
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
    sounds["door"] = make_tone(180, 350, 0.4, 25)
    sounds["tick"] = make_tone(880, 30, 0.12)
    sounds["screamer"] = make_tone(160, 500, 0.5, 120)


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
        sound.set_volume(min(1.0, sound_volume * 1.35))
        foot_channel = sound.play(loops=-1)
        foot_is_playing = True
    elif not should_play and foot_is_playing:
        if foot_channel:
            foot_channel.stop()
        foot_channel = None
        foot_is_playing = False
    elif should_play and foot_channel:
        foot_channel.set_volume(min(1.0, sound_volume * 1.35))


MUSIC_TRACKS = ["ambient-music", "mongolian-secret"]

def start_menu_music():
    if not sound_available or not sound_enabled:
        return
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.set_volume(music_volume)
        return
    path = os.path.join(_audio_dir(), "main_menu.wav")
    if os.path.isfile(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(loops=-1)


def stop_menu_music():
    if sound_available:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()


def stop_all_sounds():
    if sound_available:
        pygame.mixer.stop()
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()


def start_ambient_music(track=None):
    if not sound_available or not sound_enabled:
        return
    if track is None:
        try:
            import settings
            track = settings.get().get("music_track", "ambient-music")
        except Exception:
            track = "ambient-music"
    path = os.path.join(_audio_dir(), track + ".wav")
    if not os.path.isfile(path):
        path = os.path.join(_audio_dir(), "ambient-music.wav")
    if os.path.isfile(path):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.music.load(path)
        vol = music_volume * (0.50 if "mongolian" in track else 0.50)
        pygame.mixer.music.set_volume(vol)
        pygame.mixer.music.play(loops=-1)


def stop_ambient_music():
    if sound_available:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()


def start_ending_music():
    if not sound_available or not sound_enabled:
        return
    path = os.path.join(_audio_dir(), "ending.wav")
    if os.path.isfile(path):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play()


def start_level_music(day):
    if not sound_available or not sound_enabled:
        return
    if day == 1 or day == 5:
        return
    path = os.path.join(_audio_dir(), f"level{day}.wav")
    if not os.path.isfile(path):
        return
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    pygame.mixer.music.load(path)
    pygame.mixer.music.set_volume(music_volume * 0.50)
    pygame.mixer.music.play(loops=-1)


def start_chase_music():
    if not sound_available or not sound_enabled:
        return
    path = os.path.join(_audio_dir(), "level5.wav")
    if not os.path.isfile(path):
        return
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    pygame.mixer.music.load(path)
    pygame.mixer.music.set_volume(music_volume * 0.50)
    pygame.mixer.music.play(loops=-1)
