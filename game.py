import math
import random
import pygame
from config import DAY_LIMIT, MAX_HEALTH, APARTMENT_MAP, CORRIDOR_MAP, CORRIDOR_LENGTH, EXIT_X, EXIT_Y, CABLE_X, CABLE_Y, SAFE_X, SAFE_Y, FOV
import state
import sounds


def distance(ax, ay, bx, by):
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def angle_diff(a, b):
    return (a - b + math.pi) % (math.pi * 2) - math.pi


def current_map():
    if state.day == 5:
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
    return is_exit(state.player_x, state.player_y) or distance(state.player_x, state.player_y, EXIT_X, EXIT_Y) < 0.95


def try_move(dx, dy):
    nx = state.player_x + dx
    ny = state.player_y + dy

    if not wall_at(nx, state.player_y):
        state.player_x = nx
    if not wall_at(state.player_x, ny):
        state.player_y = ny


def show_message(text, time=230):
    state.message = text
    state.message_timer = time


def reset_cable_task():
    state.cable_progress = 0
    state.selected_cable = None
    state.cable_panel_open = False
    state.cable_connected = {"rouge": False, "jaune": False, "bleu": False}


def reset_game():
    state.player_x = 1.5
    state.player_y = 9.5
    state.player_a = 0.0
    state.look_pitch = 0

    state.day = 1
    state.day_timer = DAY_LIMIT
    state.message = "Jour 1 : explore l'appartement. Un bruit arrive bientot..."
    state.message_timer = 260
    state.shake = 0
    state.j1_event_done = False
    state.j1_timer = 4.0

    for painting in state.paintings:
        painting["gone"] = False
    for spot in state.sink_spots:
        spot["used"] = False

    state.stuck = False
    state.stuck_clicks = 0
    state.sand_damage_timer = 0.0
    state.player_health = MAX_HEALTH
    state.inventory_slots[:] = [None, None, None, None]
    state.selected_inventory = 0
    state.safe_panel_open = False
    state.safe_input = ""
    state.safe_unlocked = False
    state.safe_code = str(random.randint(100, 999))

    state.power_fixed = False
    reset_cable_task()
    state.monster_x = 12.5
    state.monster_y = 1.5
    state.heartbeat = 0

    state.ending_timer = 0
    state.game_finished = False
    state.death_message = ""
    state.corridor_exit_open = False
    state.ending_cinematic = False


def kill_player(reason):
    sounds.update_footsteps(False)
    state.death_message = reason
    if state.cable_panel_open:
        close_cable_panel()
    if state.safe_panel_open:
        close_safe_panel()
    state.game_state = "dead"
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    sounds.play_sound("bang")


def cable_panel_rects():
    from config import WIDTH, HEIGHT
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
    if state.power_fixed:
        return

    state.cable_panel_open = True
    state.selected_cable = None
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    pygame.mouse.get_rel()
    sounds.play_sound("click")


def close_cable_panel():
    state.cable_panel_open = False
    state.selected_cable = None
    if state.game_state == "playing" and not state.game_finished:
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()


def finish_cable_task():
    state.power_fixed = True
    state.cable_progress = 100
    close_cable_panel()
    show_message("Les 3 cables sont relies. Le courant revient, le monstre disparait.", 280)


def handle_cable_click(pos):
    panel, close, left, right = cable_panel_rects()

    if close.collidepoint(pos):
        close_cable_panel()
        return

    if not panel.collidepoint(pos):
        return

    for name, rect in left.items():
        if rect.collidepoint(pos) and not state.cable_connected[name]:
            state.selected_cable = name
            sounds.play_sound("click")
            return

    for name, rect in right.items():
        if rect.collidepoint(pos) and state.selected_cable:
            if name == state.selected_cable:
                state.cable_connected[name] = True
                state.selected_cable = None
                state.cable_progress = int(sum(state.cable_connected.values()) / 3 * 100)
                sounds.play_sound("electricite")
                if all(state.cable_connected.values()):
                    finish_cable_task()
            else:
                state.selected_cable = None
                show_message("Mauvaise prise. Relie chaque cable a la meme couleur.", 180)
                sounds.play_sound("click")
            return


def add_item_to_inventory(item_name):
    for index, item in enumerate(state.inventory_slots):
        if item is None:
            state.inventory_slots[index] = item_name
            return True
    return False


def selected_item():
    return state.inventory_slots[state.selected_inventory]


def open_safe_panel():
    if state.safe_unlocked:
        show_message("Le coffre est deja ouvert.", 160)
        return

    state.safe_panel_open = True
    state.safe_input = ""
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    pygame.mouse.get_rel()
    sounds.play_sound("click")


