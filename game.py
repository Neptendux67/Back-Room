import math
import random
import pygame
from config import DAY_LIMIT, MAX_HEALTH, APARTMENT_MAP, CORRIDOR_MAP, CORRIDOR_LENGTH, EXIT_X, EXIT_Y, CABLE_X, CABLE_Y, SAFE_X, SAFE_Y, SHREDDER_X, SHREDDER_Y, FOV, MONSTER_SPEED
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
    r = 0.22  # Bounding collision radius to prevent wall clipping and seeing through walls
    
    # Check X movement
    nx = state.player_x + dx
    if dx > 0:
        if not wall_at(nx + r, state.player_y - r) and not wall_at(nx + r, state.player_y + r):
            state.player_x = nx
    elif dx < 0:
        if not wall_at(nx - r, state.player_y - r) and not wall_at(nx - r, state.player_y + r):
            state.player_x = nx
            
    # Check Y movement
    ny = state.player_y + dy
    if dy > 0:
        if not wall_at(state.player_x - r, ny + r) and not wall_at(state.player_x + r, ny + r):
            state.player_y = ny
    elif dy < 0:
        if not wall_at(state.player_x - r, ny - r) and not wall_at(state.player_x + r, ny - r):
            state.player_y = ny


def show_message(text, duration=4.0):
    state.lore_active = True
    state.lore_text = text
    state.lore_char_index = 0
    state.lore_timer = 0.0
    state.lore_state = "entering"
    state.lore_hold_time = duration


def update_lore(dt):
    if not state.lore_active:
        return
    state.lore_timer += dt

    if state.lore_state == "entering":
        if state.lore_timer >= 0.35:
            state.lore_state = "typing"
            state.lore_timer = 0.0
            state.lore_char_index = 0

    elif state.lore_state == "typing":
        CHARS_PER_SEC = 45
        prev = state.lore_char_index
        state.lore_char_index = min(len(state.lore_text), int(state.lore_timer * CHARS_PER_SEC))
        if state.lore_char_index > prev:
            sounds.play_sound("tick")
        if state.lore_char_index >= len(state.lore_text):
            state.lore_state = "waiting"
            state.lore_timer = 0.0

    elif state.lore_state == "waiting":
        if state.lore_timer >= state.lore_hold_time:
            state.lore_state = "exiting"
            state.lore_timer = 0.0

    elif state.lore_state == "exiting":
        if state.lore_timer >= 0.35:
            state.lore_active = False


def lore_input():
    if not state.lore_active:
        return False
    if state.lore_state == "typing":
        state.lore_char_index = len(state.lore_text)
        state.lore_state = "waiting"
        state.lore_timer = 0.0
        sounds.play_sound("click")
        return True
    elif state.lore_state == "waiting":
        state.lore_state = "exiting"
        state.lore_timer = 0.0
        sounds.play_sound("click")
        return True
    return False


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
    state.lore_active = False
    state.lore_text = ""
    state.lore_char_index = 0
    state.lore_timer = 0.0
    state.lore_state = ""
    state.shake = 0
    state.j1_event_done = False
    state.j1_timer = 4.0
    state.shredder_cooldown = 0.0

    for painting in state.paintings:
        painting["gone"] = False
        painting["shredded"] = False
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
    state.ending_cinematic = False
    state.stamina = 100
    state.is_sprinting = False
    state.player_has_moved = False
    state.death_cinematic = False
    state.death_timer = 0.0
    state.death_pos_x = 0.0
    state.death_pos_y = 0.0
    state.death_pos_a = 0.0
    state.chase_timer = 3.0
    state.monster_visible = False
    state.monster_scream_played = False
    state.camera_z = 0.0
    state.level_intro_timer = 0.0
    state.transition_active = False
    state.transition_timer = 0.0
    state.mongolian_unlocked = False


