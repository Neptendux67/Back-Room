from config import DAY_LIMIT, MAX_HEALTH

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
    {"x": 4.5, "y": 1.5, "gone": False, "shredded": False},
    {"x": 11.5, "y": 3.5, "gone": False, "shredded": False},
    {"x": 2.5, "y": 5.5, "gone": False, "shredded": False},
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
ending_cinematic = False
death_message = ""
debug_input = ""
debug_menu_open = False
chase_timer = 0.0
pause_submenu = None
prev_state = None
stamina = 100
is_sprinting = False
monster_visible = False
monster_scream_played = False
player_has_moved = False
death_cinematic = False
death_timer = 0.0
death_pos_x = 0.0
death_pos_y = 0.0
death_pos_a = 0.0
camera_z = 0.0


