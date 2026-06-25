import math
import random
import sys
import pygame
 
import config
import state
import sounds
import game
import render

pygame.init()

try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    sounds.sound_available = True
except pygame.error:
    sounds.sound_available = False

config.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
pygame.display.set_caption("Backroom : One Minute to Escape")
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
    sounds.stop_all_sounds()
    sounds.start_ambient_music()
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
    sounds.start_ambient_music()
    sounds.play_sound("click")


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
    rects = render.options_rects()
    if rects["vol_down"].collidepoint(pos):
        sounds.sound_volume = max(0.0, round(sounds.sound_volume - 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["vol_up"].collidepoint(pos):
        sounds.sound_volume = min(1.0, round(sounds.sound_volume + 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["music_vol_down"].collidepoint(pos):
        sounds.music_volume = max(0.0, round(sounds.music_volume - 0.1, 1))
        sounds.start_menu_music()
        sounds.play_sound("click")
        return

    if rects["music_vol_up"].collidepoint(pos):
        sounds.music_volume = min(1.0, round(sounds.music_volume + 0.1, 1))
        sounds.start_menu_music()
        sounds.play_sound("click")
        return

    if rects["back"].collidepoint(pos):
        enter_menu()
        sounds.play_sound("click")
        return


def handle_pause_click(pos):
    rects = render.pause_menu_rects()
    if rects["resume"].collidepoint(pos):
        render.clear_pause_bg()
        state.game_state = "playing"
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()
        sounds.play_sound("click")
        return

    if rects["vol_down"].collidepoint(pos):
        sounds.sound_volume = max(0.0, round(sounds.sound_volume - 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["vol_up"].collidepoint(pos):
        sounds.sound_volume = min(1.0, round(sounds.sound_volume + 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["music_vol_down"].collidepoint(pos):
        sounds.music_volume = max(0.0, round(sounds.music_volume - 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["music_vol_up"].collidepoint(pos):
        sounds.music_volume = min(1.0, round(sounds.music_volume + 0.1, 1))
        sounds.play_sound("click")
        return

    if rects["menu"].collidepoint(pos):
        render.clear_pause_bg()
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

        if not state.debug_menu_open and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                state.debug_input = state.debug_input[:-1]
            elif event.unicode:
                state.debug_input += event.unicode
                if "admin" in state.debug_input:
                    state.debug_input = ""
                    state.debug_menu_open = True
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)

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
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                start_game()

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
                        game.show_message("Tu t'arraches du sol. Ne reste pas ici.", 240)

                if event.key == pygame.K_e and not state.cable_panel_open and not state.safe_panel_open:
                    game.interact()

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
        render.draw_death_screen()
        pygame.display.flip()
        continue

    if state.game_state == "paused":
        render.draw_pause_menu()
        pygame.display.flip()
        continue

    keys = pygame.key.get_pressed()

    if not state.game_finished:
        if state.day == 5:
            state.is_sprinting = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and state.stamina > 0
            speed = config.SPRINT_SPEED if state.is_sprinting else config.WALK_SPEED
        else:
            speed = config.WALK_SPEED

        if not state.stuck and not state.cable_panel_open and not state.safe_panel_open and not state.death_cinematic:
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
        if state.death_timer >= 4.5:
            state.death_cinematic = False
            state.game_state = "dead"
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
    else:
        game.update_day_events(dt)

    if state.game_state == "dead":
        render.draw_death_screen()
        pygame.display.flip()
        continue

    if state.game_finished:
        if state.ending_cinematic:
            state.ending_timer += dt
        sounds.update_footsteps(False)
        render.draw_game_over()
    else:
        original_screen = config.screen
        if state.death_cinematic:
            temp_surf = pygame.Surface((config.WIDTH, config.HEIGHT))
            config.screen = temp_surf
            
            # Move camera back safely
            dist = 2.0
            while dist > 0.5:
                cx = state.death_pos_x - math.cos(state.death_pos_a) * dist
                cy = state.death_pos_y - math.sin(state.death_pos_a) * dist
                if not game.wall_at(cx, cy):
                    break
                dist -= 0.15
                
            orig_px = state.player_x
            orig_py = state.player_y
            orig_pa = state.player_a
            orig_pitch = state.look_pitch
            orig_cz = getattr(state, "camera_z", 0.0)
            
            state.camera_z = 0.38
            state.player_x = state.death_pos_x - math.cos(state.death_pos_a) * dist
            state.player_y = state.death_pos_y - math.sin(state.death_pos_a) * dist
            state.player_a = state.death_pos_a
            
            # Smooth look down tilt (look further down since camera is elevated)
            look_down_progress = min(1.0, state.death_timer / 1.5)
            state.look_pitch = int(-260 * look_down_progress)
            
        render.draw_floor_ceiling()
        depth_buffer = render.cast_rays()
        render.draw_objects(depth_buffer)
        
        if state.death_cinematic:
            config.screen = original_screen
            state.player_x = orig_px
            state.player_y = orig_py
            state.player_a = orig_pa
            state.look_pitch = orig_pitch
            state.camera_z = orig_cz
            
            config.screen.blit(temp_surf, (0, 0))
            
            # Red vignette blood fade-in
            vignette = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
            alpha = min(220, int(state.death_timer * 75))
            vignette.fill((160, 0, 0, alpha))
            config.screen.blit(vignette, (0, 0))
        else:
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

            render.draw_ui()
            if state.cable_panel_open:
                render.draw_cable_panel()
            if state.safe_panel_open:
                render.draw_safe_panel()

    if state.debug_menu_open:
        render.draw_debug_menu()

    pygame.display.flip()

sounds.stop_menu_music()
pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
sys.exit()
