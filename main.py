import math
import random
import sys
import pygame
 
import config
import state
import sounds
import game
import render
import settings

pygame.init()

try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    sounds.sound_available = True
except pygame.error:
    sounds.sound_available = False

settings.load()
settings.apply()
pygame.display.set_caption("Backroom : One Minute to Escape")
try:
    icon = pygame.image.load(os.path.join("assets", "ui", "logo.png"))
    pygame.display.set_icon(icon)
except Exception:
    pass
config.clock = pygame.time.Clock()

config.FONT = pygame.font.SysFont("arial", 22)
config.BIG = pygame.font.SysFont("arial", 46, bold=True)
config.SMALL = pygame.font.SysFont("arial", 16)

render.load_textures()

pygame.mouse.set_visible(True)
pygame.event.set_grab(False)


def enter_menu():
    state.game_state = "menu"
    sounds.stop_all_sounds()
    sounds.start_menu_music()


def start_game(reset=True):
    if reset:
        game.reset_game()
    render.clear_pause_bg()
    state.game_state = "playing"
    state.level_intro_timer = 2.5
    sounds.stop_all_sounds()
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
    sounds.play_sound("click")


def start_intro():
    game.reset_game()
    render.clear_pause_bg()
    state.intro_timer = 0.0
    state.game_state = "intro"
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
    sounds.stop_menu_music()


def handle_menu_click(pos):
    rects = render.menu_rects()
    if rects["play"].collidepoint(pos):
        start_intro()
        return False

    if rects["options"].collidepoint(pos):
        state.game_state = "options"
        sounds.play_sound("click")
        return False

    if rects["quit"].collidepoint(pos):
        sounds.stop_menu_music()
        return True

    return False


def handle_options_click(pos):
    import settings
    rects = render.options_rects()
    opts = settings.get()
    changed = False

    if rects["vol_down"].collidepoint(pos):
        sounds.sound_volume = max(0.0, round(sounds.sound_volume - 0.1, 1))
        sounds.play_sound("click")
        opts["sound_volume"] = sounds.sound_volume
        changed = True

    if rects["vol_up"].collidepoint(pos):
        sounds.sound_volume = min(1.0, round(sounds.sound_volume + 0.1, 1))
        sounds.play_sound("click")
        opts["sound_volume"] = sounds.sound_volume
        changed = True

    if rects["music_vol_down"].collidepoint(pos):
        sounds.music_volume = max(0.0, round(sounds.music_volume - 0.1, 1))
        sounds.start_menu_music()
        sounds.play_sound("click")
        opts["music_volume"] = sounds.music_volume
        changed = True

    if rects["music_vol_up"].collidepoint(pos):
        sounds.music_volume = min(1.0, round(sounds.music_volume + 0.1, 1))
        sounds.start_menu_music()
        sounds.play_sound("click")
        opts["music_volume"] = sounds.music_volume
        changed = True

    if rects["fullscreen"].collidepoint(pos):
        opts["fullscreen"] = not opts["fullscreen"]
        settings.apply()
        render.load_textures()
        changed = True
        sounds.play_sound("click")

    if rects["resolution"].collidepoint(pos):
        opts["resolution_index"] = (opts["resolution_index"] + 1) % len(settings.RESOLUTIONS)
        settings.apply()
        render.load_textures()
        changed = True
        sounds.play_sound("click")

    if state.mongolian_unlocked and rects["music_track"] and rects["music_track"].collidepoint(pos):
        tracks = ["ambient-music", "mongolian-secret"]
        cur = opts.get("music_track", "ambient-music")
        idx = (tracks.index(cur) + 1) % len(tracks) if cur in tracks else 0
        opts["music_track"] = tracks[idx]
        sounds.start_ambient_music(tracks[idx])
        changed = True
        sounds.play_sound("click")

    if rects["back"].collidepoint(pos):
        settings.save()
        if state.prev_state == "paused":
            state.prev_state = None
            state.game_state = "paused"
        else:
            enter_menu()
        sounds.play_sound("click")
        return

    if changed:
        settings.save()


def handle_pause_click(pos):
    rects = render.pause_menu_rects()

    if rects["resume"].collidepoint(pos):
        render.clear_pause_bg()
        state.pause_submenu = None
        state.game_state = "playing"
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()
        sounds.play_sound("click")
        return

    if rects["options"].collidepoint(pos):
        state.prev_state = "paused"
        state.game_state = "options"
        sounds.play_sound("click")
        return

    if rects["menu"].collidepoint(pos):
        render.clear_pause_bg()
        state.pause_submenu = None
        sounds.play_sound("click")
        enter_menu()
        return


