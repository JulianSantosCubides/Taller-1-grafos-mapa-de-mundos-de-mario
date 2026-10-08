import pygame
import sys
import math
from pathlib import Path

# Add comment for Jira but without Jira key

# Add comment for Jira with Jira key

pygame.init()

# --- CONFIG ---
WIDTH, HEIGHT = 1280, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mapa - Avatar animado + popups")
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 28)

# --- ARCHIVOS ---
MAP_FILE = "mapa.png"            # tu mapa cartoon
SPRITE_FILE = "sprite_niño.png"  # sprite sheet generado (3 cols x 4 rows)
# Opcional: imágenes por nodo (ejemplo: node_A.png). Si no existen, se usa placeholder.
NODE_IMAGE_FILES = {
    "A": "node_A.png",
    "B": "node_B.png",
    "C": "node_C.png",
}

# --- CARGA IMÁGENES con fallbacks ---
# Mapa -> escalamos al tamaño de ventana
if Path(MAP_FILE).exists():
    mapa = pygame.image.load(MAP_FILE).convert_alpha()
    mapa = pygame.transform.smoothscale(mapa, (WIDTH, HEIGHT))
else:
    mapa = pygame.Surface((WIDTH, HEIGHT))
    mapa.fill((120, 200, 120))

# Sprite sheet
if not Path(SPRITE_FILE).exists():
    raise FileNotFoundError(f"No encontré {SPRITE_FILE}. Pon el sprite sheet en la carpeta.")
sprite_sheet = pygame.image.load(SPRITE_FILE).convert_alpha()
sheet_w, sheet_h = sprite_sheet.get_width(), sprite_sheet.get_height()

# --- EXTRAER LOS 4 FRAMES ESTÁTICOS DEL SPRITE ---

cols = 4
rows = 1

sheet_w = sprite_sheet.get_width()
sheet_h = sprite_sheet.get_height()

frame_w = sheet_w // cols
frame_h = sheet_h  # solo una fila

frames = {"down": [], "left": [], "right": [], "up": []}
order = ["down", "left", "right", "up"]

for col, direction in enumerate(order):
    x = col * frame_w
    y = 0
    frame = sprite_sheet.subsurface(pygame.Rect(x, y, frame_w, frame_h)).copy()
    frames[direction].append(frame)  # solo un frame por dirección




def load_frames_custom(sheet, coords_dict):
    loaded = {}
    for direction, coords_list in coords_dict.items():
        loaded[direction] = []
        for (x, y, w, h) in coords_list:
            rect = pygame.Rect(x, y, w, h)
            frame = sheet.subsurface(rect).copy()
            loaded[direction].append(frame)
    return loaded

# Cargar frames reales
#frames = load_frames_custom(sprite_sheet, frames_coords)

# Tamaño al que quieres escalar al personaje (ajusta si lo quieres más grande/pequeño)
SCALE = 0.2   # 0.5 => 32x32 si el frame original es 64x64

# Escalar todos los frames después de cargarlos (una sola vez)
for direction in frames:
    for i in range(len(frames[direction])):
        frame = frames[direction][0]
        w, h = frame.get_size()
        frames[direction][i] = pygame.transform.scale(frame, (int(w * SCALE), int(h * SCALE)))

# Ahora que tenemos frames escalados, obtengo su tamaño real desde el primer frame
FRAME_W, FRAME_H = frames["down"][0].get_size()

# --- GRAFO: nodos con posiciones (en píxeles dentro de la ventana) ---
graph = {
    "A": {"pos": (200, 480), "edges": ["B"]},
    "B": {"pos": (600, 320), "edges": ["A", "C"]},
    "C": {"pos": (1000, 520), "edges": ["B"]},
}

# Pre-cargar imágenes de los nodos (o placeholder)
node_images = {}
for name, path in NODE_IMAGE_FILES.items():
    if Path(path).exists():
        img = pygame.image.load(path).convert_alpha()
        # escalamos a un tamaño razonable para el popup
        img = pygame.transform.smoothscale(img, (300, 200))
        node_images[name] = img
    else:
        node_images[name] = None  # usaremos placeholder

# --- PLAYER STATE ---
player_x, player_y = graph["A"]["pos"]
dir_key = "down"
anim_speed = 8.0  # frames per second for animation (smoother control)
frame_idx = 0.0
vel = 3.2

# Popup state
popup_open = False
popup_node = None

def distance(a, b):
    return math.dist(a, b)

def draw_edges(surface):
    for node, data in graph.items():
        x1, y1 = data["pos"]
        for neigh in data["edges"]:
            x2, y2 = graph[neigh]["pos"]
            pygame.draw.line(surface, (160, 110, 40), (x1, y1), (x2, y2), 10)

