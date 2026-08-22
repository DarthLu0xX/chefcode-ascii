#!/usr/bin/env python3
"""
Chef Code - ASCII Video
------------------------
Convierte un video o GIF en una animación ASCII que se reproduce
en bucle directo en tu terminal. Presiona Ctrl + C para detenerla.

Uso:
    python ascii_video.py mi_video.mp4
    python ascii_video.py mi_video.gif --width 80 --fps 12
    python ascii_video.py mi_video.mp4 --truecolor --feather --once
    python ascii_video.py mi_video.mp4 --truecolor --install
"""

import argparse
import os
import sys
import time
import platform
import shutil

import cv2
import numpy as np
from PIL import Image, ImageSequence

ASCII_CHARS = "@%#*+=-:. "

COLOR_CODES = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "reset": "\033[0m",
}

CLEAR_SCREEN = "\033[H\033[J"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
# "Salida sincronizada" (modo DEC 2026): le pide a la terminal que
# junte todo lo que se imprima entre estos dos códigos y lo muestre de
# golpe, en vez de ir pintando a medida que llega. Evita el parpadeo
# de borrar+redibujar sin dejar fotogramas fantasma pegados. Windows
# Terminal reciente lo soporta; si no lo soporta, simplemente lo
# ignora sin romper nada.
SYNC_BEGIN = "\033[?2026h"
SYNC_END = "\033[?2026l"


def frame_to_ascii(frame, width, invert=False):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    aspect_ratio = h / w
    new_height = max(int(aspect_ratio * width * 0.55), 1)
    resized = cv2.resize(gray, (width, new_height), interpolation=cv2.INTER_AREA)

    chars = ASCII_CHARS[::-1] if invert else ASCII_CHARS
    normalized = (resized.astype(np.float32) / 255) * (len(chars) - 1)
    indices = normalized.astype(np.uint8)

    lines = []
    for row in indices:
        line = "".join(chars[i] for i in row)
        lines.append(line)
    return "\n".join(lines)