def close_safe_panel():
    state.safe_panel_open = False
    state.safe_input = ""
    if state.game_state == "playing" and not state.game_finished:
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()


def unlock_safe():
    state.safe_unlocked = True
    state.safe_input = ""
    close_safe_panel()
    if add_item_to_inventory("Clef"):
        show_message("Le coffre s'ouvre. Tu prends une clef.", 260)
        sounds.play_sound("clef")
    else:
        show_message("Inventaire plein. La clef reste dans le coffre.", 260)
        state.safe_unlocked = False


def handle_safe_key(event):
    if event.key in (pygame.K_ESCAPE, pygame.K_e):
        close_safe_panel()
        return

    if event.key == pygame.K_BACKSPACE:
        state.safe_input = state.safe_input[:-1]
        sounds.play_sound("click")
        return

    if event.key == pygame.K_RETURN:
        if state.safe_input == state.safe_code:
            unlock_safe()
        else:
            state.safe_input = ""
            show_message("Code faux.", 150)
            sounds.play_sound("bang")
        return

    digit = None
    if pygame.K_0 <= event.key <= pygame.K_9:
        digit = str(event.key - pygame.K_0)
    elif pygame.K_KP0 <= event.key <= pygame.K_KP9:
        digit = str(event.key - pygame.K_KP0)

    if digit and len(state.safe_input) < len(state.safe_code):
        state.safe_input += digit
        sounds.play_sound("click")
        if len(state.safe_input) == len(state.safe_code):
            if state.safe_input == state.safe_code:
                unlock_safe()
            else:
                state.safe_input = ""
                show_message("Code faux.", 150)


def get_interact_prompt():
    if state.day == 2:
        for p in state.paintings:
            if not p["gone"] and distance(state.player_x, state.player_y, p["x"], p["y"]) < 1.25:
                return "Appuie sur E pour jeter le tableau"
    if state.day == 3:
        if distance(state.player_x, state.player_y, SAFE_X, SAFE_Y) < 1.6:
            return "Appuie sur E pour ouvrir le coffre"
        if near_exit() and selected_item() == "Clef":
            return "Clic droit pour utiliser la clef sur la porte"
    if state.day == 4:
        if distance(state.player_x, state.player_y, CABLE_X, CABLE_Y) < 1.6 and not state.power_fixed:
            return "Appuie sur E pour ouvrir la boite electrique"
    return None


def interact():
    if state.day == 5 and state.corridor_exit_open:
        door_dist = distance(state.player_x, state.player_y, 2.5, CORRIDOR_LENGTH - 1.5)
        if door_dist < 1.2:
            sounds.play_sound("door")
            state.ending_cinematic = True
            state.ending_timer = 0.0
            state.game_finished = True
            sounds.play_sound("ending")
            return

    if near_exit():
        if state.day == 3:
            if selected_item() == "Clef":
                sounds.play_sound("door")
                next_day()
            else:
                show_message("La porte est verrouillee. Selectionne la clef et fais clic droit.", 220)
        else:
            check_exit()
        return

    if state.day == 2:
        for p in state.paintings:
            if not p["gone"] and distance(state.player_x, state.player_y, p["x"], p["y"]) < 1.25:
                p["gone"] = True
                remaining = sum(1 for item in state.paintings if not item["gone"])
                if remaining == 0:
                    show_message("Tous les tableaux sont jetes. Va a la porte de sortie pour aller au travail.", 300)
                else:
                    show_message("Tu jettes le tableau. Il en reste " + str(remaining) + ".")
                sounds.play_sound("interact")
                return

    if state.day == 4:
        if distance(state.player_x, state.player_y, CABLE_X, CABLE_Y) < 1.6 and not state.power_fixed:
            open_cable_panel()

    if state.day == 3:
        if distance(state.player_x, state.player_y, SAFE_X, SAFE_Y) < 1.6:
            open_safe_panel()


def use_selected_item():
    if state.day == 3 and near_exit():
        if selected_item() == "Clef":
            show_message("Tu ouvres la porte avec la clef.", 180)
            sounds.play_sound("door")
            next_day()
        else:
            show_message("La porte est verrouillee. Selectionne la clef et fais clic droit.", 220)


