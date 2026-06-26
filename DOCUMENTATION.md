# Documentation du Projet — Backroom : One Minute to Escape

---

## Présentation du projet

### Nom du jeu

**Backroom : One Minute to Escape**

### Description

*Backroom : One Minute to Escape* est un jeu d'horreur pseudo-3D développé avec Pygame. Le joueur incarne une personne piégée dans un appartement situé dans les Backrooms, un univers liminal et oppressant. Il dispose de 60 secondes par jour pour survivre, accomplir des objectifs et s'échapper avant que le temps ne s'écoule ou que le monstre ne l'attrape.

### Concept

Le jeu est structuré en **5 jours**. Chaque jour introduit un nouvel objectif, de nouveaux dangers et une progression dans l'histoire. Le joueur doit résoudre des énigmes, collecter des objets, interagir avec l'environnement et fuir un monstre de plus en plus agressif.

### Objectif du joueur

Survivre 5 jours en accomplissant les objectifs quotidiens pour s'échapper définitivement des Backrooms.

### Technologies utilisées

- **Langage** : Python 3.12+
- **Moteur graphique** : Pygame 2.5+
- **Calculs matriciels** : NumPy 2.0+
- **Audio** : Pygame mixer (fréquence 22050 Hz, mono, 16 bits)
- **Système d'exploitation** : Linux (développé sous), compatible Windows

### Auteurs

- Développeurs : Noah & Anthony
- Game Design : Mikael & Luaï
- Sound Design : Kerim
- Studio : Mossard Studio / Back-Room Studios

---

## Architecture du projet

### Organisation des dossiers

```
Back-Room/
├── assets/
│   ├── audio/          # Fichiers sonores (WAV, MP3)
│   ├── textures/       # Textures et sprites (PNG)
│   └── ui/             # Éléments d'interface (logo.png)
├── config.py           # Constantes et configuration globale
├── game.py             # Logique de jeu, interactions, niveaux
├── main.py             # Boucle principale et gestion des événements
├── render.py           # Moteur de rendu pseudo-3D et affichage
├── settings.py         # Gestion des paramètres (son, résolution)
├── settings.json       # Fichier de sauvegarde des paramètres
├── sounds.py           # Gestion de l'audio (effets, musique)
├── state.py            # État global du jeu (variables partagées)
├── requirements.txt    # Dépendances Python
├── DOCUMENTATION.md    # Ce fichier
└── .gitignore
```

### Rôle de chaque fichier Python

| Fichier | Rôle |
|---|---|
| `config.py` | Définit toutes les constantes du jeu : dimensions, vitesses, cartes, positions fixes, couleurs, polices globales. |
| `state.py` | Contient l'état mutable du jeu sous forme de variables globales partagées entre tous les modules. |
| `main.py` | Boucle principale (`while running`), initialisation Pygame, machine à états (`menu`, `playing`, `paused`, `dead`, etc.), gestion des entrées clavier/souris. |
| `game.py` | Logique métier : collisions, objectifs journaliers, interaction avec les objets, système de messages (lore), progression des niveaux, comportement du monstre. |
| `render.py` | Moteur de rendu : raycaster pseudo-3D, sprites, murs texturés, sol/plafond, UI, menus, effet VHS, transitions, écran de mort. |
| `sounds.py` | Chargement et lecture des effets sonores, gestion de la musique d'ambiance, musique de niveau, musique de poursuite. |
| `settings.py` | Chargement/sauvegarde des paramètres (volume, résolution, plein écran) dans `settings.json`. |

### Dépendances entre les fichiers

```
config.py  (pas de dépendances)
    ↑
state.py  (dépend de config.py)
    ↑
sounds.py  (dépend de state.py)
    ↑
game.py  (dépend de config.py, state.py, sounds.py)
    ↑
render.py  (dépend de config.py, state.py, game.py)
    ↑
settings.py  (dépend de config.py, sounds.py, render.py [import local])
    ↑
main.py  (dépend de tous les modules)
```

---

## Gameplay

### Le joueur

Le joueur se déplace dans un environnement en 2D vu à travers un moteur pseudo-3D (raycaster). Il est représenté par une position `(player_x, player_y)` et un angle `(player_a)`. Il peut regarder en haut et en bas (`look_pitch`).

### Contrôles

