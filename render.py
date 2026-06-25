import math
import os
import numpy as np
import pygame
import pygame.surfarray as surfarray
from config import WIDTH, HEIGHT, FOV, RAYS, MAX_DEPTH, EXIT_X, EXIT_Y, CABLE_X, CABLE_Y, SAFE_X, SAFE_Y, CABLE_COLORS, CORRIDOR_LENGTH, TILE_SCALE
import state
import sounds
import game

TEX_COLS = None
TEX_SURF = None
MONSTER_FRAMES = None
MONSTER_FW = 48
MONSTER_FH = 64
TEX_W = 32
TEX_H = 32
TEX_INDICES = {}

_COS_OFF = None
_SIN_OFF = None
_BODY_OVERLAY = None
_SHADE_PANEL = None
_PAUSE_BG = None


def load_textures():
    global TEX_COLS, TEX_SURF, TEX_W, TEX_H, _COS_OFF, _SIN_OFF, MONSTER_FRAMES
    tex_dir = os.path.join(os.path.dirname(__file__), "assets", "textures")
    path = os.path.join(tex_dir, "Wall-Texture.png")
    try:
        tex = pygame.image.load(path).convert()
        TEX_SURF = tex
        TEX_W, TEX_H = tex.get_width(), tex.get_height()
        arr = surfarray.array3d(tex).astype(np.uint16)
        TEX_COLS = [arr[:, i, :].copy() for i in range(TEX_W)]
        for h in range(1, HEIGHT * 2 + 1):
            TEX_INDICES[h] = np.linspace(0, TEX_H - 1, h, dtype=np.uint16)
    except Exception:
        print("Warning: Could not load wall texture, using fallback")
        TEX_W, TEX_H = 32, 32
        tex = pygame.Surface((32, 32))
        tex.fill((180, 150, 80))
        TEX_SURF = tex
        arr = surfarray.array3d(tex).astype(np.uint16)
        TEX_COLS = [arr[:, i, :].copy() for i in range(TEX_W)]
        for h in range(1, HEIGHT * 2 + 1):
            TEX_INDICES[h] = np.linspace(0, TEX_H - 1, h, dtype=np.uint16)

    off = np.arange(WIDTH, dtype=np.float32) / WIDTH * FOV - FOV / 2
    _COS_OFF = np.cos(off)
    _SIN_OFF = np.sin(off)

    try:
        mon_path = os.path.join(tex_dir, "Monster-Spritesheet.png")
        mon_surf = pygame.image.load(mon_path).convert_alpha()
        mw, mh = mon_surf.get_width(), mon_surf.get_height()
        nframes = mw // MONSTER_FW
        MONSTER_FRAMES = []
        for i in range(nframes):
            frame = mon_surf.subsurface((i * MONSTER_FW, 0, MONSTER_FW, MONSTER_FH))
            MONSTER_FRAMES.append(frame)
    except Exception:
        MONSTER_FRAMES = None