def next_day():
    state.day += 1
    state.day_timer = DAY_LIMIT
    if state.day == 5:
        state.player_x = 2.5
        state.player_y = 1.5
        state.player_a = math.pi / 2
    else:
        state.player_x = 1.5
        state.player_y = 9.5
        state.player_a = 0.0
    state.look_pitch = 0
    state.stuck = False
    state.stuck_clicks = 0
    state.sand_damage_timer = 0.0

    if state.day == 2:
        show_message("Jour 2 : les tableaux ont change de place. Jette-les avant de sortir.", 300)
    elif state.day == 3:
        show_message("Jour 3 : trouve le code au plafond, ouvre le coffre, prends la clef.", 320)
    elif state.day == 4:
        reset_cable_task()
        state.power_fixed = False
        state.monster_x = 12.5
        state.monster_y = 1.5
        show_message("Jour 4 : coupure de courant. Trouve la boite electrique loin de la sortie.", 300)
    elif state.day == 5:
        state.ending_timer = 0
        state.monster_x = 2.5
        state.monster_y = 0.5
        show_message("Jour 5 : cours jusqu'au fond du long couloir avant la fin du chrono.", 320)
    else:
        state.game_finished = True


def check_exit():
    if not near_exit():
        return

    if state.day == 1:
        if state.j1_event_done:
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Quelque chose te retient. Attends...")
    elif state.day == 2:
        if all(p["gone"] for p in state.paintings):
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Impossible de partir : les tableaux bougent encore.")
    elif state.day == 3:
        if not state.stuck:
            show_message("Porte verrouillee. Trouve la clef, selectionne-la, puis E.", 220)
    elif state.day == 4:
        if state.power_fixed:
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Il faut reparer le courant avant de partir.")
    elif state.day == 5:
        pass


def update_day_events(dt):
    if not state.ending_cinematic:
        state.day_timer -= dt
    if state.day_timer <= 0 and not state.ending_cinematic:
        kill_player("Le temps est ecoule. Tu recommences depuis le debut.")
        return

    if state.day == 1:
        if not state.j1_event_done:
            state.j1_timer -= dt
            if state.j1_timer <= 0:
                state.j1_event_done = True
                state.shake = 22
                show_message("BANG ! Un bruit soudain et impossible vient du plafond. Sors vite !", 320)
                sounds.play_sound("bang")

    if state.day == 3 and not state.stuck:
        for s in state.sink_spots:
            if not s["used"] and distance(state.player_x, state.player_y, s["x"], s["y"]) < 0.65:
                state.stuck = True
                state.stuck_clicks = 0
                state.sand_damage_timer = 0.0
                s["used"] = True
                show_message("Le sable mou t'aspire ! Appuie vite sur ESPACE !", 260)

    if state.day == 3 and state.stuck:
        state.sand_damage_timer += dt
        if state.sand_damage_timer >= 2.0:
            state.sand_damage_timer -= 2.0
            state.player_health -= 1
            show_message("Le sable mou t'etouffe. -1 PV", 150)
            if state.player_health <= 0:
                kill_player("Tu es reste trop longtemps dans le sable mou.")
                return

    if state.day == 4 and not state.power_fixed:
        dx = state.player_x - state.monster_x
        dy = state.player_y - state.monster_y
        dist = math.sqrt(dx * dx + dy * dy)
        monster_angle = math.atan2(state.monster_y - state.player_y, state.monster_x - state.player_x)
        seen = abs(angle_diff(monster_angle, state.player_a)) < (FOV / 2.2) and dist < 9

        if dist > 0.2:
            old_mx, old_my = state.monster_x, state.monster_y
            if seen:
                state.monster_x -= dx / dist * 0.022
                state.monster_y -= dy / dist * 0.022
            else:
                state.monster_x += dx / dist * 0.010
                state.monster_y += dy / dist * 0.010

            if wall_at(state.monster_x, state.monster_y):
                state.monster_x, state.monster_y = old_mx, old_my

        state.heartbeat = max(0, 6 - dist)

        if dist < 0.55:
            show_message("Le monstre t'a touche. Tu te reveilles au debut du jour 4.", 300)
            if state.cable_panel_open:
                close_cable_panel()
            reset_cable_task()
            state.monster_x = 12.5
            state.monster_y = 1.5

    if state.day == 5 and not state.corridor_exit_open and state.day_timer <= 10.0:
        state.corridor_exit_open = True
        show_message("Une porte de sortie apparait au fond ! Cours !", 300)
        state.shake = 18

    if state.day == 5 and not state.ending_cinematic:
        dy = state.player_y - state.monster_y
        dist = abs(dy)
        if dist > 0.2:
            speed = 0.075
            state.monster_y += math.copysign(speed, dy)
            if wall_at(state.monster_x, state.monster_y):
                state.monster_y -= math.copysign(speed, dy)
        state.heartbeat = max(0, 6 - dist)
        if dist < 0.55:
            kill_player("Le monstre t'a rattrape. Tu recommences depuis le debut.")
