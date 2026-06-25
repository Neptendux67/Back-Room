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


def start_game(reset=True):
    if reset:
        game.reset_game()
    state.game_state = "playing"
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
    sounds.play_sound("click")


def start_intro():
    game.reset_game()
    state.intro_timer = 0.0
    state.game_state = "intro"
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()
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
        return True

    return False


def handle_options_click(pos):
    rects = render.options_rects()
    if rects["sound"].collidepoint(pos):
        sounds.sound_enabled = not sounds.sound_enabled
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

    if rects["back"].collidepoint(pos):
        state.game_state = "menu"
        sounds.play_sound("click")
        return


sounds.load_sounds()

running = True

while running:
    dt = config.clock.tick(60) / 1000
    moving_now = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state.game_state == "menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if handle_menu_click(event.pos):
                    running = False

        if state.game_state == "options":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state.game_state = "menu"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_options_click(event.pos)

        elif state.game_state == "loading":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                state.game_state = "menu"

        elif state.game_state == "intro":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game(reset=False)

        elif state.game_state == "dead":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                start_game()

        elif state.game_state == "playing":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state.cable_panel_open:
                game.handle_cable_click(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and not state.cable_panel_open and not state.safe_panel_open:
                game.use_selected_item()

            if event.type == pygame.MOUSEWHEEL and not state.cable_panel_open and not state.safe_panel_open:
                state.selected_inventory = (state.selected_inventory - event.y) % len(state.inventory_slots)
                sounds.play_sound("click")

            if event.type == pygame.MOUSEMOTION and not state.game_finished and not state.cable_panel_open and not state.safe_panel_open:
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
                        running = False

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

    if state.game_state == "loading":
        state.loading_timer += dt
        if state.loading_timer >= config.LOADING_DURATION:
            state.game_state = "menu"
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

    keys = pygame.key.get_pressed()

    if not state.game_finished:
        speed = 0.085 if state.day == 5 else 0.050

        if not state.stuck and not state.cable_panel_open and not state.safe_panel_open:
            forward = keys[pygame.K_w] or keys[pygame.K_z]
            backward = keys[pygame.K_s]
            left = keys[pygame.K_a] or keys[pygame.K_q]
            right = keys[pygame.K_d]
            moving_now = forward or backward or left or right

            if forward:
                game.try_move(math.cos(state.player_a) * speed, math.sin(state.player_a) * speed)
            if backward:
                game.try_move(-math.cos(state.player_a) * speed, -math.sin(state.player_a) * speed)
            if left:
                game.try_move(math.sin(state.player_a) * speed, -math.cos(state.player_a) * speed)
            if right:
                game.try_move(-math.sin(state.player_a) * speed, math.cos(state.player_a) * speed)

        sounds.update_footsteps(moving_now)
        game.check_exit()

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
        render.draw_floor_ceiling()
        depth_buffer = render.cast_rays()
        render.draw_objects(depth_buffer)
        render.draw_player_body(moving_now)
        render.draw_ceiling_code_hint()
        render.draw_crosshair()

        if state.shake > 0:
            state.shake -= 1
            offset_x = random.randint(-state.shake, state.shake)
            offset_y = random.randint(-state.shake, state.shake)
            copy = config.screen.copy()
            config.screen.fill((0, 0, 0))
            config.screen.blit(copy, (offset_x, offset_y))

        render.draw_ui()
        if state.cable_panel_open:
            render.draw_cable_panel()
        if state.safe_panel_open:
            render.draw_safe_panel()

    pygame.display.flip()

pygame.mouse.set_visible(True)
pygame.event.set_grab(False)
pygame.quit()
sys.exit()
