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

import cv2
import numpy as np

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

    print("👨‍🍳 Cocinando los fotogramas, un momento...")

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

    print(f"✅ {len(frames)} fotogramas listos.\n")
    return frames, source_fps


def play_ascii(frames, fps, color=None, loop=True, truecolor=False):
    color_code = COLOR_CODES.get(color, "") if (color and not truecolor) else ""
    reset = COLOR_CODES["reset"] if (color and not truecolor) else ""
    delay = 1.0 / max(fps, 1)

    try:
        print(HIDE_CURSOR, end="")
        while True:
            for frame in frames:
                print(CLEAR_SCREEN + color_code + frame + reset, end="", flush=True)
                time.sleep(delay)
            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        print(SHOW_CURSOR, end="")
        print("\n🍳 Chef Code - ¡Hasta la próxima receta!")


def install_permanent(video_path, width, fps, truecolor=False, feather=False, color=None):
    """Agrega al perfil de PowerShell el comando para reproducir esta
    animación cada vez que se abra la terminal (solo Windows). A
    diferencia de una imagen fija, esto vuelve a correr Python en cada
    apertura de terminal, así que necesitas Python + las dependencias
    de este proyecto instaladas."""

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

    cmd_parts = [
        f'& "{sys.executable}"',
        f'"{script_path}"',
        f'"{video_abspath}"',
        f"--width {width}",
        f"--fps {fps}",
        "--once",
    ]
    if truecolor:
        cmd_parts.append("--truecolor")
    if feather:
        cmd_parts.append("--feather")
    if color:
        cmd_parts.append(f"--color {color}")

    block = "\n".join([marker_start, " ".join(cmd_parts), marker_end])

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
    print("🔄 Cierra y vuelve a abrir la terminal para verlo (se reproduce una vez, con --once).")
    print("⚠️  Esto ejecuta Python cada vez que abres la terminal — necesitas Python y las")
    print("    dependencias de este proyecto (requirements.txt) instaladas en esta máquina.")


def main():
    parser = argparse.ArgumentParser(
        description="Chef Code - Reproduce un video como animación ASCII en tu terminal"
    )
    parser.add_argument("video", help="Ruta al video o GIF (mp4, gif, mov, etc.)")
    parser.add_argument("--width", type=int, default=80, help="Ancho del arte ASCII en caracteres (default: 80)")
    parser.add_argument("--fps", type=int, default=15, help="Fotogramas por segundo de reproducción (default: 15)")
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto (ignorado con --truecolor)")
    parser.add_argument("--truecolor", action="store_true", help="Usa bloques a color real (24-bit) en vez de ASCII por brillo, igual que en fixed/ascii_fixed.py.")
    parser.add_argument("--feather", action="store_true", help="Degrada los bordes de cada fotograma hacia el color de fondo (solo con --truecolor).")
    parser.add_argument("--bg-color", default="0,0,0", help="Color de fondo de tu terminal como 'R,G,B' (default: 0,0,0), usado por --feather.")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros (ignorado con --truecolor)")
    parser.add_argument("--once", action="store_true", help="Reproduce una sola vez en vez de en bucle")
    parser.add_argument("--max-frames", type=int, default=None, help="Límite de fotogramas a procesar (útil para videos largos)")
    parser.add_argument("--install", action="store_true", help="Deja el video instalado para que se reproduzca al abrir la terminal (PowerShell)")

    args = parser.parse_args()
    bg_color = tuple(int(c.strip()) for c in args.bg_color.split(","))

    frames, source_fps = extract_frames(
        args.video, args.width, args.invert, max_frames=args.max_frames,
        truecolor=args.truecolor, feather=args.feather, bg_color=bg_color,
    )

    print("▶️  Reproduciendo... (Ctrl + C para detener)\n")
    time.sleep(1)

    play_ascii(frames, fps=args.fps, color=args.color, loop=not args.once, truecolor=args.truecolor)

    if args.install:
        install_permanent(args.video, args.width, args.fps, truecolor=args.truecolor, feather=args.feather, color=args.color)


if __name__ == "__main__":
    main()