def _smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def frame_to_ansi_truecolor(frame, width, feather=False, bg_color=(0, 0, 0)):
    """Convierte un fotograma a un frame de bloques semi-carácter (▀) a
    color verdadero (24-bit), igual que el modo --truecolor de las
    fotos. Usa cv2.INTER_AREA para un downscale limpio (sin bloques)."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    aspect_ratio = h / w
    out_height = int(round(width * aspect_ratio))
    out_height = max(out_height + (out_height % 2), 2)
    resized = cv2.resize(rgb, (width, out_height), interpolation=cv2.INTER_AREA).astype(np.float32)

    if feather:
        ys, xs = np.mgrid[0:out_height, 0:width]
        cx, cy = (width - 1) / 2, (out_height - 1) / 2
        u = (xs - cx) / (width / 2)
        v = (ys - cy) / (out_height / 2)
        r = np.sqrt(u * u + v * v)
        alpha = (1.0 - _smoothstep(0.72, 1.05, r))[..., None]
        bg = np.array(bg_color, dtype=np.float32)
        resized = resized * alpha + bg * (1 - alpha)

    resized = np.clip(resized, 0, 255).astype(np.uint8)
    px = resized.tolist()

    lines = []
    for y in range(0, out_height, 2):
        row_top = px[y]
        row_bot = px[y + 1]
        parts = []
        for (r1, g1, b1), (r2, g2, b2) in zip(row_top, row_bot):
            parts.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
        parts.append("\033[0m")
        lines.append("".join(parts))
    return "\n".join(lines)


def _pil_frame_to_sixel(img, width=None, max_colors=256, alpha_threshold=128):
    """Igual que image_to_sixel de fixed/ascii_fixed.py pero recibe un
    Image de Pillow ya cargado (un fotograma), en vez de una ruta."""
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA") if has_alpha else img.convert("RGB")

    if width:
        aspect = img.height / img.width
        new_h = max(int(round(width * aspect)), 1)
        img = img.resize((width, new_h), Image.LANCZOS)

    w, h = img.size
    rgb = img.convert("RGB")
    alpha_px = img.split()[-1].load() if has_alpha else None

    pal_img = rgb.convert("P", palette=Image.ADAPTIVE, colors=max_colors)
    palette = pal_img.getpalette()
    pal_px = pal_img.load()

    out = ["\x1bP0;1;0q", f'"1;1;{w};{h}']
    for i in range(len(palette) // 3):
        r, g, b = palette[i * 3: i * 3 + 3]
        out.append(f"#{i};2;{round(r * 100 / 255)};{round(g * 100 / 255)};{round(b * 100 / 255)}")

    for band_start in range(0, h, 6):
        band_rows = min(6, h - band_start)
        color_cols = {}
        for x in range(w):
            for r in range(band_rows):
                y = band_start + r
                if alpha_px and alpha_px[x, y] < alpha_threshold:
                    continue
                c = pal_px[x, y]
                bits = color_cols.setdefault(c, [0] * w)
                bits[x] |= 1 << r

        first = True
        for c in sorted(color_cols):
            if not first:
                out.append("$")
            first = False
            out.append(f"#{c}")
            bits = color_cols[c]
            i = 0
            while i < w:
                b = bits[i]
                run = 1
                while i + run < w and bits[i + run] == b:
                    run += 1
                ch = chr(0x3F + b)
                out.append(f"!{run}{ch}" if run > 3 else ch * run)
                i += run
        out.append("-")

    if out[-1] == "-":
        out.pop()
    out.append("\x1b\\")
    return "".join(out), w, h


def extract_frames_sixel(path, width, max_frames=None):
    """Extrae fotogramas y los codifica como Sixel (imagen real, sin
    escalones). Los GIF se leen con Pillow (respeta la transparencia
    real de cada fotograma, cosa que cv2 no hace); otros formatos de
    video se leen con cv2, igual que en extract_frames."""
    if not os.path.exists(path):
        print(f"❌ No se encontró el archivo: {path}")
        sys.exit(1)

    print("👨‍🍳 Cocinando los fotogramas, un momento...", flush=True)

    frames = []
    fps = 15
    img_size = None

    if os.path.splitext(path)[1].lower() == ".gif":
        gif = Image.open(path)
        durations = []
        count = 0
        for frame in ImageSequence.Iterator(gif):
            data, w, h = _pil_frame_to_sixel(frame.convert("RGBA"), width=width)
            frames.append(data)
            img_size = img_size or (w, h)
            durations.append(frame.info.get("duration", 100) or 100)
            count += 1
            if max_frames and count >= max_frames:
                break
        if durations:
            fps = 1000 / (sum(durations) / len(durations))
    else:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"❌ No se pudo abrir el video: {path}")
            sys.exit(1)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            data, w, h = _pil_frame_to_sixel(Image.fromarray(rgb), width=width)
            frames.append(data)
            img_size = img_size or (w, h)
            count += 1
            if max_frames and count >= max_frames:
                break
        cap.release()

    if not frames:
        print("❌ No se pudieron extraer fotogramas.")
        sys.exit(1)

    print(f"✅ {len(frames)} fotogramas listos.\n", flush=True)
    return frames, fps, img_size


def extract_frames(video_path, width, invert=False, max_frames=None,
                    truecolor=False, feather=False, bg_color=(0, 0, 0)):
    if not os.path.exists(video_path):
        print(f"❌ No se encontró el archivo: {video_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ No se pudo abrir el video: {video_path}")
        sys.exit(1)

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frames = []
    count = 0

    print("👨‍🍳 Cocinando los fotogramas, un momento...", flush=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if truecolor:
            frames.append(frame_to_ansi_truecolor(frame, width, feather=feather, bg_color=bg_color))
        else:
            frames.append(frame_to_ascii(frame, width, invert))
        count += 1
        if max_frames and count >= max_frames:
            break

    cap.release()

    if not frames:
        print("❌ No se pudieron extraer fotogramas del video.")
        sys.exit(1)

    print(f"✅ {len(frames)} fotogramas listos.\n", flush=True)
    return frames, source_fps


def _center_prefix(img_size, cell_size=(9, 18)):
    """Calcula espacios/saltos de línea para centrar una imagen de
    img_size píxeles dentro del panel actual. cell_size es una
    estimación del tamaño en píxeles de un carácter de tu fuente (no
    hay forma portable de saber el valor exacto) -- el centrado es
    aproximado, no perfecto."""
    if not img_size:
        return ""
    img_w, img_h = img_size
    cell_w, cell_h = cell_size
    cols, rows = shutil.get_terminal_size(fallback=(80, 24))
    pad_cols = max(0, int((cols - img_w / cell_w) / 2))
    pad_rows = max(0, int((rows - img_h / cell_h) / 2))
    return ("\n" * pad_rows) + (" " * pad_cols)


def play_ascii(frames, fps, color=None, loop=True, truecolor=False, sixel=False, img_size=None):
    plain = truecolor or sixel
    color_code = COLOR_CODES.get(color, "") if (color and not plain) else ""
    reset = COLOR_CODES["reset"] if (color and not plain) else ""
    delay = 1.0 / max(fps, 1)
    prefix = _center_prefix(img_size) if sixel else ""

    try:
        # Cada fotograma se borra y redibuja de nuevo (si no, los pixeles
        # transparentes que el personaje dejó de ocupar se quedan pegados
        # -- rastro fantasma). Envuelto en "salida sincronizada" para que
        # la terminal muestre el borrado+redibujado como un solo golpe,
        # sin el parpadeo de antes.
        print(HIDE_CURSOR, end="")
        while True:
            for frame in frames:
                print(SYNC_BEGIN + CLEAR_SCREEN + prefix + color_code + frame + reset + SYNC_END, end="", flush=True)
                time.sleep(delay)
            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        print(SHOW_CURSOR, end="")
        print("\n🍳 Chef Code - ¡Hasta la próxima receta!")


def install_permanent(video_path, width, fps, truecolor=False, feather=False, color=None,
                       sixel=False, once=True, split_pane=False, split_ratio=0.3):
    """Agrega al perfil de PowerShell el comando para reproducir esta
    animación cada vez que se abra la terminal (solo Windows). A
    diferencia de una imagen fija, esto vuelve a correr Python en cada
    apertura de terminal, así que necesitas Python + las dependencias
    de este proyecto instaladas.

    Si split_pane=True (pensado para --once=False, bucle infinito), la
    animación se abre en un panel nuevo de Windows Terminal en vez de
    ocupar la terminal principal — así puedes seguir escribiendo
    comandos en tu panel de siempre mientras el panel nuevo sigue
    reproduciendo en bucle."""

    if platform.system() != "Windows":
        print("⚠️  La instalación automática solo está soportada en Windows (PowerShell).")
        return

    import subprocess

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "echo $PROFILE"],
            capture_output=True, text=True, check=True
        )
        profile_path = result.stdout.strip()
    except Exception as e:
        print(f"❌ No se pudo obtener la ruta de $PROFILE: {e}")
        return

    profile_dir = os.path.dirname(profile_path)
    os.makedirs(profile_dir, exist_ok=True)

    script_path = os.path.abspath(__file__)
    video_abspath = os.path.abspath(video_path)

    marker_start = "# >>> chefcode-ascii-video >>>"
    marker_end = "# <<< chefcode-ascii-video <<<"

    py_args = [f'"{video_abspath}"', f"--width {width}", f"--fps {fps}"]
    if once:
        py_args.append("--once")
    if sixel:
        py_args.append("--sixel")
    elif truecolor:
        py_args.append("--truecolor")
        if feather:
            py_args.append("--feather")
        if color:
            py_args.append(f"--color {color}")

    if split_pane:
        # -w 0 apunta a la ventana de Windows Terminal actual (la que
        # llamó a este script) en vez de abrir una ventana nueva.
        command_line = (
            f"wt -w 0 split-pane -s {split_ratio} -V "
            f'"{sys.executable}" "{script_path}" ' + " ".join(py_args)
        )
    else:
        command_line = f'& "{sys.executable}" "{script_path}" ' + " ".join(py_args)

    block = "\n".join([marker_start, command_line, marker_end])

    existing = ""
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            existing = f.read()

    if marker_start in existing and marker_end in existing:
        before = existing.split(marker_start)[0]
        after = existing.split(marker_end)[1]
        new_content = before + block + after
    else:
        new_content = existing + "\n\n" + block + "\n"

    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Instalado en tu perfil de PowerShell: {profile_path}")
    if split_pane:
        print("🔄 Cierra y vuelve a abrir la terminal (en Windows Terminal) para verlo.")
        print("   Se abre en un panel nuevo, en bucle infinito — tu panel principal queda libre para trabajar.")
    elif once:
        print("🔄 Cierra y vuelve a abrir la terminal para verlo (se reproduce una vez, con --once).")
    else:
        print("🔄 Cierra y vuelve a abrir la terminal para verlo — se reproduce EN BUCLE INFINITO.")
        print("   La terminal no queda usable hasta que presiones Ctrl+C para detener la animación.")
    print("⚠️  Esto ejecuta Python cada vez que abres la terminal — necesitas Python y las")
    print("    dependencias de este proyecto (requirements.txt) instaladas en esta máquina.")


def main():
    parser = argparse.ArgumentParser(
        description="Chef Code - Reproduce un video como animación ASCII en tu terminal"
    )
    parser.add_argument("video", help="Ruta al video o GIF (mp4, gif, mov, etc.)")
    parser.add_argument("--width", type=int, default=None, help="Ancho en caracteres (modo texto) o en píxeles reales (--sixel). Default: 80 en modo texto, 300 con --sixel.")
    parser.add_argument("--fps", type=int, default=None, help="Fotogramas por segundo de reproducción (default: 15, o la velocidad real del GIF con --sixel si no se especifica)")
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto (ignorado con --truecolor/--sixel)")
    parser.add_argument("--truecolor", action="store_true", help="Usa bloques a color real (24-bit) en vez de ASCII por brillo, igual que en fixed/ascii_fixed.py.")
    parser.add_argument("--sixel", action="store_true", help="Dibuja cada fotograma como imagen real (protocolo Sixel), sin escalones. Respeta la transparencia real de los GIF. Experimental (Windows Terminal 1.22+). Ignora --truecolor/--color/--invert/--feather.")
    parser.add_argument("--feather", action="store_true", help="Degrada los bordes de cada fotograma hacia el color de fondo (solo con --truecolor).")
    parser.add_argument("--bg-color", default="0,0,0", help="Color de fondo de tu terminal como 'R,G,B' (default: 0,0,0), usado por --feather.")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros (ignorado con --truecolor/--sixel)")
    parser.add_argument("--once", action="store_true", help="Reproduce una sola vez en vez de en bucle")
    parser.add_argument("--max-frames", type=int, default=None, help="Límite de fotogramas a procesar (útil para videos largos)")
    parser.add_argument("--install", action="store_true", help="Deja el video instalado para que se reproduzca al abrir la terminal (PowerShell)")
    parser.add_argument("--split-pane", action="store_true", help="Con --install y bucle infinito (sin --once): abre la animación en un panel nuevo de Windows Terminal en vez de ocupar la terminal principal, para poder seguir trabajando mientras se reproduce.")
    parser.add_argument("--split-ratio", type=float, default=0.3, help="Fracción de la ventana que ocupa el panel nuevo con --split-pane (default: 0.3)")

    args = parser.parse_args()
    bg_color = tuple(int(c.strip()) for c in args.bg_color.split(","))
    if args.width is None:
        args.width = 300 if args.sixel else 80

    img_size = None
    if args.sixel:
        frames, source_fps, img_size = extract_frames_sixel(args.video, args.width, max_frames=args.max_frames)
    else:
        frames, source_fps = extract_frames(
            args.video, args.width, args.invert, max_frames=args.max_frames,
            truecolor=args.truecolor, feather=args.feather, bg_color=bg_color,
        )

    fps = args.fps or source_fps or 15

    # Con --install y bucle infinito, reproducir aquí primero bloquearía
    # este mismo proceso para siempre (nunca llegaría a instalar). Se
    # instala directo; para probar antes de instalar, usa --once.
    skip_preview = args.install and not args.once
    if not skip_preview:
        print("▶️  Reproduciendo... (Ctrl + C para detener)\n", flush=True)
        time.sleep(1)
        play_ascii(frames, fps=fps, color=args.color, loop=not args.once, truecolor=args.truecolor, sixel=args.sixel, img_size=img_size)

    if args.install:
        install_permanent(
            args.video, args.width, fps, truecolor=args.truecolor, feather=args.feather,
            color=args.color, sixel=args.sixel, once=args.once,
            split_pane=args.split_pane, split_ratio=args.split_ratio,
        )


if __name__ == "__main__":
    main()