def kill_player(reason):
    sounds.update_footsteps(False)
    sounds.stop_ambient_music()
    state.death_message = reason
    if state.cable_panel_open:
        close_cable_panel()
    if state.safe_panel_open:
        close_safe_panel()
        
    state.death_cinematic = True
    state.death_timer = 0.0
    state.shake = 30
    state.game_over_zoom = 0.8
    state.death_pos_x = state.player_x
    state.death_pos_y = state.player_y
    state.death_pos_a = state.player_a

    sounds.play_sound("monster_scream")

    if state.day == 5:
        # Place the monster right next to the player's body
        state.monster_x = state.player_x + math.cos(state.player_a + math.pi / 4.0) * 0.45
        state.monster_y = state.player_y + math.sin(state.player_a + math.pi / 4.0) * 0.45
        state.monster_visible = True
    else:
        state.monster_visible = False
    
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
    show_message("Les 3 câbles sont reliés. Le courant revient.", 4.5)


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
                show_message("Mauvaise prise. Relie chaque câble à la même couleur.", 3.0)
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
        show_message("Le coffre est déjà ouvert.", 2.5)
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
        show_message("Le coffre s'ouvre. Tu prends une clef.", 4.0)
        sounds.play_sound("clef")
    else:
        show_message("Inventaire plein. La clef reste dans le coffre.", 4.0)
        state.safe_unlocked = False