def draw_floor_ceiling():
    from config import screen
    horizon = int(HEIGHT // 2 + state.look_pitch)

    floor_base = (200, 180, 110)
    if state.day == 4 and not state.power_fixed:
        floor_base = (50, 45, 28)

    screen.fill(floor_base, (0, horizon, WIDTH, HEIGHT - horizon))

    ceil_h = max(0, horizon)
    if ceil_h > 0:
        ceil_color = (25, 22, 15) if state.day == 4 and not state.power_fixed else (185, 175, 130)
        screen.fill(ceil_color, (0, 0, WIDTH, ceil_h))


def cast_rays():
    from config import screen
    start_angle = state.player_a - FOV / 2
    depth_buffer = [MAX_DEPTH] * WIDTH

    arr = surfarray.pixels3d(screen)
    cols = TEX_COLS

    for ray in range(RAYS):
        ray_angle = start_angle + ray / RAYS * FOV
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 0.02
        hit_x = state.player_x
        hit_y = state.player_y

        while depth < MAX_DEPTH:
            hit_x = state.player_x + cos_a * depth
            hit_y = state.player_y + sin_a * depth

            if game.wall_at(hit_x, hit_y):
                break

            depth += 0.025

        depth *= math.cos(state.player_a - ray_angle)
        wall_h = min(HEIGHT * 2, int(HEIGHT / (depth + 0.0001)))

        fx = hit_x - int(hit_x)
        fy = hit_y - int(hit_y)
        vertical_hit = fx < 0.04 or fx > 0.96

        x_screen = int(ray * WIDTH / RAYS)
        w = int(WIDTH / RAYS) + 1
        x_end = min(WIDTH, x_screen + w)
        y1 = HEIGHT // 2 - wall_h // 2 + state.look_pitch
        y2 = y1 + wall_h

        for sx in range(max(0, x_screen), x_end):
            depth_buffer[sx] = depth

        shade = max(0.12, 1.0 - depth / MAX_DEPTH * 0.92)
        if state.day == 4 and not state.power_fixed:
            shade *= 0.25
        if not vertical_hit:
            shade *= 0.75

        if cols is not None:
            tex_x = int(((fy if vertical_hit else fx) * TILE_SCALE % 1.0) * (TEX_W - 1))
            tex_x = max(0, min(TEX_W - 1, tex_x))

            y_start = y1 if y1 > 0 else 0
            y_end = y2 if y2 < HEIGHT else HEIGHT
            draw_h = y_end - y_start
            if draw_h > 0:
                lo = y_start - y1
                hi = lo + draw_h
                idx = TEX_INDICES[wall_h][lo:hi]
                out = np.take(cols[tex_x], idx, axis=0)
                if shade < 0.99:
                    out = (out * shade).astype(np.uint8)
                else:
                    out = out.astype(np.uint8)
                arr[x_screen:x_end, y_start:y_end, :] = out[np.newaxis, :, :]
        else:
            base = [180, 155, 100]
            if not vertical_hit:
                base = [int(c * 0.82) for c in base]
            c = (int(base[0] * shade), int(base[1] * shade), int(base[2] * shade))
            pygame.draw.rect(screen, c, (x_screen, y1, w, wall_h))

        baseboard_h = max(2, min(12, wall_h // 13))
        base_y = min(HEIGHT, y2 - baseboard_h)
        pygame.draw.rect(screen, (214, 207, 178), (x_screen, base_y, w, baseboard_h))

    return depth_buffer


def draw_clipped_sprite(sprite, rect, dist, depth_buffer):
    from config import screen
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


def draw_sprite(obj_x, obj_y, color, size=1.0, label=None, shape="rect", depth_buffer=None):
    from config import screen
    dx = obj_x - state.player_x
    dy = obj_y - state.player_y
    dist = math.sqrt(dx * dx + dy * dy)
    theta = math.atan2(dy, dx)
    delta = game.angle_diff(theta, state.player_a)

    if abs(delta) > FOV / 1.25 or dist < 0.2:
        return

    screen_x = WIDTH // 2 + int(math.tan(delta) * WIDTH)
    sprite_h = max(8, min(HEIGHT * 2, int(HEIGHT / dist * size)))
    sprite_w = max(8, min(WIDTH, sprite_h // 2))

    y = HEIGHT // 2 - sprite_h // 2 + state.look_pitch
    rect = pygame.Rect(screen_x - sprite_w // 2, y, sprite_w, sprite_h)

    darkness = 1.0
    if state.day == 4 and not state.power_fixed:
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
        light_color = (60, 210, 85) if state.safe_unlocked else (220, 60, 50)
        pygame.draw.circle(sprite, color_with_light(light_color, darkness), (door_rect.right - 10, door_rect.top + 10), max(2, rect.width // 22))
    elif shape == "cable_box":
        pygame.draw.rect(sprite, color_with_light((52, 56, 60), darkness), (3, 3, rect.width - 6, rect.height - 6), border_radius=5)
        pygame.draw.rect(sprite, color_with_light((135, 140, 135), darkness), (3, 3, rect.width - 6, rect.height - 6), 2, border_radius=5)
        pygame.draw.rect(sprite, color_with_light((22, 24, 26), darkness), (rect.width // 5, rect.height // 5, rect.width * 3 // 5, rect.height // 2), border_radius=3)
        for index, name in enumerate(["rouge", "jaune", "bleu"]):
            y_wire = rect.height // 4 + index * max(4, rect.height // 8)
            pygame.draw.line(sprite, color_with_light(CABLE_COLORS[name], darkness), (rect.width // 5, y_wire), (rect.width * 4 // 5, y_wire + 5), max(2, rect.width // 18))
        pygame.draw.circle(sprite, color_with_light((210, 40, 35), darkness), (rect.width // 4, rect.height - rect.height // 5), max(2, rect.width // 12))
        pygame.draw.circle(sprite, color_with_light((40, 160, 75), darkness if state.power_fixed else darkness * 0.35), (rect.width * 3 // 4, rect.height - rect.height // 5), max(2, rect.width // 12))
    elif shape == "door":
        pygame.draw.rect(sprite, c, (4, 0, rect.width - 8, rect.height))
        pygame.draw.rect(sprite, (38, 52, 66), (4, 0, rect.width - 8, rect.height), 3)
        pygame.draw.circle(sprite, (230, 210, 90), (rect.width - 14, rect.height // 2), 4)
    elif shape == "shredder":
        pygame.draw.rect(sprite, color_with_light((100, 85, 60), darkness), (0, 0, rect.width, rect.height), border_radius=6)
        pygame.draw.rect(sprite, color_with_light((60, 50, 35), darkness), (2, 2, rect.width - 4, rect.height - 4), 3, border_radius=6)
        slot = pygame.Rect(rect.width // 4, rect.height // 3, rect.width // 2, rect.height // 6)
        pygame.draw.rect(sprite, (20, 18, 15), slot, border_radius=2)
        pygame.draw.rect(sprite, color_with_light((160, 140, 110), darkness), (rect.width // 3, rect.height * 2 // 3, rect.width // 3, rect.height // 5))
        teeth = [(rect.width // 3 + i * 8, rect.height * 2 // 3) for i in range(4)]
        for tx, ty in teeth:
            pygame.draw.polygon(sprite, color_with_light((180, 160, 130), darkness), [(tx, ty), (tx + 3, ty - 6), (tx + 6, ty)])
    elif shape == "monster":
        if MONSTER_FRAMES:
            tick = pygame.time.get_ticks() / 1000
            frame_idx = int(tick * 6) % len(MONSTER_FRAMES)
            frame = MONSTER_FRAMES[frame_idx]
            scaled = pygame.transform.scale(frame, (rect.width, rect.height))
            if darkness < 1.0:
                dark = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
                dark.fill((0, 0, 0, int((1.0 - darkness) * 255)))
                scaled.blit(dark, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            sprite.blit(scaled, (0, 0))
        else:
            pygame.draw.rect(sprite, (10, 10, 12), (0, 0, rect.width, rect.height))
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


def draw_objects(depth_buffer):
    if state.day != 5:
        draw_sprite(EXIT_X, EXIT_Y, (70, 115, 160), 0.95, "sortie", "door", depth_buffer)
    else:
        if state.corridor_exit_open:
            draw_sprite(2.5, CORRIDOR_LENGTH - 1.5, (255, 220, 50), 1.3, "SORTIE - Entre vite !", "door", depth_buffer)
        else:
            draw_sprite(2.5, CORRIDOR_LENGTH - 1.5, (60, 55, 45), 1.1, "porte (verrouillee)", "door", depth_buffer)

    for window in state.windows:
        draw_sprite(window["x"], window["y"], (160, 200, 235), window["size"], None, "window", depth_buffer)

    for item in state.furniture:
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

    if state.day == 2:
        from config import SHREDDER_X, SHREDDER_Y
        draw_sprite(SHREDDER_X, SHREDDER_Y, (150, 120, 80), 0.9, None, "shredder", depth_buffer)
        for i, p in enumerate(state.paintings):
            if not p["gone"]:
                offset = math.sin(pygame.time.get_ticks() / 300 + i) * 0.15
                draw_sprite(p["x"] + offset, p["y"], (180, 55, 75), 0.75, None, "painting", depth_buffer)

    if state.day == 3:
        label = "coffre ouvert" if state.safe_unlocked else "coffre fort"
        draw_sprite(SAFE_X, SAFE_Y, (80, 86, 92), 0.9, label, "safe", depth_buffer)

    if state.day == 4:
        draw_sprite(CABLE_X, CABLE_Y, (230, 190, 55), 0.9, "boite electrique", "cable_box", depth_buffer)
        if not state.power_fixed:
            draw_sprite(state.monster_x, state.monster_y, (10, 10, 12), 1.35, "???", "monster", depth_buffer)

    if state.day == 5 and not state.ending_cinematic:
        draw_sprite(state.monster_x, state.monster_y, (10, 10, 12), 1.35, "???", "monster", depth_buffer)


def draw_crosshair():
    from config import screen
    cx, cy = WIDTH // 2, int(HEIGHT // 2 + state.look_pitch)

    pygame.draw.line(screen, (230, 230, 220), (cx - 8, cy), (cx - 3, cy), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx + 3, cy), (cx + 8, cy), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx, cy - 8), (cx, cy - 3), 1)
    pygame.draw.line(screen, (230, 230, 220), (cx, cy + 3), (cx, cy + 8), 1)




def draw_ceiling_code_hint():
    from config import screen, BIG
    if state.day != 3:
        return

    if game.distance(state.player_x, state.player_y, 1.5, 9.5) > 2.2 or state.look_pitch < 165:
        return

    text = BIG.render("CODE " + state.safe_code, True, (65, 55, 38))
    shadow = BIG.render("CODE " + state.safe_code, True, (210, 200, 160))
    x = WIDTH // 2 - text.get_width() // 2
    y = 188
    screen.blit(shadow, (x + 2, y + 2))
    screen.blit(text, (x, y))


def draw_player_body(moving):
    global _BODY_OVERLAY
    from config import screen
    tick = pygame.time.get_ticks() / 1000
    walk = math.sin(tick * (8.0 if moving else 2.0))
    bob = int(walk * (12 if moving else 3))
    light = 0.55 if state.day == 4 and not state.power_fixed else 1.0

    skin = color_with_light((214, 164, 118), light)
    skin_shadow = color_with_light((170, 112, 82), light)
    sleeve = color_with_light((48, 61, 78), light)
    shoe = color_with_light((32, 31, 34), light)
    sole = color_with_light((86, 83, 78), light)

    if _BODY_OVERLAY is None:
        _BODY_OVERLAY = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _BODY_OVERLAY.fill((0, 0, 0, 0))
    overlay = _BODY_OVERLAY

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

    if game.selected_item() == "Clef":
        key_x = right_hand[0] + 24
        key_y = right_hand[1] - 31
        gold = color_with_light((230, 190, 70), light)
        pygame.draw.circle(overlay, (*gold, 255), (key_x, key_y), 14, 5)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 14, key_y), (key_x + 73, key_y + 3), 9)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 56, key_y + 3), (key_x + 56, key_y + 23), 7)
        pygame.draw.line(overlay, (*gold, 255), (key_x + 71, key_y + 3), (key_x + 71, key_y + 17), 7)

    if state.look_pitch < -122:
        foot_alpha = max(0, min(235, int((-state.look_pitch - 122) * 1.26)))
        foot_y = HEIGHT - 216 + int(max(-88, state.look_pitch) * 0.18)
        spread = 101 + int(min(80, -state.look_pitch * 0.25))
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
    from config import screen, SMALL
    x, y = 240, 24
    bar_w, bar_h = 216, 28
    pygame.draw.rect(screen, (35, 12, 12), (x, y, bar_w, bar_h), border_radius=6)
    fill_w = int(bar_w * max(0, state.player_health) / 10)
    pygame.draw.rect(screen, (190, 35, 35), (x, y, fill_w, bar_h), border_radius=6)
    pygame.draw.rect(screen, (235, 210, 185), (x, y, bar_w, bar_h), 3, border_radius=6)
    hp = SMALL.render("PV " + str(state.player_health) + "/10", True, (255, 235, 220))
    screen.blit(hp, (x + bar_w + 14, y - 1))


def draw_day_timer():
    from config import screen, FONT
    remaining = max(0, int(math.ceil(state.day_timer)))
    color = (255, 235, 170) if remaining > 10 else (255, 90, 70)
    text = FONT.render("Temps : " + str(remaining) + "s", True, color)
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 21))


def draw_inventory_bar():
    from config import screen, SMALL
    slot_size = 90
    gap = 14
    total_w = slot_size * 4 + gap * 3
    x0 = WIDTH // 2 - total_w // 2
    y = HEIGHT - 112

    for index in range(4):
        rect = pygame.Rect(x0 + index * (slot_size + gap), y, slot_size, slot_size)
        selected = index == state.selected_inventory
        base = (26, 27, 30) if not selected else (58, 52, 34)
        border = (120, 112, 86) if not selected else (245, 210, 90)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 3 if selected else 2, border_radius=6)

        num = SMALL.render(str(index + 1), True, (180, 175, 150))
        screen.blit(num, (rect.x + 5, rect.y + 3))

        item = state.inventory_slots[index]
        if item:
            name = SMALL.render(item, True, (235, 232, 210))
            screen.blit(name, (rect.centerx - name.get_width() // 2, rect.centery - name.get_height() // 2))
        else:
            empty = SMALL.render("Vide", True, (110, 110, 110))
            screen.blit(empty, (rect.centerx - empty.get_width() // 2, rect.centery - empty.get_height() // 2))


def draw_ui():
    from config import screen, FONT, SMALL, BIG
    title = FONT.render("Jour " + str(state.day) + " / 5", True, (255, 235, 170))
    screen.blit(title, (30, 21))
    draw_health_bar()
    draw_day_timer()

    if state.day == 1:
        obj = "Objectif : attends le bruit bizarre puis sors de l'appartement."
    elif state.day == 2:
        left = sum(1 for p in state.paintings if not p["gone"])
        obj = "Objectif : jette les tableaux qui bougent. Restants : " + str(left)
    elif state.day == 3:
        obj = "Objectif : code au plafond du spawn, coffre au fond, clef en main puis clic droit porte."
    elif state.day == 4:
        obj = "Objectif : repare les cables dans le couloir. Ne laisse pas le monstre approcher."
    else:
        obj = "Objectif : cours jusqu'au fond du couloir. La porte s'ouvre dans les 10 dernieres secondes !"

    objective = SMALL.render(obj, True, (220, 220, 220))
    screen.blit(objective, (30, 75))

    controls = SMALL.render("Souris | ZQSD/WASD | Molette inv. | E | ESPACE | ESC", True, (185, 185, 185))
    screen.blit(controls, (WIDTH - controls.get_width() - 30, 31))

    if state.message_timer > 0:
        box = pygame.Rect(30, HEIGHT - 240, WIDTH - 60, 90)
        pygame.draw.rect(screen, (0, 0, 0), box)
        pygame.draw.rect(screen, (180, 160, 110), box, 3)
        txt = FONT.render(state.message, True, (255, 245, 210))
        screen.blit(txt, (box.x + 24, box.y + 22))
        state.message_timer -= 1

    if state.stuck:
        txt = BIG.render("TU T'ENFONCES ! APPUIE SUR ESPACE", True, (255, 80, 80))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 200))
        bar_w = 600
        pygame.draw.rect(screen, (50, 50, 50), (WIDTH // 2 - bar_w // 2, HEIGHT // 2 - 100, bar_w, 34))
        pygame.draw.rect(screen, (255, 70, 70), (WIDTH // 2 - bar_w // 2, HEIGHT // 2 - 100, int(bar_w * state.stuck_clicks / 18), 34))

    if (state.day == 4 and not state.power_fixed) or (state.day == 5 and not state.ending_cinematic):
        alpha = max(40, min(180, int(220 - state.heartbeat * 40)))
        red = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        red.fill((80, 0, 0, alpha // 3))
        screen.blit(red, (0, 0))

        if game.distance(state.player_x, state.player_y, CABLE_X, CABLE_Y) < 1.6:
            bar_w = 520
            pygame.draw.rect(screen, (30, 30, 30), (WIDTH // 2 - bar_w // 2, HEIGHT - 220, bar_w, 30))
            pygame.draw.rect(screen, (240, 200, 70), (WIDTH // 2 - bar_w // 2, HEIGHT - 220, int(bar_w * state.cable_progress / 100), 30))
            t = SMALL.render("Appuie sur E pour ouvrir la boite et relier rouge, jaune et bleu", True, (255, 240, 190))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT - 260))

    prompt = game.get_interact_prompt()
    if prompt and not state.cable_panel_open and not state.safe_panel_open:
        txt = SMALL.render(prompt, True, (255, 245, 210))
        bx = pygame.Rect(0, 0, txt.get_width() + 40, txt.get_height() + 20)
        bx.center = (WIDTH // 2, HEIGHT - 170)
        bg = pygame.Surface(bx.size, pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        screen.blit(bg, bx.topleft)
        pygame.draw.rect(screen, (180, 160, 110), bx, 2, border_radius=8)
        screen.blit(txt, (bx.centerx - txt.get_width() // 2, bx.centery - txt.get_height() // 2))

    draw_inventory_bar()


def draw_cable_panel():
    global _SHADE_PANEL
    from config import screen, FONT, SMALL
    panel, close, left, right = game.cable_panel_rects()
    mouse_pos = pygame.mouse.get_pos()

    if _SHADE_PANEL is None:
        _SHADE_PANEL = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _SHADE_PANEL.fill((0, 0, 0, 165))
    screen.blit(_SHADE_PANEL, (0, 0))

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
        if state.cable_connected[name]:
            pygame.draw.circle(screen, (120, 220, 120), rect.center, 10)
        elif state.selected_cable == name:
            pygame.draw.circle(screen, (255, 255, 230), rect.center, 28, 4)

    for name, rect in right.items():
        color = CABLE_COLORS[name]
        pygame.draw.rect(screen, (42, 43, 47), rect.inflate(24, 24), border_radius=8)
        pygame.draw.circle(screen, color, rect.center, 20)
        pygame.draw.circle(screen, (12, 12, 12), rect.center, 20, 4)
        label = SMALL.render("prise " + name, True, (230, 230, 220))
        screen.blit(label, (rect.right + 18, rect.centery - label.get_height() // 2))

    for name, done in state.cable_connected.items():
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

    if state.selected_cable:
        start = left[state.selected_cable].center
        pygame.draw.line(screen, CABLE_COLORS[state.selected_cable], start, mouse_pos, 10)
        pygame.draw.line(screen, (20, 20, 20), start, mouse_pos, 3)

    progress = sum(state.cable_connected.values())
    status = FONT.render(str(progress) + " / 3 cables relies", True, (245, 233, 190))
    screen.blit(status, (panel.centerx - status.get_width() // 2, panel.bottom - 70))


def draw_safe_panel():
    global _SHADE_PANEL
    from config import screen, FONT, BIG, SMALL
    if _SHADE_PANEL is None:
        _SHADE_PANEL = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _SHADE_PANEL.fill((0, 0, 0, 170))
    screen.blit(_SHADE_PANEL, (0, 0))

    panel = pygame.Rect(WIDTH // 2 - 320, HEIGHT // 2 - 240, 640, 480)
    pygame.draw.rect(screen, (25, 27, 30), panel, border_radius=12)
    pygame.draw.rect(screen, (150, 150, 145), panel, 4, border_radius=12)

    title = FONT.render("Coffre fort", True, (235, 235, 220))
    screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 36))

    display = pygame.Rect(panel.centerx - 160, panel.top + 120, 320, 80)
    pygame.draw.rect(screen, (8, 12, 10), display, border_radius=8)
    pygame.draw.rect(screen, (80, 120, 85), display, 3, border_radius=8)
    shown = state.safe_input + "_" * (len(state.safe_code) - len(state.safe_input))
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


def draw_ending():
    from config import screen, BIG
    t = pygame.time.get_ticks() / 1000
    screen.fill((190, 170, 70))

    for x in range(0, WIDTH, 80):
        pygame.draw.line(screen, (160, 145, 55), (x, 0), (x + math.sin(t + x) * 20, HEIGHT), 2)

    for y in range(0, HEIGHT, 70):
        pygame.draw.line(screen, (210, 190, 90), (0, y), (WIDTH, y + math.cos(t + y) * 15), 2)

    fade = min(255, int(state.ending_timer * 50))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, max(0, 180 - fade // 2)))
    screen.blit(overlay, (0, 0))

    if state.ending_timer < 2:
        text = "..."
    elif state.ending_timer < 4:
        text = "Tu ouvres les yeux."
    elif state.ending_timer < 6:
        text = "Les murs jaunes ne sont plus là."
    elif state.ending_timer < 8:
        text = "Bienvenue dans la Réalité."
    else:
        text = "FIN"

    txt = BIG.render(text, True, (30, 25, 10))
    screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 40))


def draw_game_over():
    from config import screen, BIG, FONT, SMALL
    if state.ending_cinematic:
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
    from config import screen, BIG, FONT, SMALL
    screen.fill((18, 5, 7))
    pulse = int((math.sin(pygame.time.get_ticks() / 220) + 1) * 25)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((120 + pulse, 0, 0, 55))
    screen.blit(overlay, (0, 0))

    title = BIG.render("TU ES MORT", True, (255, 70, 70))
    reason = FONT.render(state.death_message, True, (235, 215, 205))
    restart = FONT.render("Appuie sur ESPACE ou clique pour recommencer au debut.", True, (255, 235, 190))
    hp = SMALL.render("PV : 0 / 10", True, (210, 160, 150))

    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 166))
    screen.blit(reason, (WIDTH // 2 - reason.get_width() // 2, HEIGHT // 2 - 56))
    screen.blit(hp, (WIDTH // 2 - hp.get_width() // 2, HEIGHT // 2 + 14))
    screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 101))


def draw_loading_screen():
    from config import screen, BIG, FONT, SMALL
    progress = min(1.0, state.loading_timer / 10.0)
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
    from config import screen, BIG, FONT, SMALL
    t = state.intro_timer
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
        line1 = "Pour survivre, tu devras accomplir des taches sur 5 jours."
        line2 = "Mais tu n'as que 1 minutes par jours."
    else:
        line1 = "Voyons si tu es digne"
        line2 = "de t'échappé."

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
        "options": pygame.Rect(center_x - 165, 572, 330, 84),
        "quit": pygame.Rect(center_x - 165, 815, 330, 84),
    }


def options_rects():
    center_x = WIDTH // 2
    return {
        "vol_down": pygame.Rect(center_x - 165, 430, 82, 60),
        "vol_up": pygame.Rect(center_x + 83, 430, 82, 60),
        "music_vol_down": pygame.Rect(center_x - 165, 540, 82, 60),
        "music_vol_up": pygame.Rect(center_x + 83, 540, 82, 60),
        "back": pygame.Rect(center_x - 165, 660, 330, 60),
    }


def draw_button(rect, text, mouse_pos, main=False):
    from config import screen, FONT
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
    from config import screen, BIG, FONT, SMALL
    mouse_pos = pygame.mouse.get_pos()
    screen.fill((20, 19, 17))

    for y in range(0, HEIGHT, 58):
        color = (35, 32, 25) if (y // 58) % 2 == 0 else (28, 27, 23)
        pygame.draw.rect(screen, color, (0, y, WIDTH, 58))

    for x in range(0, WIDTH, 90):
        pygame.draw.line(screen, (62, 48, 30), (x, HEIGHT), (x + 140, 0), 1)

    title = BIG.render("BACKROOM :", True, (220, 200, 110))
    subtitle = BIG.render("One Minute to Escape", True, (230, 230, 220))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 167))
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 268))

    rects = menu_rects()
    draw_button(rects["play"], "Lancer la partie", mouse_pos, True)
    draw_button(rects["options"], "Options", mouse_pos)
    draw_button(rects["quit"], "Quitter", mouse_pos)


def draw_options_menu():
    from config import screen, BIG, FONT, SMALL
    import sounds
    mouse_pos = pygame.mouse.get_pos()
    screen.fill((20, 19, 17))

    for y in range(0, HEIGHT, 58):
        color = (35, 32, 25) if (y // 58) % 2 == 0 else (28, 27, 23)
        pygame.draw.rect(screen, color, (0, y, WIDTH, 58))

    for x in range(0, WIDTH, 90):
        pygame.draw.line(screen, (62, 48, 30), (x, HEIGHT), (x + 140, 0), 1)

    title = FONT.render("Options", True, (245, 222, 142))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 170))

    rects = options_rects()

    draw_button(rects["vol_down"], "-", mouse_pos)
    draw_button(rects["vol_up"], "+", mouse_pos)

    vol_box = pygame.Rect(WIDTH // 2 - 70, 430, 140, 60)
    pygame.draw.rect(screen, (12, 12, 13), vol_box, border_radius=8)
    pygame.draw.rect(screen, (132, 118, 78), vol_box, 2, border_radius=8)
    vol = FONT.render("Volume " + str(int(sounds.sound_volume * 100)) + "%", True, (238, 234, 215))
    screen.blit(vol, (vol_box.centerx - vol.get_width() // 2, vol_box.centery - vol.get_height() // 2))

    eff_label = SMALL.render("Effets sonores", True, (190, 185, 165))
    screen.blit(eff_label, (WIDTH // 2 - eff_label.get_width() // 2, 400))

    draw_button(rects["music_vol_down"], "-", mouse_pos)
    draw_button(rects["music_vol_up"], "+", mouse_pos)

    music_box = pygame.Rect(WIDTH // 2 - 70, 540, 140, 60)
    pygame.draw.rect(screen, (12, 12, 13), music_box, border_radius=8)
    pygame.draw.rect(screen, (132, 118, 78), music_box, 2, border_radius=8)
    music_vol_text = FONT.render("Volume " + str(int(sounds.music_volume * 100)) + "%", True, (238, 234, 215))
    screen.blit(music_vol_text, (music_box.centerx - music_vol_text.get_width() // 2, music_box.centery - music_vol_text.get_height() // 2))

    music_label = SMALL.render("Musique", True, (190, 185, 165))
    screen.blit(music_label, (WIDTH // 2 - music_label.get_width() // 2, 510))

    draw_button(rects["back"], "Retour", mouse_pos)


def pause_menu_rects():
    center_x = WIDTH // 2
    return {
        "vol_down": pygame.Rect(center_x - 146, 378, 70, 50),
        "vol_up": pygame.Rect(center_x + 76, 378, 70, 50),
        "music_vol_down": pygame.Rect(center_x - 146, 468, 70, 50),
        "music_vol_up": pygame.Rect(center_x + 76, 468, 70, 50),
        "resume": pygame.Rect(center_x - 146, 548, 292, 56),
        "menu": pygame.Rect(center_x - 146, 618, 292, 56),
    }


def save_pause_bg():
    global _PAUSE_BG
    from config import screen
    _PAUSE_BG = screen.copy()


def clear_pause_bg():
    global _PAUSE_BG
    _PAUSE_BG = None


def draw_pause_menu():
    global _PAUSE_BG
    from config import screen, FONT, SMALL
    mouse_pos = pygame.mouse.get_pos()

    if _PAUSE_BG is None:
        save_pause_bg()
    bg = _PAUSE_BG
    small = pygame.transform.scale(bg, (WIDTH // 6, HEIGHT // 6))
    bg = pygame.transform.scale(small, (WIDTH, HEIGHT))
    screen.blit(bg, (0, 0))

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 70))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 260, 400, 520)
    pygame.draw.rect(screen, (22, 23, 25), panel, border_radius=12)
    pygame.draw.rect(screen, (190, 170, 104), panel, 3, border_radius=12)

    title = FONT.render("PAUSE", True, (245, 222, 142))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.top + 30))

    rects = pause_menu_rects()

    draw_button(rects["vol_down"], "-", mouse_pos)
    draw_button(rects["vol_up"], "+", mouse_pos)

    vol_box = pygame.Rect(WIDTH // 2 - 64, 378, 128, 50)
    pygame.draw.rect(screen, (12, 12, 13), vol_box, border_radius=8)
    pygame.draw.rect(screen, (132, 118, 78), vol_box, 2, border_radius=8)
    vol_text = FONT.render("Volume " + str(int(sounds.sound_volume * 100)) + "%", True, (238, 234, 215))
    screen.blit(vol_text, (vol_box.centerx - vol_text.get_width() // 2, vol_box.centery - vol_text.get_height() // 2))

    eff_label = SMALL.render("Effets sonores", True, (190, 185, 165))
    screen.blit(eff_label, (WIDTH // 2 - eff_label.get_width() // 2, 355))

    draw_button(rects["music_vol_down"], "-", mouse_pos)
    draw_button(rects["music_vol_up"], "+", mouse_pos)

    music_box = pygame.Rect(WIDTH // 2 - 64, 468, 128, 50)
    pygame.draw.rect(screen, (12, 12, 13), music_box, border_radius=8)
    pygame.draw.rect(screen, (132, 118, 78), music_box, 2, border_radius=8)
    music_vol_text = FONT.render("Volume " + str(int(sounds.music_volume * 100)) + "%", True, (238, 234, 215))
    screen.blit(music_vol_text, (music_box.centerx - music_vol_text.get_width() // 2, music_box.centery - music_vol_text.get_height() // 2))

    music_label = SMALL.render("Musique", True, (190, 185, 165))
    screen.blit(music_label, (WIDTH // 2 - music_label.get_width() // 2, 445))

    draw_button(rects["resume"], "Reprendre", mouse_pos, True)
    draw_button(rects["menu"], "Menu principal", mouse_pos)


def debug_menu_rects():
    center_x = WIDTH // 2
    return {
        "day1": pygame.Rect(center_x - 240, 230, 150, 44),
        "day2": pygame.Rect(center_x - 75, 230, 150, 44),
        "day3": pygame.Rect(center_x + 90, 230, 150, 44),
        "day4": pygame.Rect(center_x - 240, 290, 150, 44),
        "day5": pygame.Rect(center_x - 75, 290, 150, 44),
        "give_key": pygame.Rect(center_x + 90, 290, 150, 44),
        "tp_exit": pygame.Rect(center_x - 160, 360, 320, 44),
        "god": pygame.Rect(center_x - 160, 420, 320, 44),
        "close": pygame.Rect(center_x - 160, 500, 320, 44),
    }


def draw_debug_menu():
    from config import screen, FONT, SMALL
    mouse_pos = pygame.mouse.get_pos()

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(WIDTH // 2 - 260, 140, 520, 430)
    pygame.draw.rect(screen, (22, 23, 25), panel, border_radius=12)
    pygame.draw.rect(screen, (200, 180, 80), panel, 3, border_radius=12)

    title = FONT.render("MENU DEBUG", True, (245, 222, 142))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, panel.top + 18))

    pos = SMALL.render(f"Position: {state.player_x:.2f}, {state.player_y:.2f}  Jour: {state.day}", True, (190, 185, 165))
    screen.blit(pos, (WIDTH // 2 - pos.get_width() // 2, panel.top + 55))

    rects = debug_menu_rects()
    draw_button(rects["day1"], "Jour 1", mouse_pos)
    draw_button(rects["day2"], "Jour 2", mouse_pos)
    draw_button(rects["day3"], "Jour 3", mouse_pos)
    draw_button(rects["day4"], "Jour 4", mouse_pos)
    draw_button(rects["day5"], "Jour 5", mouse_pos)
    draw_button(rects["give_key"], "Donner clef", mouse_pos)
    draw_button(rects["tp_exit"], "TP a la sortie", mouse_pos)
    god_text = "Dieu: ON" if state.player_health == 999 else "Dieu: OFF"
    draw_button(rects["god"], god_text, mouse_pos)
    draw_button(rects["close"], "Fermer (ESC)", mouse_pos)


def handle_debug_click(pos):
    import game
    from config import CORRIDOR_LENGTH, EXIT_X, EXIT_Y

    rects = debug_menu_rects()
    if rects["close"].collidepoint(pos):
        state.debug_menu_open = False
        if state.game_state == "playing":
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            pygame.mouse.get_rel()
        return

    day_map = {
        "day1": 1, "day2": 2, "day3": 3, "day4": 4, "day5": 5,
    }
    for key, d in day_map.items():
        if rects[key].collidepoint(pos):
            state.day = d
            state.day_timer = 60.0
            state.game_finished = False
            state.ending_cinematic = False
            state.corridor_exit_open = False
            if d == 5:
                state.player_x = 2.5
                state.player_y = 1.5
                state.player_a = math.pi / 2
                state.monster_x = 2.5
                state.monster_y = 0.5
                state.chase_timer = 3.0
            else:
                state.player_x = 1.5
                state.player_y = 9.5
                state.player_a = 0.0
            state.stuck = False
            state.look_pitch = 0
            game.show_message(f"Teleporte au jour {d}", 120)
            return

    if rects["give_key"].collidepoint(pos):
        state.inventory_slots[0] = "Clef"
        game.show_message("Clef ajoutee a l'inventaire", 120)
        return

    if rects["tp_exit"].collidepoint(pos):
        if state.day == 5:
            state.player_y = CORRIDOR_LENGTH - 2.5
        else:
            state.player_x = EXIT_X - 1.5
            state.player_y = EXIT_Y
        game.show_message("TP a la sortie", 120)
        return

    if rects["god"].collidepoint(pos):
        if state.player_health == 999:
            state.player_health = 100
            game.show_message("Dieu: OFF", 120)
        else:
            state.player_health = 999
            game.show_message("Dieu: ON", 120)