sounds.load_sounds()

running = True

while running:
    dt = min(config.clock.tick(config.FPS_CAP) / 1000, 0.05)  # cap dt to prevent spiral-of-death
    moving_now = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if not state.debug_menu_open and state.game_state == "playing" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                state.debug_input = state.debug_input[:-1]
            elif event.unicode:
                state.debug_input += event.unicode
                if "admin" in state.debug_input:
                    state.debug_input = ""
                    state.debug_menu_open = True
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                if "mongolian" in state.debug_input:
                    state.debug_input = ""
                    state.mongolian_unlocked = True

        if state.debug_menu_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state.debug_menu_open = False
                if state.game_state == "playing":
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    pygame.mouse.get_rel()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                render.handle_debug_click(event.pos)
            continue

        if state.game_state == "menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if handle_menu_click(event.pos):
                    running = False

        if state.game_state == "options":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state.prev_state == "paused":
                    state.prev_state = None
                    state.game_state = "paused"
                else:
                    enter_menu()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_options_click(event.pos)

        elif state.game_state == "loading":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                enter_menu()

        elif state.game_state == "intro":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game(reset=False)

        elif state.game_state == "paused":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                render.clear_pause_bg()
                state.game_state = "playing"
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                pygame.mouse.get_rel()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_pause_click(event.pos)

        elif state.game_state == "dead":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                sounds.stop_all_sounds()
                enter_menu()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                btn_w, btn_h = 220, 50
                replay_rect = pygame.Rect(config.WIDTH // 2 - btn_w // 2, config.HEIGHT // 2 + 50, btn_w, btn_h)
                menu_rect = pygame.Rect(config.WIDTH // 2 - btn_w // 2, config.HEIGHT // 2 + 120, btn_w, btn_h)
                if replay_rect.collidepoint(event.pos):
                    start_game()
                elif menu_rect.collidepoint(event.pos):
                    sounds.stop_all_sounds()
                    enter_menu()

        elif state.game_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.cable_panel_open:
                    game.handle_cable_click(event.pos)
                elif state.safe_panel_open:
                    game.handle_safe_click(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and not state.cable_panel_open and not state.safe_panel_open:
                game.use_selected_item()

            if event.type == pygame.MOUSEWHEEL and not state.cable_panel_open and not state.safe_panel_open:
                state.selected_inventory = (state.selected_inventory - event.y) % len(state.inventory_slots)
                sounds.play_sound("click")

            if event.type == pygame.MOUSEMOTION and not state.game_finished and not state.cable_panel_open and not state.safe_panel_open and not state.death_cinematic:
                state.player_a += event.rel[0] * config.MOUSE_SENSITIVITY
                state.look_pitch -= event.rel[1] * 1.1
                state.look_pitch = int(max(-config.PITCH_LIMIT, min(config.PITCH_LIMIT, state.look_pitch)))

            if event.type == pygame.KEYDOWN:
                if state.safe_panel_open:
                    game.handle_safe_key(event)
                    continue

                if event.key == pygame.K_ESCAPE:
                    if state.cable_panel_open:
                        game.close_cable_panel()
                    elif state.safe_panel_open:
                        game.close_safe_panel()
                    else:
                        state.pause_submenu = None
                        state.game_state = "paused"
                        render.save_pause_bg()
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)

                if event.key == pygame.K_e and state.cable_panel_open:
                    game.close_cable_panel()
                    continue

                if event.key == pygame.K_SPACE and state.stuck:
                    state.stuck_clicks += 1
                    if state.stuck_clicks >= 18:
                        state.stuck = False
                        state.stuck_clicks = 0
                        state.sand_damage_timer = 0.0
                        game.show_message("Tu t'arraches du sol. Ne reste pas ici.", 4.0)

                if event.key == pygame.K_e and not state.cable_panel_open and not state.safe_panel_open:
                    if state.lore_active:
                        game.lore_input()
                    else:
                        game.interact()

                if event.key == pygame.K_SPACE and not state.stuck and state.lore_active:
                    game.lore_input()

        if state.game_finished and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            sounds.stop_all_sounds()
            enter_menu()

    if state.debug_menu_open:
        render.draw_debug_menu()
        pygame.display.flip()
        continue

    if state.game_state == "loading":
        state.loading_timer += dt
        if state.loading_timer >= config.LOADING_DURATION:
            enter_menu()
        render.draw_loading_screen()
        pygame.display.flip()
        continue

    if state.game_state == "intro":
        state.intro_timer += dt
        if state.intro_timer >= config.INTRO_DURATION:
            start_game(reset=False)
        render.draw_intro_cinematic()
        pygame.display.flip()
        continue

    if state.game_state == "menu":
        render.draw_menu()
        pygame.display.flip()
        continue

    if state.game_state == "options":
        render.draw_options_menu()
        pygame.display.flip()
        continue

    if state.game_state == "dead":
        state.game_over_zoom = min(1.35, state.game_over_zoom + dt * 0.2)
        render.draw_death_screen()
        pygame.display.flip()
        continue

    if state.game_state == "paused":
        render.draw_pause_menu()
        pygame.display.flip()
        continue

    keys = pygame.key.get_pressed()

    if not state.game_finished and not state.transition_active:
        can_sprint = state.day == 5 or state.stamina > 0
        state.is_sprinting = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and can_sprint
        speed = config.SPRINT_SPEED if state.is_sprinting else config.WALK_SPEED

        if not state.stuck and not state.cable_panel_open and not state.safe_panel_open and not state.death_cinematic and not state.lore_active:
            forward = keys[pygame.K_w] or keys[pygame.K_z]
            backward = keys[pygame.K_s]
            left = keys[pygame.K_a] or keys[pygame.K_q]
            right = keys[pygame.K_d]
            moving_now = forward or backward or left or right
            s = speed * dt

            if forward:
                game.try_move(math.cos(state.player_a) * s, math.sin(state.player_a) * s)
            if backward:
                game.try_move(-math.cos(state.player_a) * s, -math.sin(state.player_a) * s)
            if left:
                game.try_move(math.sin(state.player_a) * s, -math.cos(state.player_a) * s)
            if right:
                game.try_move(-math.sin(state.player_a) * s, math.cos(state.player_a) * s)

        sounds.update_footsteps(moving_now)

    if state.death_cinematic:
        state.death_timer += dt
        if state.death_timer >= 0.8 and not state.game_finished:
            state.death_cinematic = False
            state.game_state = "dead"
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
    else:
        game.update_day_events(dt)

    game.update_jumpscares(dt)

    if state.transition_active:
        state.transition_timer += dt
        if state.transition_timer >= 3.0:
            state.transition_active = False

    if state.game_state == "dead":
        state.game_over_zoom = min(1.35, state.game_over_zoom + dt * 0.2)
        render.draw_death_screen()
        pygame.display.flip()
        continue

    if state.game_finished:
        if state.ending_cinematic:
            state.ending_timer += dt
        sounds.update_footsteps(False)
        render.draw_game_over()
    else:
        render.draw_floor_ceiling()
        depth_buffer = render.cast_rays()
        render.draw_objects(depth_buffer)
        if not state.death_cinematic:
            render.draw_player_body(moving_now)
            render.draw_ceiling_code_hint()
            render.draw_crosshair()

        if state.shake > 0:
            state.shake -= 1
            offset_x = random.randint(-state.shake, state.shake)
            offset_y = random.randint(-state.shake, state.shake)
            if not hasattr(config, '_shake_buf'):
                config._shake_buf = pygame.Surface((config.WIDTH, config.HEIGHT))
            config._shake_buf.blit(config.screen, (0, 0))
            config.screen.fill((0, 0, 0))
            config.screen.blit(config._shake_buf, (offset_x, offset_y))

        if state.death_cinematic:
            pitch_target = -config.PITCH_LIMIT
            state.look_pitch += (pitch_target - state.look_pitch) * dt * 12
            t = min(1.0, state.death_timer / 0.8)
            alpha = min(255, int(t * 220))
            vignette = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
            vignette.fill((80, 0, 0, alpha))
            config.screen.blit(vignette, (0, 0))
            if t > 0.2 and random.random() < 0.6:
                for _ in range(8):
                    bx = random.randint(0, config.WIDTH)
                    by = random.randint(0, config.HEIGHT // 2)
                    br = random.randint(3, 16)
                    pygame.draw.circle(vignette, (60, 0, 0, random.randint(60, 180)), (bx, by), br)
            config.screen.blit(vignette, (0, 0))

        if not state.death_cinematic:
            render.draw_ui()
            render.draw_lore_message()
        if state.cable_panel_open:
            render.draw_cable_panel()
        if state.safe_panel_open:
            render.draw_safe_panel()

    if state.jumpscare_active:
        render.draw_jumpscare()

    if state.debug_menu_open:
        render.draw_debug_menu()

    render.draw_transition_overlay()

    if state.game_state in ("playing", "dead", "intro"):
        render.apply_vhs_effect()

    pygame.display.flip()

sounds.stop_menu_music()
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
sys.exit()
