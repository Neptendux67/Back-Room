import pygame
import math
import random
import sys
import os
import unicodedata
from datetime import date, datetime
from array import array

pygame.init()

sound_available = False
try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    sound_available = True
except pygame.error:
    sound_available = False

WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Backroom - Apparament Anormal...")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 22)
BIG = pygame.font.SysFont("arial", 46, bold=True)
SMALL = pygame.font.SysFont("arial", 16)

FOV = math.pi / 3
RAYS = 460
MAX_DEPTH = 18
MOUSE_SENSITIVITY = 0.0032
PITCH_LIMIT = 400

APARTMENT_MAP = [
    "111111111111111",
    "100000100000001",
    "101110101111101",
    "100010100000001",
    "111010111011101",
    "100010000010001",
    "101111011110101",
    "100000010000001",
    "111011110111101",
    "1000000000000E1",
    "111111111111111",
]

CORRIDOR_LENGTH = 45
CORRIDOR_MAP = ["11111"] + ["10001"] * (CORRIDOR_LENGTH - 2) + ["11111"]

MAP = APARTMENT_MAP
MAP_W = len(APARTMENT_MAP[0])
MAP_H = len(APARTMENT_MAP)
EXIT_X = 13.5
EXIT_Y = 9.5
CABLE_X = 2.5
CABLE_Y = 1.5
SAFE_X = 12.5
SAFE_Y = 1.5
DAY_LIMIT = 60.0
LOADING_DURATION = 10.0
INTRO_DURATION = 12.0
ENDING_DURATION = 9.0

player_x = 1.5
player_y = 9.5
player_a = 0.0
look_pitch = 0

day = 1
day_timer = DAY_LIMIT
message = "Jour 1 : explore l'appartement. Un bruit arrive bientot..."
message_timer = 260

shake = 0
j1_event_done = False
j1_timer = 4.0

paintings = [
    {"x": 4.5, "y": 1.5, "gone": False},
    {"x": 11.5, "y": 3.5, "gone": False},
    {"x": 2.5, "y": 5.5, "gone": False},
]

sink_spots = [
    {"x": 2.5, "y": 3.5, "used": False},
    {"x": 3.5, "y": 8.5, "used": False},
    {"x": 5.5, "y": 5.5, "used": False},
    {"x": 6.5, "y": 7.5, "used": False},
    {"x": 8.5, "y": 9.5, "used": False},
    {"x": 9.5, "y": 4.5, "used": False},
    {"x": 10.5, "y": 7.5, "used": False},
    {"x": 12.5, "y": 3.5, "used": False},
]

furniture = []
windows = []

stuck = False
stuck_clicks = 0
sand_damage_timer = 0.0
MAX_HEALTH = 10
player_health = MAX_HEALTH

inventory_slots = [None, None, None, None]
selected_inventory = 0
safe_panel_open = False
safe_input = ""
safe_unlocked = False
safe_code = "314"

power_fixed = False
cable_progress = 0
cable_panel_open = False
selected_cable = None
cable_connected = {"rouge": False, "jaune": False, "bleu": False}
monster_x = 12.5
monster_y = 1.5
heartbeat = 0

ending_timer = 0
loading_timer = 0.0
intro_timer = 0.0
game_finished = False
game_state = "loading"
corridor_exit_open = False
ending_cinematic = False
death_message = ""
sound_enabled = True
sound_volume = 0.6
sounds = {}
foot_channel = None
foot_is_playing = False

pygame.mouse.set_visible(True)
pygame.event.set_grab(False)


def show_message(text, time=230):
    global message, message_timer
    message = text
    message_timer = time


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
        os.path.join(home, "Téléchargements"),
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
        and game_state == "playing"
        and not game_finished
        and not cable_panel_open
        and not safe_panel_open
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


def reset_game():
    global player_x, player_y, player_a, look_pitch
    global day, day_timer, message, message_timer, shake, j1_event_done, j1_timer
    global stuck, stuck_clicks, sand_damage_timer, player_health
    global power_fixed, monster_x, monster_y, heartbeat
    global ending_timer, game_finished, death_message
    global selected_inventory, safe_panel_open, safe_input, safe_unlocked, safe_code
    global corridor_exit_open, ending_cinematic

    player_x = 1.5
    player_y = 9.5
    player_a = 0.0
    look_pitch = 0

    day = 1
    day_timer = DAY_LIMIT
    message = "Jour 1 : explore l'appartement. Un bruit arrive bientot..."
    message_timer = 260
    shake = 0
    j1_event_done = False
    j1_timer = 4.0

    for painting in paintings:
        painting["gone"] = False
    for spot in sink_spots:
        spot["used"] = False

    stuck = False
    stuck_clicks = 0
    sand_damage_timer = 0.0
    player_health = MAX_HEALTH
    inventory_slots[:] = [None, None, None, None]
    selected_inventory = 0
    safe_panel_open = False
    safe_input = ""
    safe_unlocked = False
    safe_code = str(random.randint(100, 999))

    power_fixed = False
    reset_cable_task()
    monster_x = 12.5
    monster_y = 1.5
    heartbeat = 0

    ending_timer = 0
    game_finished = False
    death_message = ""
    corridor_exit_open = False
    ending_cinematic = False


def kill_player(reason):
    global game_state, death_message
    update_footsteps(False)
    death_message = reason
    if cable_panel_open:
        close_cable_panel()
    if safe_panel_open:
        close_safe_panel()
    game_state = "dead"
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    play_sound("bang")


def current_map():
    if day == 5:
        return CORRIDOR_MAP
    return APARTMENT_MAP


def current_map_size():
    level = current_map()
    return len(level[0]), len(level)


def wall_at(x, y):
    level = current_map()
    mx, my = int(x), int(y)
    if mx < 0 or my < 0 or my >= len(level) or mx >= len(level[0]):
        return True
    return level[my][mx] == "1"


def is_exit(x, y):
    level = current_map()
    mx, my = int(x), int(y)
    if mx < 0 or my < 0 or my >= len(level) or mx >= len(level[0]):
        return False
    return level[my][mx] == "E"


def near_exit():
    return is_exit(player_x, player_y) or distance(player_x, player_y, EXIT_X, EXIT_Y) < 0.95


def distance(ax, ay, bx, by):
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def angle_diff(a, b):
    return (a - b + math.pi) % (math.pi * 2) - math.pi


def try_move(dx, dy):
    global player_x, player_y

    nx = player_x + dx
    ny = player_y + dy

    if not wall_at(nx, player_y):
        player_x = nx
    if not wall_at(player_x, ny):
        player_y = ny