| Touche | Action |
|---|---|
| Z / W | Avancer |
| S | Reculer |
| Q / A | Strafe gauche |
| D | Strafe droite |
| Souris | Rotation et visée verticale |
| E | Interagir / Valider un message |
| Espace | Sauter un message / Se dégager du sable |
| Shift (gauche/droite) | Sprint (consomme de l'endurance) |
| Échap | Pause / Fermer un panneau / Retour au menu |
| Molette | Changer d'emplacement d'inventaire |
| Clic gauche | Utiliser un objet dans l'inventaire |
| Clic droit | Utiliser l'objet sélectionné |

### Déplacement

Le déplacement utilise un système de **bounding box** (rayon de collision de 0.22 tuiles). Les collisions sont vérifiées séparément sur les axes X et Y pour permettre le glissement le long des murs (wall sliding). La vitesse de marche est de **1.5 tuiles/s**, le sprint de **3.0 tuiles/s**.

L'**endurance** (stamina) est consommée pendant le sprint (30 unités/s) et se régénère au repos (18 unités/s). Elle n'est pas affichée au jour 5. Pendant le jour 5, le sprint est illimité.

### Le timer

Chaque jour dure **60 secondes** (`DAY_LIMIT`). Si le temps s'écoule, le joueur meurt immédiatement. Le timer est affiché en haut de l'écran, passant du jaune au rouge quand il reste moins de 10 secondes. Pendant l'affichage d'un message (lore), le timer est toujours actif.

### Objectifs par jour

| Jour | Objectif |
|---|---|
| **Jour 1** | Attendre le BANG (environ 4s), puis sortir par la porte. |
| **Jour 2** | Récupérer 3 tableaux « corrompus » dans l'appartement, les porter au broyeur (shredder), détruire les 3, puis sortir. |
| **Jour 3** | Lire le code sur le plafond du spawn (regarder en haut près du point de départ), entrer le code sur le coffre-fort, récupérer la clef, clic droit sur la porte de sortie. |
| **Jour 4** | Ouvrir le panneau électrique, connecter les 3 câbles (rouge → rouge, jaune → jaune, bleu → bleu) tout en évitant le monstre qui rôde. |
| **Jour 5** | Courir jusqu'au bout du long couloir (75 tuiles). Le monstre apparaît après 3 secondes et vous poursuit (vitesse 2,25 tuiles/s). |

### Interactions détaillées

#### Jour 2 — Tableaux et broyeur

- Les tableaux sont placés à 3 endroits dans l'appartement.
- Appuyer sur **E** à proximité les ramasse et les place dans l'inventaire.
- Le broyeur se trouve dans une pièce spécifique. Avec un tableau dans l'inventaire, appuyer sur **E** pour le détruire.
- Le broyeur a un **cooldown de 3 secondes**.
- Un son de broyage (`broyeur.wav`) est joué à chaque utilisation.

#### Jour 3 — Coffre-fort et code

- Le code à 3 chiffres est affiché au plafond quand le joueur regarde en haut près du spawn (`look_pitch >= 165`).
- Le code est généré aléatoirement entre 100 et 999.
- Le coffre s'ouvre avec la souris (cliquer sur les chiffres) ou le clavier (taper les chiffres, Entrée pour valider).
- Si l'inventaire est plein, la clef reste dans le coffre (`safe_unlocked = False`).

#### Jour 4 — Panneau électrique

- 3 câbles à connecter : **rouge**, **jaune**, **bleu**.
- Cliquer à gauche pour sélectionner un câble, puis à droite sur la prise de la même couleur.
- Si la couleur est fausse, la sélection est annulée.
- Le monstre se déplace dans le couloir : il **s'approche** quand le joueur le regarde, s'**éloigne** quand le joueur détourne le regard.

### Jour 5 (Level 5)

- Le joueur spawn dans un long corridor de 75 tuiles de long.
- La sortie est au fond (2.0 ; LENGTH − 1.5).
- Le monstre apparaît **3 secondes** après que le joueur a commencé à bouger.
- La musique de poursuite (`level5.wav` en boucle) démarre.
- Le monstre se déplace uniquement sur l'axe Y, à 2,25 tuiles/s. Le joueur doit sprinter.
- L'endurance est infinie (pas de drain de stamina).
- Au bout du couloir, appuyer sur **E** pour ouvrir la porte et déclencher la cinématique de fin.

### Game Over

La mort peut survenir dans plusieurs cas :

| Cause | Condition |
|---|---|
| Timer écoulé | `day_timer <= 0` |
| Asphyxié par le sable (Jour 3) | `player_health <= 0` (dégâts toutes les 2s) |
| Attrapé par le monstre (Jour 4) | Distance < 0.55 tuile |
| Rattrapé par le monstre (Jour 5) | Distance < 0.55 tuile |

Quand le joueur meurt :

1. **Cinématique de mort** (0,8s) : la caméra recule, le personnage est visible au sol, un vignettage rouge apparaît, du sang éclabousse, `monster_scream` est joué.
2. **Écran Game Over** : image `Player-Slumped.png` avec zoom lent (0,8 → 1,35), overlay rouge pulsé, texte "GAME OVER" avec effet glitch, message de la cause de la mort.
3. Boutons : **Rejouer** (recommence depuis le jour 1) ou **Menu principal**.

### Victoire

Quand le joueur ouvre la porte au jour 5 :

- `ending_cinematic = True`, musique de fin (`ending.wav`).
- Cinématique : fond jaune, lignes ondulées, texte qui défile :
  - "…" → "Tu ouvres les yeux." → "Les murs jaunes ne sont plus là." → "Bienvenue dans la Réalité." → "FIN"
- Générique défilant (crédits) avec les noms des contributeurs.
- Appuyer sur **Échap** pour revenir au menu principal.

### Messages (système Lore)

Les messages sont affichés via un système de **machine à états** :

1. `entering` : glissement vers le haut (0,35s)
2. `typing` : défilement des caractères un par un (45 caractères/s) avec son `tick`
3. `waiting` : attente (durée configurable), bouton "[E] Continuer" pulsé
4. `exiting` : glissement vers le bas (0,35s)

Le joueur peut passer le message avec **E** ou **Espace** à tout moment. Pendant l'affichage, les déplacements sont bloqués.

---

## Raycaster

### Principe général

Le moteur utilise un **raycasting DDA** (Digital Differential Analyzer). Pour chaque colonne de l'écran, un rayon est lancé depuis la position du joueur dans la direction correspondante. On parcourt une grille 2D jusqu'à rencontrer un mur, puis on calcule la distance et on affiche une colonne de texture.

### Détails du raycaster

- **Nombre de rayons** : 460 (`RAYS`), inférieur à la largeur d'écran (1920). Chaque rayon couvre plusieurs pixels.
- **Champ de vision** : 60° (`FOV = π/3`).
- **Profondeur maximale** : 18 tuiles (`MAX_DEPTH`).
- **Distance maximale de rendu des murs** : `MAX_DEPTH`. Au-delà, le mur est invisble.
- **Correction fish-eye** : `depth_corrected = depth × cos(ray_angle − player_angle)`. Chaque distance est projetée sur le vecteur de vue du joueur.

### Calcul des murs (DDA)

1. On calcule les distances initiales aux bords de la case actuelle (`side_dist_x`, `side_dist_y`).
2. On itère en avançant d'une case dans la direction du rayon, en choisissant à chaque étape l'axe avec la plus petite distance.
3. Quand on touche un mur (`1` dans la carte), on calcule la distance perpendiculaire.
4. `side = 0` pour un mur vertical (axe X), `side = 1` pour un mur horizontal (axe Y). Les murs horizontaux sont ombrés à 75 %.
5. La hauteur affichée du mur : `wall_h = HEIGHT / depth_corrected`.

### Textures

- Une texture unique (`Wall-Texture.png`) est appliquée à tous les murs.
- La texture est pré-découpée en colonnes (`TEX_COLS`) pour un accès rapide par numpy.
- Les indices de texture sont pré-calculés pour toutes les hauteurs de mur possibles (1 à `HEIGHT × 2`) dans `TEX_INDICES`.
- Le **shading** (ombrage) réduit la luminosité en fonction de la distance : `shade = max(0,12, 1 − depth/MAX_DEPTH × 0,92)`.
- En journée 4 sans électricité, l'ombrage est multiplié par `0,25` (obscurité).

### Performances

- Le raycaster utilise `numpy` pour les opérations matricielles (application des textures, shading). Les colonnes sont écrites directement dans le `surfarray.pixels3d` de Pygame.
- Les indices de texture sont pré-calculés au chargement dans `load_textures()`.
- `camera_z` est extrait de la boucle pour éviter `getattr` 460 fois par frame.
- `p_angle` est utilisé en variable locale plutôt que `state.player_a` pour éviter l'accès au module global.
- Le `dt` est capé à 0,05s (20 FPS minimum) pour éviter la spirale de la mort.

### Sprites

Les sprites sont dessinés en 2D par dessus le raycaster :

- Position projetée : `screen_x = WIDTH/2 + tan(delta) × WIDTH`.
- Taille : `sprite_h = HEIGHT / dist × size`.
- Le sprite est créé sur une surface Pygame avec transparence, puis découpé colonne par colonne en fonction du `depth_buffer` (depth testing).
- Types de sprites : fenêtres (météo dynamique), meubles (lampe, table, canapé, lit, frigo, commode), tableaux, coffre-fort, boîte électrique, broyeur, porte, monstre.

### Objets 3D (mort)

Pendant la cinématique de mort, le joueur et le monstre sont rendus en **3D cuboïde** via la fonction `make_cuboid_faces()`. Les cubes sont projetés en perspective, triés par distance (painter's algorithm), et dessinés avec un ombrage par face.

---

## Audio

### Système audio

Le son utilise le module `pygame.mixer` configuré en :
- Fréquence : 22050 Hz
- Format : 16 bits signé
- Canaux : 1 (mono)
- Buffer : 512 échantillons

### Musique

| Musique | Fichier | Déclencheur |
|---|---|---|
| Menu principal | `main_menu.wav` | Boucle infinie dans le menu |
| Niveau 1 | (aucune) | Le niveau 1 n'a pas de musique d'ambiance |
| Niveau 2 | `level2.wav` | Début du jour 2 (boucle) |
| Niveau 3 | `level3.wav` | Début du jour 3 (boucle) |
| Niveau 4 | `level4.wav` | Début du jour 4 (boucle) |
| Poursuite (Jour 5) | `level5.wav` | Quand le monstre devient visible au jour 5 (boucle) |
| Fin | `ending.wav` | Quand le joueur ouvre la porte au jour 5 |
| Ambiance | `ambient-music.wav` / `mongolian-secret.wav` | Lecture manuelle via le menu options (déblocable) |

### Effets sonores

Les effets sont chargés via `AUDIO_FILES` dans `sounds.py`. Si un fichier est absent, un son de synthèse de secours (`make_tone()`) est généré.

| Nom | Fichier | Usage |
|---|---|---|
| `click` | `click.wav` | Clics de菜单, validation |
| `bang` | `bang.wav` | Bruit d'impact (mort, événement jour 1) |
| `interact` | `interact.wav` | Interaction générique |
| `repair` | `repair.wav` | Réparation |
| `electricite` | `electricity.wav` | Connexion électrique réussie |
| `door` | `door-opening.wav` | Ouverture de porte |
| `clef` | `key-collect.wav` | Ramassage de clef |
| `foot` | `footsteps.wav` | Pas du joueur (boucle) |
| `ending` | `ending.wav` | Musique de fin |
| `main_menu` | `main_menu.wav` | Musique du menu |
| `monster_scream` | `monstre_cri.mp3` | Cri du monstre (mort, poursuite) |
| `pickup_item` | `pickup-item.wav` | Ramassage d'objet |
| `shredder` | `broyeur.wav` | Broyage de tableau |
| `level1` | `level1.wav` | Effet sonore unique au BANG du jour 1 |
| `tick` | `tick.wav` | Caractère du système lore (typewriter) |

Les pas utilisent un canal dédié (`foot_channel`) pour une lecture en boucle.

---

## Assets

### Textures

Dossier : `assets/textures/`

| Fichier | Rôle |
|---|---|
| `Wall-Texture.png` | Texture appliquée à tous les murs du raycaster |
| `Monster-Spritesheet.png` | Spritesheet 8 frames du monstre (animation) |
| `Monster-Sitting.png` | Image du monstre assis (écran de mort, jour 5) |
| `Player-Slumped.png` | Image du joueur effondré (écran Game Over) |

### Sons

Dossier : `assets/audio/`

| Fichier | Type | Rôle |
|---|---|---|
| `ambient-music.wav` | Musique | Piste d'ambiance optionnelle (menu options) |
| `broyeur.wav` | SFX | Bruit du broyeur de tableaux (3s) |
| `door-opening.wav` | SFX | Porte qui s'ouvre |
| `electricity.wav` | SFX | Connexion électrique |
| `ending.wav` | Musique | Musique de fin |
| `footsteps.wav` | SFX (boucle) | Bruit de pas |
| `key-collect.wav` | SFX | Ramassage de clef |
| `level1.wav` | SFX | Effet sonore unique du BANG (jour 1) |
| `level2.wav` | Musique | Musique du jour 2 |
| `level3.wav` | Musique | Musique du jour 3 |
| `level4.wav` | Musique | Musique du jour 4 |
| `level5.wav` | Musique | Musique de poursuite (jour 5) |
| `main_menu.wav` | Musique | Musique du menu principal |
| `mongolian-secret.wav` | Musique | Piste secrète (déblocable) |
| `monstre_cri.mp3` | SFX | Cri du monstre |
| `pickup-item.wav` | SFX | Ramassage d'objet |

### UI

Dossier : `assets/ui/`

| Fichier | Rôle |
|---|---|
| `logo.png` | Icône de la fenêtre et du jeu |

### Polices

Les polices sont chargées via `pygame.font.SysFont` :

| Variable | Police | Taille | Usage |
|---|---|---|---|
| `FONT` | Arial | 22 | Texte standard |
| `BIG` | Arial | 46, gras | Titres, messages importants |
| `SMALL` | Arial | 16 | Petits textes, légendes |

---

## Menus

### Menu principal

- Affiche une scène générée du couloir (jour 5) en arrière-plan.
- Effets : scanlines, poussière, flicker, titre avec halo lumineux et glitch aléatoire.
- Boutons : **Lancer la partie**, **Options**, **Quitter**.
- Animation de fondu à l'ouverture (1s).

### Options

- Volume des effets sonores (0–100 %), avec boutons +/−.
- Volume de la musique (0–100 %), avec boutons +/−.
- Piste musicale (visible seulement si `mongolian_unlocked` est vrai).
- Plein écran : OUI/NON.
- Résolution : cycle à travers 5 résolutions (1920×1080, 1280×720, 2560×1440, 1600×900, 1366×768).
- Bouton **Retour**.

Le menu Options est partagé entre le menu principal et le menu pause (état `prev_state`).

### Pause

- Capture l'écran de jeu, le réduit puis l'agrandit (effet flou).
- Boutons : **Reprendre**, **Options**, **Menu principal**.

### Écran de chargement

- Barre de progression avec messages aléatoires.
- Durée : 3 secondes (`LOADING_DURATION`). Passage possible avec **Espace**.

### Cinématique d'intro

- Texte qui apparaît en fondu : "You don't remember how you got here..." → "The only way out..." → "...is to survive."
- Effets : bruit visuel (static), glitch.
- Passage possible avec **Espace** ou **Entrée**. Durée maximale : 10 secondes.

### Transitions entre niveaux

- Fade noir (0,5s) → Texte du niveau + objectif (2s) → Fade d'ouverture (0,5s).
- Durée totale : 3 secondes.

### Game Over

- Image `Player-Slumped.png` avec zoom lent.
- Overlay rouge pulsé.
- Effet glitch (lignes horizontales aléatoires).
- Texte "GAME OVER" avec ombre et décalage glitch.
- Message de la cause de la mort.
- Boutons animés au survol : **Rejouer**, **Menu principal**.

### Menu Debug

Accessible en tapant `admin` pendant le jeu. Permet de :

- Se téléporter à n'importe quel jour.
- Ajouter une clef à l'inventaire.
- Se téléporter à la sortie.
- Activer/désactiver le mode Dieu (`player_health = 999`, timer infini).

### Cheat secret

Taper `mongolian` pendant le jeu débloque la piste musicale `mongolian-secret.wav` dans le menu Options.

---

## Optimisations

| Optimisation | Description |
|---|---|
| **Pré-calcul des indices de texture** | `TEX_INDICES` pré-calcule toutes les hauteurs de mur possibles (1 à HEIGHT×2) dans `load_textures()` |
| **Texture en colonnes** | `TEX_COLS` stocke chaque colonne de la texture pour un accès numpy direct |
| **Accès direct au framebuffer** | Écriture via `surfarray.pixels3d()` au lieu de `pygame.draw` |
| **Shading numpy vectorisé** | Application de l'ombrage via multiplication matricielle numpy |
| **Variable locale dans le raycaster** | `camera_z` et `p_angle` extraits de la boucle pour éviter les accès module |
| **Capping du dt** | `dt = min(clock.tick(FPS_CAP) / 1000, 0.05)` pour éviter la spirale de la mort |
| **Cache des surfaces de rendu** | `_BODY_OVERLAY`, `_SHADE_PANEL`, `_PAUSE_BG`, `_MENU_BG`, `_VHS_SCANLINES` créés une seule fois et réutilisés |
| **Pré-calcul des textures fallback** | En cas d'échec de chargement, la texture de secours est aussi pré-découpée en colonnes |
| **Nettoyage régulier** | Variables inutilisées et imports morts supprimés du projet |

---

## Dépendances

Le projet nécessite Python 3.12+ et les bibliothèques suivantes :

```
numpy>=2.0
pygame>=2.0
```

---

## Installation

### Depuis les sources

```bash
# Cloner le dépôt
git clone https://github.com/votre-compte/Back-Room.git
cd Back-Room

# Créer un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate   # Linux
# ou venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le jeu
python3 main.py
```

### Créer un exécutable

#### Linux (avec PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Backroom" main.py
# L'exécutable sera dans dist/Backroom
```

#### Windows (avec PyInstaller)

```batch
pip install pyinstaller
pyinstaller --onefile --windowed --name "Backroom.exe" --add-data "assets;assets" main.py
REM L'exécutable sera dans dist/Backroom.exe
```

> Note : L'option `--add-data "assets;assets"` est nécessaire pour inclure les textures, sons et UI. Sur Linux, utiliser `--add-data "assets:assets"`.

### Configuration minimale

- **OS** : Linux / Windows
- **Python** : 3.12 ou supérieur
- **RAM** : 512 Mo minimum
- **Processeur** : 2 cœurs, 2 GHz
- **Carte graphique** : Compatible OpenGL (pour l'accélération Pygame)
- **Espace disque** : 200 Mo

---

## Git

### Récupérer le projet

```bash
git clone https://github.com/votre-compte/Back-Room.git
cd Back-Room
```

### Lancer le jeu

```bash
python3 main.py
```

### Contribuer

1. Créer une branche : `git checkout -b feature/ma-feature`
2. Coder et tester
3. Compiler le projet : `python3 -m py_compile *.py`
4. Commit : `git commit -m "Description des changements"`
5. Push : `git push origin feature/ma-feature`
6. Créer une Pull Request sur GitHub

#### Règles de contribution

- Ne pas casser le gameplay existant.
- Tester tous les niveaux avant de soumettre.
- Ne pas ajouter de dépendances inutiles.
- Documenter toute nouvelle fonctionnalité.
- Privilégier la stabilité à la performance.

---

## Améliorations possibles

### Graphismes

- Ajout de textures différenciées par type de mur.
- Système d'éclairage dynamique (ombres portées).
- Effet de brouillard volumétrique.
- Particules supplémentaires (poussière, fumée).
- Animations de sprites plus fluides (interpolation).

### Audio

- Plus de variations pour les bruits de pas (sol, sable).
- Sons ambiants procéduraux (grincements, chuchotements).
- Spatialisation sonore (volume basé sur la distance).
- Mixage et mastering professionnels.

### Gameplay

- Nouveaux niveaux (au-delà du jour 5).
- Objets utilisables supplémentaires.
- Énigmes plus variées.
- Système de sauvegarde.
- Difficulté progressive (timer plus court, monstre plus rapide).
- Mode sans fin (endless).

### Technique

- Portage vers un véritable moteur 3D (OpenGL/DirectX) via Ursina, Panda3D ou Godot.
- Multijoueur (coopération ou compétition).
- Version web (WebAssembly/Pyodide).
- Support des manettes (joystick/gamepad).
- Optimisation du raycaster (multithreading, GPU via compute shaders).

### Interface

- Sous-titres pour les messages.
- Carte du niveau (minimap).
- Journal de bord (objectifs complétés).
- Animations des icônes d'inventaire.
- Support de plusieurs langues (anglais, français).

### Accessibilité

- Option de réduction des effets visuels (VHS, glitch, flicker).
- Option de daltonisme.
- Réglage de la sensibilité de la souris.
- Réglage du FOV.
- Sous-titres pour les sons importants.

---

*Documentation générée le 26 juin 2026 — Version 1.0*