def safe_panel_rects():
    from config import WIDTH, HEIGHT
    panel = pygame.Rect(WIDTH // 2 - 320, HEIGHT // 2 - 240, 640, 480)
    keys = {}
    for i in range(10):
        col = i % 5
        row = i // 5
        key_rect = pygame.Rect(panel.left + 100 + col * 90, panel.top + 290 + row * 64, 60, 48)
        keys[str(i)] = key_rect
    return panel, keys


def handle_safe_click(pos):
    panel, keys = safe_panel_rects()
    if not panel.collidepoint(pos):
        return

    for digit, rect in keys.items():
        if rect.collidepoint(pos):
            if len(state.safe_input) < len(state.safe_code):
                state.safe_input += digit
                sounds.play_sound("click")
                if len(state.safe_input) == len(state.safe_code):
                    if state.safe_input == state.safe_code:
                        unlock_safe()
                    else:
                        state.safe_input = ""
                        show_message("Code faux.", 2.5)
                        sounds.play_sound("bang")
            return


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
            show_message("Code faux.", 2.5)
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
                show_message("Code faux.", 2.5)


def get_interact_prompt():
    if state.day == 5:
        if distance(state.player_x, state.player_y, 2.0, CORRIDOR_LENGTH - 1.5) < 1.2:
            return "Appuie sur E pour sortir"
        return None
    if state.day == 2:
        for p in state.paintings:
            if not p["gone"] and distance(state.player_x, state.player_y, p["x"], p["y"]) < 1.25:
                return "Appuie sur E pour récupérer le tableau"
    if state.day == 3:
        if distance(state.player_x, state.player_y, SAFE_X, SAFE_Y) < 1.6:
            return "Appuie sur E pour ouvrir le coffre"
        if near_exit() and selected_item() == "Clef":
            return "Clic droit pour utiliser la clef sur la porte"
    if state.day == 4:
        if distance(state.player_x, state.player_y, CABLE_X, CABLE_Y) < 1.6 and not state.power_fixed:
            return "Appuie sur E pour ouvrir la boîte électrique"
    return None


def interact():
    if state.day == 5:
        if distance(state.player_x, state.player_y, 2.0, CORRIDOR_LENGTH - 1.5) < 1.2:
            if state.game_finished:
                return
            sounds.play_sound("door")
            sounds.stop_ambient_music()
            state.monster_visible = False
            state.ending_cinematic = True
            state.ending_timer = 0.0
            state.game_finished = True
            sounds.start_ending_music()
            return

    if near_exit():
        if state.day == 3:
            if selected_item() == "Clef":
                state.inventory_slots[state.selected_inventory] = None
                sounds.play_sound("door")
                next_day()
            else:
                show_message("La porte est verrouillée. Sélectionne la clef et fais un clic droit.", 3.5)
        else:
            check_exit()
        return

    if state.day == 2:
        shredder_dist = distance(state.player_x, state.player_y, SHREDDER_X, SHREDDER_Y)
        if shredder_dist < 1.2:
            if state.shredder_cooldown > 0:
                show_message("Le broyeur est en cours d'utilisation...", 1.5)
                return
            shredded_any = False
            for i in range(len(state.inventory_slots)):
                if state.inventory_slots[i] == "Tableau":
                    state.inventory_slots[i] = None
                    for p in state.paintings:
                        if p["gone"] and not p["shredded"]:
                            p["shredded"] = True
                            shredded_any = True
                            break
            if shredded_any:
                remaining = sum(1 for p in state.paintings if not p["shredded"])
                if remaining == 0:
                    show_message("Tous les tableaux sont détruits. Va à la sortie !", 4.5)
                else:
                    show_message(f"Tableaux broyés. Il en reste {remaining} à détruire.", 3.0)
                state.shredder_cooldown = 3.0
                sounds.play_sound("shredder")
            else:
                show_message("Tu n'as pas de tableau a broyer.", 2.0)
            return

        for p in state.paintings:
            if not p["gone"] and distance(state.player_x, state.player_y, p["x"], p["y"]) < 1.25:
                p["gone"] = True
                for i in range(len(state.inventory_slots)):
                    if state.inventory_slots[i] is None:
                        state.inventory_slots[i] = "Tableau"
                        break
                remaining = sum(1 for item in state.paintings if not item["gone"])
                show_message(f"Tableau récupéré. Porte-le au broyeur ! ({remaining} restants)", 3.0)
                sounds.play_sound("pickup_item")
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
            show_message("Tu ouvres la porte avec la clef.", 3.0)
            state.inventory_slots[state.selected_inventory] = None
            sounds.play_sound("door")
            next_day()
        else:
            show_message("La porte est verrouillée. Essaye de la déverrouiller avec une clef.", 3.5)


def next_day():
    state.day += 1
    state.day_timer = DAY_LIMIT
    if state.day == 5:
        state.player_x = 2.0
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
    state.level_intro_timer = 0.0

    if state.day == 2:
        show_message("Jour 2 : Les tableaux sont corrompus. Jette-les avant de sortir.", 4.5)
    elif state.day == 3:
        show_message("Jour 3 : Trouve le code pour ouvrir le coffre. Indice : Lève la tête.", 5.0)
    elif state.day == 4:
        reset_cable_task()
        state.power_fixed = False
        state.monster_x = 12.5
        state.monster_y = 1.5
        show_message("Jour 4 : Le monstre a coupé le courant. Trouve le disjoncteur pour remettre le courant.", 4.5)
    elif state.day == 5:
        state.ending_timer = 0
        state.monster_x = 2.0
        state.monster_y = 1.0
        state.chase_timer = 3.0
        state.stamina = 100
        state.is_sprinting = False
        state.monster_visible = False
        state.monster_scream_played = False
        state.player_has_moved = False
        show_message("Jour 5 : cours jusqu'au fond du long couloir avant la fin du chrono.", 5.0)
    else:
        state.game_finished = True
        return

    state.transition_active = True
    state.transition_timer = 0.0
    sounds.start_level_music(state.day)


def check_exit():
    if not near_exit():
        return

    if state.day == 1:
        if state.j1_event_done:
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Quelque chose te retient. Attends...", 3.5)
    elif state.day == 2:
        if all(p["shredded"] for p in state.paintings):
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Broye tous les tableaux avant de partir.", 3.5)
    elif state.day == 3:
        if not state.stuck:
            show_message("Porte verrouillée. Trouve la clef, sélectionne-la, puis E.", 3.5)
    elif state.day == 4:
        if state.power_fixed:
            sounds.play_sound("door")
            next_day()
        else:
            show_message("Il faut réparer le courant avant de partir.", 3.5)
    elif state.day == 5:
        pass


def update_day_events(dt):
    if state.level_intro_timer > 0:
        state.level_intro_timer -= dt
        if state.level_intro_timer <= 0:
            state.level_intro_timer = 0
        return

    if state.transition_active:
        return

    update_lore(dt)
    if state.lore_active:
        return

    if state.shredder_cooldown > 0:
        state.shredder_cooldown -= dt

    if not state.ending_cinematic:
        state.day_timer -= dt
    if state.day_timer <= 0 and not state.ending_cinematic and state.player_health < 900:
        kill_player("Le temps est écoulé. Tu recommences depuis le début.")
        return

    if state.day == 1:
        if not state.j1_event_done:
            state.j1_timer -= dt
            if state.j1_timer <= 0:
                state.j1_event_done = True
                state.shake = 22
                show_message("BANG ! Un bruit soudain et impossible vient du plafond. Sors vite !", 5.0)
                sounds.play_sound("bang")
                sounds.play_sound("level1")

    if state.day == 3 and not state.stuck:
        for s in state.sink_spots:
            if not s["used"] and distance(state.player_x, state.player_y, s["x"], s["y"]) < 0.65:
                state.stuck = True
                state.stuck_clicks = 0
                state.sand_damage_timer = 0.0
                s["used"] = True
                show_message("Le sol t'aspire, appuie sur Espace pour t'en extraire !", 4.0)

    if state.day == 3 and state.stuck:
        state.sand_damage_timer += dt
        if state.sand_damage_timer >= 2.0:
            state.sand_damage_timer -= 2.0
            if state.player_health < 900:
                state.player_health -= 1
                show_message("Le sol t'étouffe. -1 PV", 2.5)
                if state.player_health <= 0:
                    kill_player("Tu as traversé le sol.")
                    return
            else:
                show_message("Le sol t'étouffe. (Admin)", 2.5)

    if state.day == 4 and not state.power_fixed:
        dx = state.player_x - state.monster_x
        dy = state.player_y - state.monster_y
        dist = math.sqrt(dx * dx + dy * dy)
        monster_angle = math.atan2(state.monster_y - state.player_y, state.monster_x - state.player_x)
        seen = abs(angle_diff(monster_angle, state.player_a)) < (FOV / 2.2) and dist < 9

        if dist > 0.2:
            old_mx, old_my = state.monster_x, state.monster_y
            if seen:
                m_spd = 1.32 * dt
                state.monster_x -= dx / dist * m_spd
                state.monster_y -= dy / dist * m_spd
            else:
                m_spd = 0.6 * dt
                state.monster_x += dx / dist * m_spd
                state.monster_y += dy / dist * m_spd

            if wall_at(state.monster_x, state.monster_y):
                state.monster_x, state.monster_y = old_mx, old_my

        state.heartbeat = max(0, 6 - dist)

        if dist < 0.55 and state.player_health < 900:
            show_message("Le monstre t'a touché. Tu te réveilles au début du jour 4.", 4.5)
            if state.cable_panel_open:
                close_cable_panel()
            reset_cable_task()
            state.monster_x = 12.5
            state.monster_y = 1.5

    if state.day == 5 and not state.ending_cinematic:
        # Detect player starting to move
        if not state.player_has_moved:
            if state.player_y > 1.52 or state.player_x != 2.0:
                state.player_has_moved = True

        if state.player_has_moved:
            # Monster appears after 3 seconds
            if state.chase_timer > 0:
                state.chase_timer -= dt
                if state.chase_timer <= 0:
                    state.monster_visible = True
                    if not state.monster_scream_played:
                        sounds.play_sound("monster_scream")
                        state.monster_scream_played = True
                        sounds.start_chase_music()
                    show_message("Il est derrière toi ! Ne t'arrête pas !", 3.0)
                    state.shake = 12
            else:
                if state.monster_visible:
                    m_speed = MONSTER_SPEED * dt
                    dy = state.player_y - state.monster_y
                    dist = abs(dy)
                    if dist > 0.2:
                        state.monster_y += math.copysign(m_speed, dy)
                        if wall_at(state.monster_x, state.monster_y):
                            state.monster_y -= math.copysign(m_speed, dy)
                    state.heartbeat = max(0, 6 - dist)
                    if dist < 0.55 and state.player_health < 900:
                        kill_player("Le monstre t'a rattrapé. Tu recommences depuis le début.")
    if not state.ending_cinematic and state.day != 5:
        state.stamina = max(0, min(100, state.stamina + (-30 if state.is_sprinting else 18) * dt))
        if state.stamina <= 0:
            state.is_sprinting = False