def wall_texture_color(hit_x, hit_y, depth, vertical_hit):
    shade = max(35, 225 - int(depth * 17))

    if day == 4 and not power_fixed:
        shade = max(12, shade // 3)

    base = [shade, int(shade * 0.95), int(shade * 0.78)]

    stripe_coord = hit_y if vertical_hit else hit_x
    if int(stripe_coord * 7) % 2 == 0:
        base[0] = int(base[0] * 0.82)
        base[1] = int(base[1] * 0.86)
        base[2] = int(base[2] * 0.90)

    if int((hit_x + hit_y) * 3) % 5 == 0:
        base[0] = min(255, base[0] + 12)
        base[1] = min(255, base[1] + 10)

    if not vertical_hit:
        base = [int(c * 0.82) for c in base]

    return tuple(base)


def draw_floor_ceiling():
    horizon = int(HEIGHT // 2 + look_pitch)

    if day == 4 and not power_fixed:
        ceiling = (8, 8, 12)
        floor_base = (20, 18, 17)
    else:
        ceiling = (208, 207, 192)
        floor_base = (118, 83, 49)

    if day == 5:
        ceiling = (168, 158, 108)
        floor_base = (96, 88, 56)

    pygame.draw.rect(screen, ceiling, (0, 0, WIDTH, max(0, horizon)))
    pygame.draw.rect(screen, floor_base, (0, horizon, WIDTH, HEIGHT - horizon))

    for y in range(max(horizon, 0), HEIGHT, 42):
        pygame.draw.line(screen, (82, 58, 34), (0, y), (WIDTH, y), 1)

    for x in range(0, WIDTH, 167):
        pygame.draw.line(screen, (105, 72, 39), (x, max(horizon, 0)), (x, HEIGHT), 1)

    if day != 4 or power_fixed:
        for x in range(0, WIDTH, 209):
            pygame.draw.rect(screen, (235, 231, 202), (x, 0, 122, 30))
            pygame.draw.line(screen, (170, 166, 145), (x, 30), (x + 122, 30), 1)


def cast_rays():
    start_angle = player_a - FOV / 2
    depth_buffer = [MAX_DEPTH] * WIDTH

    for ray in range(RAYS):
        ray_angle = start_angle + ray / RAYS * FOV
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 0.02
        hit_x = player_x
        hit_y = player_y

        while depth < MAX_DEPTH:
            hit_x = player_x + cos_a * depth
            hit_y = player_y + sin_a * depth

            if wall_at(hit_x, hit_y):
                break

            depth += 0.025

        depth *= math.cos(player_a - ray_angle)
        wall_h = min(HEIGHT * 2, int(HEIGHT / (depth + 0.0001)))

        fx = hit_x - int(hit_x)
        fy = hit_y - int(hit_y)
        vertical_hit = fx < 0.04 or fx > 0.96

        x_screen = int(ray * WIDTH / RAYS)
        w = int(WIDTH / RAYS) + 1
        y1 = HEIGHT // 2 - wall_h // 2 + look_pitch
        y2 = y1 + wall_h

        for sx in range(max(0, x_screen), min(WIDTH, x_screen + w)):
            depth_buffer[sx] = depth

        # Ombrage selon profondeur et jour
        shade = max(0.12, 1.0 - depth / MAX_DEPTH * 0.92)
        if day == 4 and not power_fixed:
            shade *= 0.25
        if not vertical_hit:
            shade *= 0.75

        color = wall_texture_color(hit_x, hit_y, depth, vertical_hit)
        pygame.draw.rect(screen, color, (x_screen, y1, w, wall_h))

        # Plinthe claire en bas des murs
        baseboard_h = max(2, min(12, wall_h // 13))
        base_y = min(HEIGHT, y2 - baseboard_h)
        pygame.draw.rect(screen, (214, 207, 178), (x_screen, base_y, w, baseboard_h))

    return depth_buffer


def draw_clipped_sprite(sprite, rect, dist, depth_buffer):
    if depth_buffer is None:
        screen.blit(sprite, rect.topleft)
        return True

    left = max(0, rect.left)
    right = min(WIDTH, rect.right)
    if left >= right:
        return False

    visible = False
    for sx in range(left, right):
        if dist <= depth_buffer[sx] + 0.18:
            source_x = sx - rect.left
            screen.blit(sprite, (sx, rect.top), (source_x, 0, 1, rect.height))
            visible = True

    return visible


CABLE_COLORS = {
    "rouge": (214, 50, 45),
    "jaune": (236, 198, 55),
    "bleu": (60, 120, 220),
}


def color_with_light(color, light):
    return (
        max(0, min(255, int(color[0] * light))),
        max(0, min(255, int(color[1] * light))),
        max(0, min(255, int(color[2] * light))),
    )


def draw_wood(surface, rect, base):
    pygame.draw.rect(surface, base, rect, border_radius=3)
    for i in range(4, max(5, rect.height), 9):
        wave = int(math.sin(i * 0.7 + rect.width) * 3)
        color = color_with_light(base, 0.72 if i % 2 == 0 else 1.18)
        pygame.draw.line(surface, color, (rect.x, rect.y + i), (rect.right, rect.y + i + wave), 1)


def draw_window_weather(surface, rect, darkness):
    tick = pygame.time.get_ticks() / 1000
    cycle = tick % 64

    if cycle < 16:
        sky_top = (82, 152, 220)
        sky_bottom = (188, 220, 245)
        weather = "clear"
    elif cycle < 32:
        sky_top = (70, 82, 106)
        sky_bottom = (125, 138, 155)
        weather = "rain"
    elif cycle < 48:
        flash = 90 if int(tick * 3) % 9 == 0 else 0
        sky_top = (36 + flash, 38 + flash, 52 + flash)
        sky_bottom = (78 + flash, 80 + flash, 96 + flash)
        weather = "storm"
    else:
        sky_top = (26, 38, 82)
        sky_bottom = (210, 116, 76)
        weather = "evening"

    inside = rect.inflate(-8, -8)
    for y in range(inside.top, inside.bottom):
        ratio = (y - inside.top) / max(1, inside.height)
        col = (
            int((sky_top[0] * (1 - ratio) + sky_bottom[0] * ratio) * darkness),
            int((sky_top[1] * (1 - ratio) + sky_bottom[1] * ratio) * darkness),
            int((sky_top[2] * (1 - ratio) + sky_bottom[2] * ratio) * darkness),
        )
        pygame.draw.line(surface, col, (inside.left, y), (inside.right, y))

    if weather == "clear":
        sun_x = inside.left + int((math.sin(tick * 0.22) * 0.35 + 0.5) * inside.width)
        sun_y = inside.top + int(inside.height * 0.28)
        pygame.draw.circle(surface, color_with_light((255, 223, 118), darkness), (sun_x, sun_y), max(4, inside.width // 8))
        for cloud in range(2):
            cx = inside.left + int((tick * 9 + cloud * 70) % max(1, inside.width + 45)) - 22
            cy = inside.top + 12 + cloud * max(6, inside.height // 5)
            pygame.draw.ellipse(surface, color_with_light((238, 242, 236), darkness), (cx, cy, inside.width // 3, max(7, inside.height // 7)))
    elif weather in ("rain", "storm"):
        cloud_color = color_with_light((46, 48, 60), darkness)
        for cloud in range(3):
            cx = inside.left + cloud * max(18, inside.width // 3) - int((tick * 7) % 22)
            pygame.draw.ellipse(surface, cloud_color, (cx, inside.top + 7, max(20, inside.width // 2), max(10, inside.height // 5)))
        rain_color = color_with_light((185, 205, 235), darkness)
        for drop in range(18):
            x = inside.left + (drop * 17 + int(tick * 90)) % max(1, inside.width)
            y = inside.top + (drop * 23 + int(tick * 155)) % max(1, inside.height)
            pygame.draw.line(surface, rain_color, (x, y), (x - 4, y + 11), 1)
        if weather == "storm" and int(tick * 4) % 13 == 0:
            lx = inside.centerx
            lightning = [(lx, inside.top + 4), (lx - 8, inside.centery - 4), (lx + 2, inside.centery - 4), (lx - 10, inside.bottom - 4)]
            pygame.draw.lines(surface, color_with_light((255, 245, 170), darkness), False, lightning, 2)
    else:
        star_color = color_with_light((245, 238, 190), darkness)
        for star in range(11):
            x = inside.left + (star * 19 + 7) % max(1, inside.width)
            y = inside.top + (star * 13 + 5) % max(1, inside.height // 2)
            surface.set_at((x, y), star_color)

    frame_color = color_with_light((86, 62, 42), darkness)
    pygame.draw.rect(surface, frame_color, rect, 4, border_radius=2)
    pygame.draw.line(surface, frame_color, (rect.centerx, rect.top + 4), (rect.centerx, rect.bottom - 4), 3)
    pygame.draw.line(surface, frame_color, (rect.left + 4, rect.centery), (rect.right - 4, rect.centery), 3)
    pygame.draw.rect(surface, color_with_light((235, 230, 198), darkness), (rect.left - 4, rect.bottom - 3, rect.width + 8, 6))


def reset_cable_task():
    global cable_progress, selected_cable, cable_panel_open, cable_connected
    cable_progress = 0
    selected_cable = None
    cable_panel_open = False
    cable_connected = {"rouge": False, "jaune": False, "bleu": False}


def cable_panel_rects():
    panel = pygame.Rect(WIDTH // 2 - 430, HEIGHT // 2 - 300, 860, 600)
    close = pygame.Rect(panel.right - 64, panel.top + 24, 36, 36)
    left = {}
    right = {}
    left_order = ["rouge", "jaune", "bleu"]
    right_order = ["bleu", "rouge", "jaune"]

    for index, name in enumerate(left_order):
        y = panel.top + 180 + index * 120
        left[name] = pygame.Rect(panel.left + 100, y - 24, 50, 50)

    for index, name in enumerate(right_order):
        y = panel.top + 180 + index * 120
        right[name] = pygame.Rect(panel.right - 150, y - 24, 50, 50)

    return panel, close, left, right


def open_cable_panel():
    global cable_panel_open, selected_cable
    if power_fixed:
        return

    cable_panel_open = True
    selected_cable = None
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    pygame.mouse.get_rel()
    play_sound("click")


def close_cable_panel():
    global cable_panel_open, selected_cable
    cable_panel_open = False
    selected_cable = None
    if game_state == "playing" and not game_finished:
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()


def finish_cable_task():
    global power_fixed, cable_progress
    power_fixed = True
    cable_progress = 100
    close_cable_panel()
    show_message("Les 3 cables sont relies. Le courant revient, le monstre disparait.", 280)


def handle_cable_click(pos):
    global selected_cable, cable_progress
    panel, close, left, right = cable_panel_rects()

    if close.collidepoint(pos):
        close_cable_panel()
        return

    if not panel.collidepoint(pos):
        return

    for name, rect in left.items():
        if rect.collidepoint(pos) and not cable_connected[name]:
            selected_cable = name
            play_sound("click")
            return

    for name, rect in right.items():
        if rect.collidepoint(pos) and selected_cable:
            if name == selected_cable:
                cable_connected[name] = True
                selected_cable = None
                cable_progress = int(sum(cable_connected.values()) / 3 * 100)
                play_sound("electricite")
                if all(cable_connected.values()):
                    finish_cable_task()
            else:
                selected_cable = None
                show_message("Mauvaise prise. Relie chaque cable a la meme couleur.", 180)
                play_sound("click")
            return


def draw_cable_panel():
    panel, close, left, right = cable_panel_rects()
    mouse_pos = pygame.mouse.get_pos()

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 165))
    screen.blit(shade, (0, 0))

    pygame.draw.rect(screen, (28, 29, 31), panel, border_radius=12)
    pygame.draw.rect(screen, (190, 170, 104), panel, 4, border_radius=12)
    pygame.draw.rect(screen, (18, 18, 20), panel.inflate(-48, -120), border_radius=10)

    title = FONT.render("Boite electrique - relie les 3 cables", True, (245, 233, 190))
    screen.blit(title, (panel.left + 40, panel.top + 30))
    help_text = SMALL.render("Clique un cable a gauche, puis sa prise de meme couleur a droite. E ou X pour fermer.", True, (205, 205, 190))
    screen.blit(help_text, (panel.left + 40, panel.top + 80))

    pygame.draw.rect(screen, (75, 42, 42), close, border_radius=6)
    pygame.draw.rect(screen, (220, 180, 140), close, 3, border_radius=6)
    x_text = SMALL.render("X", True, (255, 235, 220))
    screen.blit(x_text, (close.centerx - x_text.get_width() // 2, close.centery - x_text.get_height() // 2))

    for name, rect in left.items():
        color = CABLE_COLORS[name]
        label = SMALL.render(name, True, (230, 230, 220))
        screen.blit(label, (rect.left - 8, rect.top - 32))
        pygame.draw.circle(screen, color, rect.center, 22)
        pygame.draw.circle(screen, (20, 20, 20), rect.center, 22, 4)
        if cable_connected[name]:
            pygame.draw.circle(screen, (120, 220, 120), rect.center, 10)
        elif selected_cable == name:
            pygame.draw.circle(screen, (255, 255, 230), rect.center, 28, 4)

    for name, rect in right.items():
        color = CABLE_COLORS[name]
        pygame.draw.rect(screen, (42, 43, 47), rect.inflate(24, 24), border_radius=8)
        pygame.draw.circle(screen, color, rect.center, 20)
        pygame.draw.circle(screen, (12, 12, 12), rect.center, 20, 4)
        label = SMALL.render("prise " + name, True, (230, 230, 220))
        screen.blit(label, (rect.right + 18, rect.centery - label.get_height() // 2))

    for name, done in cable_connected.items():
        if done:
            start = left[name].center
            end = right[name].center
            mid_x = (start[0] + end[0]) // 2
            points = [
                start,
                (mid_x - 80, start[1] + 30),
                (mid_x + 80, end[1] - 30),
                end,
            ]
            pygame.draw.lines(screen, CABLE_COLORS[name], False, points, 12)
            pygame.draw.lines(screen, (20, 20, 20), False, points, 3)

    if selected_cable:
        start = left[selected_cable].center
        pygame.draw.line(screen, CABLE_COLORS[selected_cable], start, mouse_pos, 10)
        pygame.draw.line(screen, (20, 20, 20), start, mouse_pos, 3)

    progress = sum(cable_connected.values())
    status = FONT.render(str(progress) + " / 3 cables relies", True, (245, 233, 190))
    screen.blit(status, (panel.centerx - status.get_width() // 2, panel.bottom - 70))


def add_item_to_inventory(item_name):
    for index, item in enumerate(inventory_slots):
        if item is None:
            inventory_slots[index] = item_name
            return True
    return False


def selected_item():
    return inventory_slots[selected_inventory]


def open_safe_panel():
    global safe_panel_open, safe_input
    if safe_unlocked:
        show_message("Le coffre est deja ouvert.", 160)
        return

    safe_panel_open = True
    safe_input = ""
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    pygame.mouse.get_rel()
    play_sound("click")


def close_safe_panel():
    global safe_panel_open, safe_input
    safe_panel_open = False
    safe_input = ""
    if game_state == "playing" and not game_finished:
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()


def unlock_safe():
    global safe_unlocked, safe_input
    safe_unlocked = True
    safe_input = ""
    close_safe_panel()
    if add_item_to_inventory("Clef"):
        show_message("Le coffre s'ouvre. Tu prends une clef.", 260)
        play_sound("clef")
    else:
        show_message("Inventaire plein. La clef reste dans le coffre.", 260)
        safe_unlocked = False


def handle_safe_key(event):
    global safe_input

    if event.key in (pygame.K_ESCAPE, pygame.K_e):
        close_safe_panel()
        return

    if event.key == pygame.K_BACKSPACE:
        safe_input = safe_input[:-1]
        play_sound("click")
        return

    if event.key == pygame.K_RETURN:
        if safe_input == safe_code:
            unlock_safe()
        else:
            safe_input = ""
            show_message("Code faux.", 150)
            play_sound("bang")
        return

    digit = None
    if pygame.K_0 <= event.key <= pygame.K_9:
        digit = str(event.key - pygame.K_0)
    elif pygame.K_KP0 <= event.key <= pygame.K_KP9:
        digit = str(event.key - pygame.K_KP0)

    if digit and len(safe_input) < len(safe_code):
        safe_input += digit
        play_sound("click")
        if len(safe_input) == len(safe_code):
            if safe_input == safe_code:
                unlock_safe()
            else:
                safe_input = ""
                show_message("Code faux.", 150)


def draw_safe_panel():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    screen.blit(shade, (0, 0))

    panel = pygame.Rect(WIDTH // 2 - 320, HEIGHT // 2 - 240, 640, 480)
    pygame.draw.rect(screen, (25, 27, 30), panel, border_radius=12)
    pygame.draw.rect(screen, (150, 150, 145), panel, 4, border_radius=12)

    title = FONT.render("Coffre fort", True, (235, 235, 220))
    screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 36))

    display = pygame.Rect(panel.centerx - 160, panel.top + 120, 320, 80)
    pygame.draw.rect(screen, (8, 12, 10), display, border_radius=8)
    pygame.draw.rect(screen, (80, 120, 85), display, 3, border_radius=8)
    shown = safe_input + "_" * (len(safe_code) - len(safe_input))
    code_text = BIG.render(shown, True, (120, 255, 150))
    screen.blit(code_text, (display.centerx - code_text.get_width() // 2, display.centery - code_text.get_height() // 2))

    help_text = SMALL.render("Tape le code puis Entree. E ou Echap pour fermer.", True, (210, 210, 200))
    screen.blit(help_text, (panel.centerx - help_text.get_width() // 2, panel.top + 240))

    for i in range(10):
        col = i % 5
        row = i // 5
        key_rect = pygame.Rect(panel.left + 100 + col * 90, panel.top + 290 + row * 64, 60, 48)
        pygame.draw.rect(screen, (48, 51, 56), key_rect, border_radius=6)
        pygame.draw.rect(screen, (120, 120, 118), key_rect, 2, border_radius=6)
        txt = SMALL.render(str(i), True, (240, 240, 230))
        screen.blit(txt, (key_rect.centerx - txt.get_width() // 2, key_rect.centery - txt.get_height() // 2))


def draw_sprite(obj_x, obj_y, color, size=1.0, label=None, shape="rect", depth_buffer=None):
    dx = obj_x - player_x
    dy = obj_y - player_y
    dist = math.sqrt(dx * dx + dy * dy)
    theta = math.atan2(dy, dx)
    delta = angle_diff(theta, player_a)

    if abs(delta) > FOV / 1.25 or dist < 0.2:
        return

    screen_x = WIDTH // 2 + int(math.tan(delta) * WIDTH)
    sprite_h = max(8, min(HEIGHT * 2, int(HEIGHT / dist * size)))
    sprite_w = max(8, min(WIDTH, sprite_h // 2))

    y = HEIGHT // 2 - sprite_h // 2 + look_pitch
    rect = pygame.Rect(screen_x - sprite_w // 2, y, sprite_w, sprite_h)

    darkness = 1.0
    if day == 4 and not power_fixed:
        darkness = 0.35

    c = (
        int(color[0] * darkness),
        int(color[1] * darkness),
        int(color[2] * darkness),
    )

    sprite = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

    if shape == "lamp":
        glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color_with_light((245, 214, 112), darkness), 45), (rect.width // 2, rect.height // 4), max(10, rect.width // 2))
        sprite.blit(glow, (0, 0))
        pygame.draw.rect(sprite, color_with_light((75, 58, 38), darkness), (rect.width // 2 - 3, rect.height // 2, 6, rect.height // 2))
        pygame.draw.polygon(sprite, c, [
            (rect.width // 2, 0),
            (2, rect.height // 3),
            (rect.width - 2, rect.height // 3),
        ])
        pygame.draw.line(sprite, color_with_light((92, 68, 35), darkness), (4, rect.height // 3), (rect.width - 4, rect.height // 3), 2)
    elif shape == "table":
        top = pygame.Rect(0, rect.height // 3, rect.width, max(5, rect.height // 4))
        draw_wood(sprite, top, c)
        pygame.draw.rect(sprite, color_with_light((62, 38, 23), darkness), (4, rect.height // 2, 5, rect.height // 3))
        pygame.draw.rect(sprite, color_with_light((62, 38, 23), darkness), (rect.width - 9, rect.height // 2, 5, rect.height // 3))
        pygame.draw.ellipse(sprite, color_with_light((226, 220, 204), darkness), (rect.width // 2 - rect.width // 6, top.y + 3, rect.width // 3, max(4, top.height // 2)))
    elif shape == "sofa":
        body = pygame.Rect(2, rect.height // 3, rect.width - 4, rect.height // 2)
        pygame.draw.rect(sprite, color_with_light((38, 48, 48), darkness), (6, rect.height - 8, rect.width - 12, 5))
        pygame.draw.rect(sprite, c, body, border_radius=8)
        pygame.draw.rect(sprite, color_with_light((65, 105, 102), darkness), (5, rect.height // 4, rect.width - 10, rect.height // 4), border_radius=6)
        pygame.draw.rect(sprite, color_with_light((72, 112, 110), darkness), (6, body.y + 5, rect.width // 2 - 8, body.height - 10), border_radius=5)
        pygame.draw.rect(sprite, color_with_light((78, 120, 117), darkness), (rect.width // 2 + 2, body.y + 5, rect.width // 2 - 8, body.height - 10), border_radius=5)
        pygame.draw.rect(sprite, color_with_light((45, 73, 72), darkness), (0, body.y + 6, 8, body.height - 2), border_radius=5)
        pygame.draw.rect(sprite, color_with_light((45, 73, 72), darkness), (rect.width - 8, body.y + 6, 8, body.height - 2), border_radius=5)
        pygame.draw.line(sprite, color_with_light((25, 45, 45), darkness), (rect.width // 2, body.y + 6), (rect.width // 2, body.bottom - 5), 1)
    elif shape == "dresser":
        draw_wood(sprite, pygame.Rect(3, 4, rect.width - 6, rect.height - 8), c)
        for drawer in range(3):
            y_drawer = 9 + drawer * max(5, (rect.height - 18) // 3)
            drawer_rect = pygame.Rect(8, y_drawer, rect.width - 16, max(4, (rect.height - 22) // 4))
            pygame.draw.rect(sprite, color_with_light((92, 56, 31), darkness), drawer_rect, border_radius=3)
            pygame.draw.circle(sprite, color_with_light((210, 180, 110), darkness), (rect.width // 2, drawer_rect.centery), 2)
        pygame.draw.rect(sprite, color_with_light((40, 28, 20), darkness), (3, 4, rect.width - 6, rect.height - 8), 2, border_radius=3)
    elif shape == "painting":
        frame = pygame.Rect(2, 2, rect.width - 4, rect.height - 4)
        pygame.draw.rect(sprite, color_with_light((74, 43, 24), darkness), frame, border_radius=3)
        inner = frame.inflate(-8, -8)
        pygame.draw.rect(sprite, color_with_light((224, 217, 188), darkness), inner)
        tick = pygame.time.get_ticks() / 1000
        wobble = int(math.sin(tick * 4 + obj_x) * max(1, rect.width // 16))
        pygame.draw.rect(sprite, color_with_light((34, 58, 92), darkness), (inner.x + 3 + wobble, inner.y + 4, inner.width // 2, inner.height // 3))
        pygame.draw.polygon(sprite, color_with_light((130, 94, 55), darkness), [
            (inner.x + 2, inner.bottom - 2),
            (inner.centerx, inner.y + inner.height // 3),
            (inner.right - 2, inner.bottom - 2),
        ])
        pygame.draw.circle(sprite, color_with_light((190, 54, 56), darkness), (inner.right - inner.width // 4, inner.y + inner.height // 3), max(2, inner.width // 8))
        pygame.draw.rect(sprite, color_with_light((32, 24, 22), darkness), frame, 2, border_radius=3)
        pygame.draw.line(sprite, color_with_light((40, 20, 24), darkness), (inner.left, inner.centery), (inner.right, inner.centery + wobble), 1)
    elif shape == "window":
        draw_window_weather(sprite, pygame.Rect(3, 3, rect.width - 6, rect.height - 6), darkness)
    elif shape == "safe":
        body = pygame.Rect(4, rect.height // 5, rect.width - 8, rect.height * 3 // 5)
        pygame.draw.rect(sprite, color_with_light((70, 76, 82), darkness), body, border_radius=5)
        pygame.draw.rect(sprite, color_with_light((150, 155, 160), darkness), body, 3, border_radius=5)
        door_rect = body.inflate(-8, -8)
        pygame.draw.rect(sprite, color_with_light((42, 47, 52), darkness), door_rect, border_radius=4)
        pygame.draw.circle(sprite, color_with_light((170, 175, 170), darkness), door_rect.center, max(5, rect.width // 10), 3)
        pygame.draw.circle(sprite, color_with_light((95, 100, 105), darkness), door_rect.center, max(2, rect.width // 24))
        light_color = (60, 210, 85) if safe_unlocked else (220, 60, 50)
        pygame.draw.circle(sprite, color_with_light(light_color, darkness), (door_rect.right - 10, door_rect.top + 10), max(2, rect.width // 22))
    elif shape == "cable_box":
        pygame.draw.rect(sprite, color_with_light((52, 56, 60), darkness), (3, 3, rect.width - 6, rect.height - 6), border_radius=5)
        pygame.draw.rect(sprite, color_with_light((135, 140, 135), darkness), (3, 3, rect.width - 6, rect.height - 6), 2, border_radius=5)
        pygame.draw.rect(sprite, color_with_light((22, 24, 26), darkness), (rect.width // 5, rect.height // 5, rect.width * 3 // 5, rect.height // 2), border_radius=3)
        for index, name in enumerate(["rouge", "jaune", "bleu"]):
            y_wire = rect.height // 4 + index * max(4, rect.height // 8)
            pygame.draw.line(sprite, color_with_light(CABLE_COLORS[name], darkness), (rect.width // 5, y_wire), (rect.width * 4 // 5, y_wire + 5), max(2, rect.width // 18))
        pygame.draw.circle(sprite, color_with_light((210, 40, 35), darkness), (rect.width // 4, rect.height - rect.height // 5), max(2, rect.width // 12))
        pygame.draw.circle(sprite, color_with_light((40, 160, 75), darkness if power_fixed else darkness * 0.35), (rect.width * 3 // 4, rect.height - rect.height // 5), max(2, rect.width // 12))
    elif shape == "door":
        pygame.draw.rect(sprite, c, (4, 0, rect.width - 8, rect.height))
        pygame.draw.rect(sprite, (38, 52, 66), (4, 0, rect.width - 8, rect.height), 3)
        pygame.draw.circle(sprite, (230, 210, 90), (rect.width - 14, rect.height // 2), 4)
    else:
        pygame.draw.rect(sprite, c, (0, 0, rect.width, rect.height))
        pygame.draw.rect(sprite, (35, 30, 25), (0, 0, rect.width, rect.height), 2)
        if shape == "bed":
            pygame.draw.rect(sprite, color_with_light((76, 55, 42), darkness), (0, rect.height // 3, rect.width, rect.height // 2), border_radius=5)
            pygame.draw.rect(sprite, c, (5, rect.height // 4, rect.width - 10, rect.height // 2), border_radius=5)
            pygame.draw.rect(sprite, color_with_light((235, 232, 218), darkness), (7, rect.height // 4 + 4, rect.width - 14, rect.height // 5), border_radius=4)
            pygame.draw.rect(sprite, color_with_light((80, 112, 158), darkness), (6, rect.height // 2, rect.width - 12, rect.height // 4), border_radius=4)
        if shape == "fridge":
            pygame.draw.rect(sprite, color_with_light((235, 238, 232), darkness), (2, 2, rect.width - 4, rect.height - 4), border_radius=4)
            pygame.draw.line(sprite, color_with_light((120, 130, 130), darkness), (2, rect.height // 2), (rect.width - 2, rect.height // 2), 2)
            pygame.draw.rect(sprite, color_with_light((115, 125, 126), darkness), (rect.width - 9, 10, 3, rect.height // 3), border_radius=2)
            pygame.draw.rect(sprite, color_with_light((115, 125, 126), darkness), (rect.width - 9, rect.height // 2 + 7, 3, rect.height // 3), border_radius=2)
            pygame.draw.rect(sprite, color_with_light((205, 70, 70), darkness), (8, rect.height // 2 + 8, 6, 5))
            pygame.draw.rect(sprite, color_with_light((70, 105, 190), darkness), (17, rect.height // 2 + 15, 5, 5))
        if shape == "soft_floor":
            sprite.fill((0, 0, 0, 0))
            pygame.draw.ellipse(sprite, color_with_light((38, 20, 16), darkness), (0, rect.height // 3, rect.width, rect.height // 2))
            pygame.draw.ellipse(sprite, color_with_light((12, 8, 7), darkness), (rect.width // 5, rect.height // 2 - 2, rect.width * 3 // 5, rect.height // 4))

    visible = draw_clipped_sprite(sprite, rect, dist, depth_buffer)
    center_visible = True
    if depth_buffer is not None and 0 <= rect.centerx < WIDTH:
        center_visible = dist <= depth_buffer[rect.centerx] + 0.18

    if visible and center_visible and label and dist < 3.4:
        txt = SMALL.render(label, True, (245, 245, 235))
        screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.y - 18))


def draw_objects(depth_buffer):
    if day != 5:
        draw_sprite(EXIT_X, EXIT_Y, (70, 115, 160), 0.95, "sortie", "door", depth_buffer)
    else:
        # Porte au fond du couloir : toujours visible, dorée quand ouverte
        if corridor_exit_open:
            draw_sprite(2.5, CORRIDOR_LENGTH - 1.5, (255, 220, 50), 1.3, "SORTIE - Entre vite !", "door", depth_buffer)
        else:
            draw_sprite(2.5, CORRIDOR_LENGTH - 1.5, (60, 55, 45), 1.1, "porte (verrouillee)", "door", depth_buffer)

    for window in windows:
        draw_sprite(window["x"], window["y"], (160, 200, 235), window["size"], None, "window", depth_buffer)

    for item in furniture:
        shape = "rect"
        if item["kind"] == "canape":
            shape = "sofa"
        elif item["kind"] == "lampe":
            shape = "lamp"
        elif item["kind"] == "table":
            shape = "table"
        elif item["kind"] == "lit":
            shape = "bed"
        elif item["kind"] == "frigo":
            shape = "fridge"
        elif item["kind"] == "commode":
            shape = "dresser"
        draw_sprite(item["x"], item["y"], item["color"], item["size"], None, shape, depth_buffer)

    if day == 2:
        for i, p in enumerate(paintings):
            if not p["gone"]:
                offset = math.sin(pygame.time.get_ticks() / 300 + i) * 0.15
                draw_sprite(p["x"] + offset, p["y"], (180, 55, 75), 0.75, "tableau", "painting", depth_buffer)

    if day == 3:
        label = "coffre ouvert" if safe_unlocked else "coffre fort"
        draw_sprite(SAFE_X, SAFE_Y, (80, 86, 92), 0.9, label, "safe", depth_buffer)

    if day == 4:
        draw_sprite(CABLE_X, CABLE_Y, (230, 190, 55), 0.9, "boite electrique", "cable_box", depth_buffer)
        if not power_fixed:
            draw_sprite(monster_x, monster_y, (10, 10, 12), 1.35, "???", "rect", depth_buffer)


def draw_crosshair():
    cx, cy = WIDTH // 2, int(HEIGHT // 2 + look_pitch)
    pygame.draw.line(screen, (230, 230, 220), (cx - 8, cy), (cx - 3, cy), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx + 3, cy), (cx + 8, cy), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx, cy - 8), (cx, cy - 3), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx, cy + 3), (cx, cy + 8), 1)


def draw_ceiling_code_hint():
    if day != 3:
        return

    if distance(player_x, player_y, 1.5, 9.5) > 2.2 or look_pitch < 165:
        return

    text = BIG.render("CODE " + safe_code, True, (65, 55, 38))
    shadow = BIG.render("CODE " + safe_code, True, (210, 200, 160))
    x = WIDTH // 2 - text.get_width() // 2
    y = 188
    screen.blit(shadow, (x + 2, y + 2))
    screen.blit(text, (x, y))


def draw_player_body(moving):
    tick = pygame.time.get_ticks() / 1000
    walk = math.sin(tick * (8.0 if moving else 2.0))
    bob = int(walk * (12 if moving else 3))
    light = 0.55 if day == 4 and not power_fixed else 1.0

    skin = color_with_light((214, 164, 118), light)
    skin_shadow = color_with_light((170, 112, 82), light)
    sleeve = color_with_light((48, 61, 78), light)
    shoe = color_with_light((32, 31, 34), light)
    sole = color_with_light((86, 83, 78), light)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    left_hand = (int(WIDTH * 0.27), HEIGHT - 122 + bob)
    right_hand = (int(WIDTH * 0.73), HEIGHT - 117 - bob)

    pygame.draw.polygon(overlay, (*sleeve, 245), [
        (left_hand[0] - 183, HEIGHT),
        (left_hand[0] - 90, HEIGHT - 63 + bob),
        (left_hand[0] - 31, HEIGHT - 21 + bob),
        (left_hand[0] - 61, HEIGHT),
    ])
    pygame.draw.polygon(overlay, (*sleeve, 245), [
        (right_hand[0] + 183, HEIGHT),
        (right_hand[0] + 90, HEIGHT - 63 - bob),
        (right_hand[0] + 31, HEIGHT - 21 - bob),
        (right_hand[0] + 61, HEIGHT),
    ])

    pygame.draw.ellipse(overlay, (*skin, 255), (left_hand[0] - 78, left_hand[1] - 49, 101, 70))
    pygame.draw.ellipse(overlay, (*skin_shadow, 210), (left_hand[0] - 42, left_hand[1] - 28, 52, 30))
    pygame.draw.ellipse(overlay, (*skin, 255), (right_hand[0] - 23, right_hand[1] - 49, 101, 70))
    pygame.draw.ellipse(overlay, (*skin_shadow, 210), (right_hand[0] - 2, right_hand[1] - 26, 52, 30))

    if selected_item() == "Clef":
        key_x = right_hand[0] + 24
        key_y = right_hand[1] - 31
        gold = color_with_light((230, 190, 70), light)
        pygame.draw.circle(overlay, (*gold, 255), (key_x, key_y), 14, 5)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 14, key_y), (key_x + 73, key_y + 3), 9)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 56, key_y + 3), (key_x + 56, key_y + 23), 7)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 71, key_y + 3), (key_x + 71, key_y + 17), 7)

    if look_pitch < -122:
        foot_alpha = max(0, min(235, int((-look_pitch - 122) * 1.26)))
        foot_y = HEIGHT - 216 + int(max(-88, look_pitch) * 0.18)
        spread = 101 + int(min(80, -look_pitch * 0.25))
        pygame.draw.polygon(overlay, (*sleeve, foot_alpha), [
            (WIDTH // 2 - spread - 38, HEIGHT),
            (WIDTH // 2 - spread + 35, foot_y + 108),
            (WIDTH // 2 - spread + 84, HEIGHT),
        ])
        pygame.draw.polygon(overlay, (*sleeve, foot_alpha), [
            (WIDTH // 2 + spread + 38, HEIGHT),
            (WIDTH // 2 + spread - 35, foot_y + 108),
            (WIDTH // 2 + spread - 84, HEIGHT),
        ])
        pygame.draw.ellipse(overlay, (*shoe, foot_alpha), (WIDTH // 2 - spread - 87, foot_y, 150, 80))
        pygame.draw.ellipse(overlay, (*shoe, foot_alpha), (WIDTH // 2 + spread - 63, foot_y, 150, 80))
        pygame.draw.rect(overlay, (*sole, foot_alpha), (WIDTH // 2 - spread - 63, foot_y + 56, 101, 12), border_radius=5)
        pygame.draw.rect(overlay, (*sole, foot_alpha), (WIDTH // 2 + spread - 38, foot_y + 56, 101, 12), border_radius=5)

    screen.blit(overlay, (0, 0))


def draw_health_bar():
    x, y = 240, 24
    bar_w, bar_h = 216, 28
    pygame.draw.rect(screen, (35, 12, 12), (x, y, bar_w, bar_h), border_radius=6)
    fill_w = int(bar_w * max(0, player_health) / MAX_HEALTH)
    pygame.draw.rect(screen, (190, 35, 35), (x, y, fill_w, bar_h), border_radius=6)
    pygame.draw.rect(screen, (235, 210, 185), (x, y, bar_w, bar_h), 3, border_radius=6)
    hp = SMALL.render("PV " + str(player_health) + "/" + str(MAX_HEALTH), True, (255, 235, 220))
    screen.blit(hp, (x + bar_w + 14, y - 1))


def draw_day_timer():
    remaining = max(0, int(math.ceil(day_timer)))
    color = (255, 235, 170) if remaining > 10 else (255, 90, 70)
    text = FONT.render("Temps : " + str(remaining) + "s", True, color)
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 21))


def draw_inventory_bar():
    slot_size = 90
    gap = 14
    total_w = slot_size * 4 + gap * 3
    x0 = WIDTH // 2 - total_w // 2
    y = HEIGHT - 112

    for index in range(4):
        rect = pygame.Rect(x0 + index * (slot_size + gap), y, slot_size, slot_size)
        selected = index == selected_inventory
        base = (26, 27, 30) if not selected else (58, 52, 34)
        border = (120, 112, 86) if not selected else (245, 210, 90)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 3 if selected else 2, border_radius=6)

        num = SMALL.render(str(index + 1), True, (180, 175, 150))
        screen.blit(num, (rect.x + 5, rect.y + 3))

        item = inventory_slots[index]
        if item:
            name = SMALL.render(item, True, (235, 232, 210))
            screen.blit(name, (rect.centerx - name.get_width() // 2, rect.centery - name.get_height() // 2))
        else:
            empty = SMALL.render("Vide", True, (110, 110, 110))
            screen.blit(empty, (rect.centerx - empty.get_width() // 2, rect.centery - empty.get_height() // 2))


def draw_ui():
    global message_timer

    pygame.draw.rect(screen, (0, 0, 0), (0, 0, WIDTH, 130))
    title = FONT.render("Jour " + str(day) + " / 5", True, (255, 235, 170))
    screen.blit(title, (30, 21))
    draw_health_bar()
    draw_day_timer()

    if day == 1:
        obj = "Objectif : attends le bruit bizarre puis sors de l'appartement."
    elif day == 2:
        left = sum(1 for p in paintings if not p["gone"])
        obj = "Objectif : jette les tableaux qui bougent. Restants : " + str(left)
    elif day == 3:
        obj = "Objectif : code au plafond du spawn, coffre au fond, clef en main puis clic droit porte."
    elif day == 4:
        obj = "Objectif : repare les cables dans le couloir. Ne laisse pas le monstre approcher."
    else:
        obj = "Objectif : cours jusqu'au fond du couloir. La porte s'ouvre dans les 10 dernieres secondes !"

    objective = SMALL.render(obj, True, (220, 220, 220))
    screen.blit(objective, (30, 75))

    controls = SMALL.render("Souris | ZQSD/WASD | Molette inv. | E | ESPACE | ESC", True, (185, 185, 185))
    screen.blit(controls, (WIDTH - controls.get_width() - 30, 31))

    if message_timer > 0:
        box = pygame.Rect(30, HEIGHT - 240, WIDTH - 60, 90)
        pygame.draw.rect(screen, (0, 0, 0), box)
        pygame.draw.rect(screen, (180, 160, 110), box, 3)
        txt = FONT.render(message, True, (255, 245, 210))
        screen.blit(txt, (box.x + 24, box.y + 22))
        message_timer -= 1

    if stuck:
        txt = BIG.render("TU T'ENFONCES ! APPUIE SUR ESPACE", True, (255, 80, 80))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 200))
        bar_w = 600
        pygame.draw.rect(screen, (50, 50, 50), (WIDTH // 2 - bar_w // 2, HEIGHT // 2 - 100, bar_w, 34))
        pygame.draw.rect(screen, (255, 70, 70), (WIDTH // 2 - bar_w // 2, HEIGHT // 2 - 100, int(bar_w * stuck_clicks / 18), 34))

    if day == 4 and not power_fixed:
        alpha = max(40, min(180, int(220 - heartbeat * 40)))
        red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        red.fill((80, 0, 0, alpha // 3))
        screen.blit(red, (0, 0))

        if distance(player_x, player_y, CABLE_X, CABLE_Y) < 1.6:
            bar_w = 520
            pygame.draw.rect(screen, (30, 30, 30), (WIDTH // 2 - bar_w // 2, HEIGHT - 220, bar_w, 30))
            pygame.draw.rect(screen, (240, 200, 70), (WIDTH // 2 - bar_w // 2, HEIGHT - 220, int(bar_w * cable_progress / 100), 30))
            t = SMALL.render("Appuie sur E pour ouvrir la boite et relier rouge, jaune et bleu", True, (255, 240, 190))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT - 260))

    draw_inventory_bar()


def interact():
    if day == 2:
        for p in paintings:
            if not p["gone"] and distance(player_x, player_y, p["x"], p["y"]) < 1.25:
                p["gone"] = True
                remaining = sum(1 for item in paintings if not item["gone"])
                if remaining == 0:
                    show_message("Tous les tableaux sont jetes. Va a la porte de sortie pour aller au travail.", 300)
                else:
                    show_message("Tu jettes le tableau. Il en reste " + str(remaining) + ".")
                play_sound("interact")
                return

    if day == 4:
        if distance(player_x, player_y, CABLE_X, CABLE_Y) < 1.6 and not power_fixed:
            open_cable_panel()

    if day == 3:
        if distance(player_x, player_y, SAFE_X, SAFE_Y) < 1.6:
            open_safe_panel()


def use_selected_item():
    if day == 3 and near_exit():
        if selected_item() == "Clef":
            show_message("Tu ouvres la porte avec la clef.", 180)
            next_day()
        else:
            show_message("La porte est verrouillee. Selectionne la clef et fais clic droit.", 220)


def next_day():
    global day, player_x, player_y, player_a, look_pitch
    global stuck, stuck_clicks, sand_damage_timer, day_timer
    global cable_progress, power_fixed, monster_x, monster_y
    global ending_timer, game_finished

    play_sound("door")
    day += 1
    day_timer = DAY_LIMIT
    if day == 5:
        player_x = 2.5
        player_y = 1.5
        player_a = math.pi / 2
    else:
        player_x = 1.5
        player_y = 9.5
        player_a = 0.0
    look_pitch = 0
    stuck = False
    stuck_clicks = 0
    sand_damage_timer = 0.0

    if day == 2:
        show_message("Jour 2 : les tableaux ont change de place. Jette-les avant de sortir.", 300)
    elif day == 3:
        show_message("Jour 3 : trouve le code au plafond, ouvre le coffre, prends la clef.", 320)
    elif day == 4:
        reset_cable_task()
        power_fixed = False
        monster_x = 12.5
        monster_y = 1.5
        show_message("Jour 4 : coupure de courant. Trouve la boite electrique loin de la sortie.", 300)
    elif day == 5:
        ending_timer = 0
        show_message("Jour 5 : cours jusqu'au fond du long couloir avant la fin du chrono.", 320)
    else:
        game_finished = True


def check_exit():
    global game_finished

    if not near_exit():
        return

    if day == 1:
        if j1_event_done:
            next_day()
        else:
            show_message("Quelque chose te retient. Attends...")
    elif day == 2:
        if all(p["gone"] for p in paintings):
            next_day()
        else:
            show_message("Impossible de partir : les tableaux bougent encore.")
    elif day == 3:
        if not stuck:
            show_message("Porte verrouillee. Trouve la clef, selectionne-la, puis clic droit.", 220)
    elif day == 4:
        if power_fixed:
            next_day()
        else:
            show_message("Il faut reparer le courant avant de partir.")
    elif day == 5:
        # La fin se gere dans update_day_events via la porte dynamique
        pass


def update_day_events(dt):
    global j1_timer, j1_event_done, shake, day_timer
    global stuck, stuck_clicks, sand_damage_timer, player_health
    global monster_x, monster_y, heartbeat, game_finished, ending_timer
    global corridor_exit_open, ending_cinematic

    if not ending_cinematic:
        day_timer -= dt
    if day_timer <= 0 and not ending_cinematic:
        kill_player("Le temps est ecoule. Tu recommences depuis le debut.")
        return

    if day == 1:
        if not j1_event_done:
            j1_timer -= dt
            if j1_timer <= 0:
                j1_event_done = True
                shake = 22
                show_message("BANG ! Un bruit soudain et impossible vient du plafond. Sors vite !", 320)
                play_sound("bang")

    if day == 3 and not stuck:
        for s in sink_spots:
            if not s["used"] and distance(player_x, player_y, s["x"], s["y"]) < 0.65:
                stuck = True
                stuck_clicks = 0
                sand_damage_timer = 0.0
                s["used"] = True
                show_message("Le sable mou t'aspire ! Appuie vite sur ESPACE !", 260)

    if day == 3 and stuck:
        sand_damage_timer += dt
        if sand_damage_timer >= 2.0:
            sand_damage_timer -= 2.0
            player_health -= 1
            show_message("Le sable mou t'etouffe. -1 PV", 150)
            if player_health <= 0:
                kill_player("Tu es reste trop longtemps dans le sable mou.")
                return

    if day == 4 and not power_fixed:
        dx = player_x - monster_x
        dy = player_y - monster_y
        dist = math.sqrt(dx * dx + dy * dy)
        monster_angle = math.atan2(monster_y - player_y, monster_x - player_x)
        seen = abs(angle_diff(monster_angle, player_a)) < FOV / 2.2 and dist < 9

        if dist > 0.2:
            if seen:
                monster_x -= dx / dist * 0.022
                monster_y -= dy / dist * 0.022
            else:
                monster_x += dx / dist * 0.010
                monster_y += dy / dist * 0.010

        if wall_at(monster_x, monster_y):
            monster_x = max(1.5, min(MAP_W - 2, monster_x))
            monster_y = max(1.5, min(MAP_H - 2, monster_y))

        heartbeat = max(0, 6 - dist)

        if dist < 0.55:
            show_message("Le monstre t'a touche. Tu te reveilles au debut du jour 4.", 300)
            if cable_panel_open:
                close_cable_panel()
            reset_cable_task()
            monster_x = 12.5
            monster_y = 1.5

    if day == 5 and is_exit(player_x, player_y):
        game_finished = True

    # Jour 5 : ouvrir la porte de sortie 10s avant la fin
    if day == 5 and not corridor_exit_open and day_timer <= 10.0:
        corridor_exit_open = True
        show_message("Une porte de sortie apparait au fond ! Cours !", 300)
        shake = 18

    # Verifier si le joueur entre dans la porte de fin de couloir
    if day == 5 and corridor_exit_open and not ending_cinematic:
        door_dist = distance(player_x, player_y, 2.5, CORRIDOR_LENGTH - 1.5)
        if door_dist < 1.2:
            ending_cinematic = True
            ending_timer = 0.0
            game_finished = True
            play_sound("door")


def draw_ending():
    t = pygame.time.get_ticks() / 1000
    screen.fill((190, 170, 70))

    for x in range(0, WIDTH, 80):
        pygame.draw.line(screen, (160, 145, 55), (x, 0), (x + math.sin(t + x) * 20, HEIGHT), 2)

    for y in range(0, HEIGHT, 70):
        pygame.draw.line(screen, (210, 190, 90), (0, y), (WIDTH, y + math.cos(t + y) * 15), 2)

    fade = min(255, int(ending_timer * 50))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, max(0, 180 - fade // 2)))
    screen.blit(overlay, (0, 0))

    if ending_timer < 2:
        text = "..."
    elif ending_timer < 4:
        text = "Tu ouvres les yeux."
    elif ending_timer < 6:
        text = "L'appartement n'est plus la."
    elif ending_timer < 8:
        text = "Bienvenue dans les Backrooms."
    else:
        text = "FIN"

    txt = BIG.render(text, True, (30, 25, 10))
    screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 40))


def draw_game_over():
    if ending_cinematic:
        draw_ending()
        return
    screen.fill((10, 10, 12))
    t1 = BIG.render("FIN", True, (255, 230, 120))
    t2 = FONT.render("Tu as survecu aux 5 jours... ou presque.", True, (230, 230, 230))
    t3 = SMALL.render("Appuie sur ESC pour quitter.", True, (180, 180, 180))

    screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, HEIGHT // 2 - 140))
    screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 - 35))
    screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, HEIGHT // 2 + 44))


def draw_death_screen():
    screen.fill((18, 5, 7))
    pulse = int((math.sin(pygame.time.get_ticks() / 220) + 1) * 25)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((120 + pulse, 0, 0, 55))
    screen.blit(overlay, (0, 0))

    title = BIG.render("TU ES MORT", True, (255, 70, 70))
    reason = FONT.render(death_message, True, (235, 215, 205))
    restart = FONT.render("Appuie sur ESPACE ou clique pour recommencer au debut.", True, (255, 235, 190))
    hp = SMALL.render("PV : 0 / " + str(MAX_HEALTH), True, (210, 160, 150))

    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 166))
    screen.blit(reason, (WIDTH // 2 - reason.get_width() // 2, HEIGHT // 2 - 56))
    screen.blit(hp, (WIDTH // 2 - hp.get_width() // 2, HEIGHT // 2 + 14))
    screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 101))


def draw_loading_screen():
    progress = min(1.0, loading_timer / LOADING_DURATION)
    messages = [
        "Compilation des fichiers",
        "Generation du terrain",
        "Verification des anomalies",
        "Chargement des sons",
        "Ouverture des Backrooms",
    ]
    index = min(len(messages) - 1, int(progress * len(messages)))

    screen.fill((9, 9, 11))
    for y in range(0, HEIGHT, 42):
        shade = 16 + (y // 42) % 2 * 10
        pygame.draw.rect(screen, (shade, shade, shade + 2), (0, y, WIDTH, 42))

    title = BIG.render("INITIALISATION", True, (245, 225, 150))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 261))

    bar = pygame.Rect(WIDTH // 2 - 400, HEIGHT // 2 - 30, 800, 60)
    pygame.draw.rect(screen, (28, 29, 31), bar, border_radius=10)
    pygame.draw.rect(screen, (170, 150, 85), bar, 3, border_radius=10)
    fill = bar.inflate(-12, -12)
    fill.width = int((bar.width - 24) * progress)
    pygame.draw.rect(screen, (218, 186, 82), fill, border_radius=8)

    pct = FONT.render(str(int(progress * 100)) + "%", True, (235, 230, 205))
    screen.blit(pct, (WIDTH // 2 - pct.get_width() // 2, bar.bottom + 30))

    text = FONT.render(messages[index] + "...", True, (210, 210, 195))
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, bar.bottom + 90))
    skip = SMALL.render("ESPACE pour passer", True, (100, 100, 100))
    screen.blit(skip, (WIDTH - skip.get_width() - 20, HEIGHT - 30))


def draw_intro_cinematic():
    t = intro_timer
    screen.fill((178, 164, 82))
    horizon = HEIGHT // 2 - 25

    for y in range(0, horizon):
        ratio = y / max(1, horizon)
        color = (155 + int(ratio * 30), 145 + int(ratio * 22), 72)
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))

    pygame.draw.rect(screen, (125, 111, 55), (0, horizon, WIDTH, HEIGHT - horizon))

    speed = t * 80
    for i in range(24):
        z = ((i * 80 - speed) % 900) + 70
        scale = 420 / z
        y = horizon + int(scale * 180)
        half = int(scale * 370)
        x1 = WIDTH // 2 - half
        x2 = WIDTH // 2 + half
        pygame.draw.line(screen, (95, 84, 42), (x1, y), (x2, y), 2)
        pygame.draw.line(screen, (205, 186, 90), (x1, y), (0, HEIGHT), 1)
        pygame.draw.line(screen, (205, 186, 90), (x2, y), (WIDTH, HEIGHT), 1)

    for x in range(-120, WIDTH + 160, 120):
        shift = int((t * 45) % 120)
        pygame.draw.rect(screen, (145, 132, 63), (x - shift, 0, 64, horizon))
        pygame.draw.rect(screen, (94, 86, 42), (x - shift, 0, 64, horizon), 2)

    fade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fade.fill((0, 0, 0, 65))
    screen.blit(fade, (0, 0))

    if t < 3.2:
        line1 = "Bienvenue dans les Backrooms."
        line2 = ""
    elif t < 7.4:
        line1 = "Pour survivre, tu devras accomplir des taches."
        line2 = "Mais tu n'as que 3 jours."
    else:
        line1 = "Voyons si tu es digne"
        line2 = "de sauver le monde."

    text1 = BIG.render(line1, True, (255, 242, 170))
    screen.blit(text1, (WIDTH // 2 - text1.get_width() // 2, HEIGHT // 2 - 66))
    if line2:
        text2 = FONT.render(line2, True, (238, 232, 205))
        screen.blit(text2, (WIDTH // 2 - text2.get_width() // 2, HEIGHT // 2 - 10))

    skip = SMALL.render("ESPACE pour passer", True, (215, 210, 185))
    screen.blit(skip, (WIDTH - skip.get_width() - 18, HEIGHT - 34))


def menu_rects():
    center_x = WIDTH // 2
    return {
        "play": pygame.Rect(center_x - 165, 444, 330, 94),
        "sound": pygame.Rect(center_x - 165, 572, 330, 84),
        "vol_down": pygame.Rect(center_x - 165, 686, 82, 80),
        "vol_up": pygame.Rect(center_x + 83, 686, 82, 80),
        "quit": pygame.Rect(center_x - 165, 815, 330, 84),
    }


def draw_button(rect, text, mouse_pos, main=False):
    hover = rect.collidepoint(mouse_pos)
    if main:
        base = (186, 150, 78) if not hover else (218, 178, 92)
        border = (255, 232, 150)
        text_color = (20, 18, 12)
    else:
        base = (30, 31, 34) if not hover else (48, 50, 54)
        border = (132, 118, 78)
        text_color = (238, 234, 215)

    pygame.draw.rect(screen, base, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    label = FONT.render(text, True, text_color)
    screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))


def draw_menu():
    mouse_pos = pygame.mouse.get_pos()
    screen.fill((20, 19, 17))

    for y in range(0, HEIGHT, 58):
        color = (35, 32, 25) if (y // 58) % 2 == 0 else (28, 27, 23)
        pygame.draw.rect(screen, color, (0, y, WIDTH, 58))

    for x in range(0, WIDTH, 90):
        pygame.draw.line(screen, (62, 48, 30), (x, HEIGHT), (x + 140, 0), 1)

    title = BIG.render("AVANT BACKROOM", True, (245, 222, 142))
    subtitle = FONT.render("Appartement anormal - 5 jours", True, (230, 226, 210))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 167))
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 268))

    rects = menu_rects()
    draw_button(rects["play"], "Lancer la partie", mouse_pos, True)

    sound_text = "Son : active" if sound_enabled else "Son : coupe"
    if not sound_available:
        sound_text = "Son : indisponible"
    draw_button(rects["sound"], sound_text, mouse_pos)

    draw_button(rects["vol_down"], "-", mouse_pos)
    draw_button(rects["vol_up"], "+", mouse_pos)

    vol_box = pygame.Rect(WIDTH // 2 - 70, 686, 140, 80)
    pygame.draw.rect(screen, (12, 12, 13), vol_box, border_radius=8)
    pygame.draw.rect(screen, (132, 118, 78), vol_box, 2, border_radius=8)
    vol = FONT.render("Volume " + str(int(sound_volume * 100)) + "%", True, (238, 234, 215))
    screen.blit(vol, (vol_box.centerx - vol.get_width() // 2, vol_box.centery - vol.get_height() // 2))

    draw_button(rects["quit"], "Quitter", mouse_pos)

    hint = SMALL.render("Clique sur Lancer la partie. La souris servira ensuite a regarder.", True, (190, 185, 165))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 52))


def start_game(reset=True):
    global game_state
    if reset:
        reset_game()
    game_state = "playing"
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
    play_sound("click")


def start_intro():
    global game_state, intro_timer
    reset_game()
    intro_timer = 0.0
    game_state = "intro"
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
    play_sound("click")


def handle_menu_click(pos):
    global sound_enabled, sound_volume

    rects = menu_rects()
    if rects["play"].collidepoint(pos):
        start_intro()
        return False

    if rects["sound"].collidepoint(pos):
        sound_enabled = not sound_enabled
        play_sound("click")
        return False

    if rects["vol_down"].collidepoint(pos):
        sound_volume = max(0.0, round(sound_volume - 0.1, 1))
        play_sound("click")
        return False

    if rects["vol_up"].collidepoint(pos):
        sound_volume = min(1.0, round(sound_volume + 0.1, 1))
        play_sound("click")
        return False

    if rects["quit"].collidepoint(pos):
        return True

    return False


load_sounds()

running = True

while running:
    dt = clock.tick(60) / 1000
    moving_now = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == "menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if handle_menu_click(event.pos):
                    running = False

        elif game_state == "loading":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                game_state = "menu"

        elif game_state == "intro":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game(reset=False)

        elif game_state == "dead":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                start_game()

        elif game_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and cable_panel_open:
                handle_cable_click(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and not cable_panel_open and not safe_panel_open:
                use_selected_item()

            if event.type == pygame.MOUSEWHEEL and not cable_panel_open and not safe_panel_open:
                selected_inventory = (selected_inventory - event.y) % len(inventory_slots)
                play_sound("click")

            if event.type == pygame.MOUSEMOTION and not game_finished and not cable_panel_open and not safe_panel_open:
                player_a += event.rel[0] * MOUSE_SENSITIVITY
                look_pitch -= event.rel[1] * 1.1
                look_pitch = int(max(-PITCH_LIMIT, min(PITCH_LIMIT, look_pitch)))

            if event.type == pygame.KEYDOWN:
                if safe_panel_open:
                    handle_safe_key(event)
                    continue

                if event.key == pygame.K_ESCAPE:
                    if cable_panel_open:
                        close_cable_panel()
                    elif safe_panel_open:
                        close_safe_panel()
                    else:
                        running = False

                if event.key == pygame.K_e and cable_panel_open:
                    close_cable_panel()
                    continue

                if event.key == pygame.K_SPACE and stuck:
                    stuck_clicks += 1
                    if stuck_clicks >= 18:
                        stuck = False
                        stuck_clicks = 0
                        sand_damage_timer = 0.0
                        show_message("Tu t'arraches du sol. Ne reste pas ici.", 240)

                if event.key == pygame.K_e and not cable_panel_open and not safe_panel_open:
                    interact()

    if game_state == "loading":
        loading_timer += dt
        if loading_timer >= LOADING_DURATION:
            game_state = "menu"
        draw_loading_screen()
        pygame.display.flip()
        continue

    if game_state == "intro":
        intro_timer += dt
        if intro_timer >= INTRO_DURATION:
            start_game(reset=False)
        draw_intro_cinematic()
        pygame.display.flip()
        continue

    if game_state == "menu":
        draw_menu()
        pygame.display.flip()
        continue

    if game_state == "dead":
        draw_death_screen()
        pygame.display.flip()
        continue

    keys = pygame.key.get_pressed()

    if not game_finished:
        speed = 0.085 if day == 5 else 0.050

        if not stuck and not cable_panel_open and not safe_panel_open:
            forward = keys[pygame.K_w] or keys[pygame.K_z]
            backward = keys[pygame.K_s]
            left = keys[pygame.K_a] or keys[pygame.K_q]
            right = keys[pygame.K_d]
            moving_now = forward or backward or left or right

            if forward:
                try_move(math.cos(player_a) * speed, math.sin(player_a) * speed)
            if backward:
                try_move(-math.cos(player_a) * speed, -math.sin(player_a) * speed)
            if left:
                try_move(math.sin(player_a) * speed, -math.cos(player_a) * speed)
            if right:
                try_move(-math.sin(player_a) * speed, math.cos(player_a) * speed)

        update_footsteps(moving_now)
        check_exit()

    update_day_events(dt)

    if game_state == "dead":
        draw_death_screen()
        pygame.display.flip()
        continue

    if game_finished:
        if ending_cinematic:
            ending_timer += dt
        update_footsteps(False)
        draw_game_over()
    else:
        draw_floor_ceiling()
        depth_buffer = cast_rays()
        draw_objects(depth_buffer)
        draw_player_body(moving_now)
        draw_ceiling_code_hint()
        draw_crosshair()

        if shake > 0:
            shake -= 1
            offset_x = random.randint(-shake, shake)
            offset_y = random.randint(-shake, shake)
            copy = screen.copy()
            screen.fill((0, 0, 0))
            screen.blit(copy, (offset_x, offset_y))

        draw_ui()
        if cable_panel_open:
            draw_cable_panel()
        if safe_panel_open:
            draw_safe_panel()

    pygame.display.flip()

pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
sys.exit()