def draw_nodes(surface):
    for name, data in graph.items():
        x, y = data["pos"]
        # marcador circular
        pygame.draw.circle(surface, (255, 230, 120), (x, y), 18)
        pygame.draw.circle(surface, (120, 80, 20), (x, y), 20, 3)
        label = FONT.render(name, True, (0,0,0))
        surface.blit(label, (x - label.get_width()/2, y - 10 - label.get_height()))

def show_popup(surface, node_name):
    """Dibuja la ventana emergente centrada con la imagen/placeholder."""
    # cuadro semi-transparente
    popup_w, popup_h = 520, 340
    popup_surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
    popup_surf.fill((20, 20, 20, 220))  # fondo oscuro semitransparente

    # título
    title = FONT.render(f"Nodo: {node_name}", True, (255,255,255))
    popup_surf.blit(title, ((popup_w - title.get_width())//2, 10))

    # imagen del nodo si existe
    img = node_images.get(node_name)
    if img:
        img_rect = img.get_rect(center=(popup_w//2, 60 + img.get_height()//2))
        popup_surf.blit(img, img_rect)
    else:
        # placeholder: rect con icono
        ph_w, ph_h = 360, 200
        ph = pygame.Surface((ph_w, ph_h), pygame.SRCALPHA)
        ph.fill((240, 240, 240))
        pygame.draw.rect(ph, (200,200,200), ph.get_rect(), 4)
        # texto
        t = FONT.render("Imagen de nodo (placeholder)", True, (20,20,20))
        ph.blit(t, ((ph_w - t.get_width())//2, (ph_h - t.get_height())//2))
        popup_surf.blit(ph, ((popup_w - ph_w)//2, 50))

    # instrucciones
    info = FONT.render("Presiona ESC para cerrar", True, (200,200,200))
    popup_surf.blit(info, ((popup_w - info.get_width())//2, popup_h - 40))

    # centrar en pantalla
    x = (WIDTH - popup_w)//2
    y = (HEIGHT - popup_h)//2
    surface.blit(popup_surf, (x, y))

# --- TIMER helpers para animación basada en tiempo ---
last_time = pygame.time.get_ticks()

# --- MAIN LOOP ---
running = True
while running:
    dt_ms = CLOCK.tick(60)  # ms desde el último frame
    dt = dt_ms / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # si estamos encima de un nodo, abrimos popup
                for name, data in graph.items():
                    if distance((player_x, player_y), data["pos"]) < 36:
                        popup_open = True
                        popup_node = name
                        break
            elif event.key == pygame.K_ESCAPE:
                popup_open = False
                popup_node = None

    # si popup abierto, solo permitir cerrar (no mover)
    if not popup_open:
        keys = pygame.key.get_pressed()
        moving = False
        # permito combinaciones diagonales -> prioridad no excluyente
        if keys[pygame.K_UP]:
            player_y -= vel
            dir_key = "up"
            moving = True
        if keys[pygame.K_DOWN]:
            player_y += vel
            dir_key = "down"
            moving = True
        if keys[pygame.K_LEFT]:
            player_x -= vel
            dir_key = "left"
            moving = True
        if keys[pygame.K_RIGHT]:
            player_x += vel
            dir_key = "right"
            moving = True

        # ANIMACIÓN: actualizamos frame_idx en función del tiempo y fps deseado (anim_speed)
        if moving:
            # anim_speed = frames per second
            frame_idx += anim_speed * dt
            # wrap usando la longitud real de la fila actual
            nframes = len(frames[dir_key])
            if frame_idx >= nframes:
                frame_idx = frame_idx % nframes
        else:
            # idle -> frame central (1) si existe, o 0 si no hay
            # frame_idx = 1.0 if len(frames[dir_key]) > 1 else 0.0
            frame_idx = 1.0

    # --- DIBUJO ---
    SCREEN.blit(mapa, (0, 0))

    # dibujar aristas y nodos
    draw_edges(SCREEN)
    draw_nodes(SCREEN)

    # avatar actual (usa el frame ya escalado; NO volver a escalar aquí)
    cur_frame = frames[dir_key][0]
    #sprite_rect = cur_frame.get_rect(midbottom=(int(player_x), int(player_y)))
    sprite_rect = cur_frame.get_rect(center=(int(player_x), int(player_y)))

    SCREEN.blit(cur_frame, sprite_rect.topleft)

    # instrucción rápida
    instr = FONT.render("Flechas: mover · ENTER: abrir nodo (si estás sobre uno) · ESC: cerrar popup", True, (20,20,20))
    SCREEN.blit(instr, (12, 12))

    # si estamos cerca de nodo, mostramos texto contextual
    for name, data in graph.items():
        if distance((player_x, player_y), data["pos"]) < 36:
            tip = FONT.render(f"Presiona ENTER para entrar a {name}", True, (10,10,10))
            SCREEN.blit(tip, (12, 44))
            break

    # popup encima de todo si está abierto
    if popup_open and popup_node:
        show_popup(SCREEN, popup_node)

    pygame.display.flip()

pygame.quit()
sys.exit()
