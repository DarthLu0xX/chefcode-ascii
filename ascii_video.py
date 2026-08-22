#!/usr/bin/env python3
"""
Chef Code - ASCII Video
------------------------
Convierte un video o GIF en una animación ASCII que se reproduce
en bucle directo en tu terminal. Presiona Ctrl + C para detenerla.

Uso:
    python ascii_video.py mi_video.mp4
    python ascii_video.py mi_video.gif --width 80 --fps 12
    python ascii_video.py mi_video.mp4 --color cyan --once
"""

import argparse
import os
import sys
import time
import shutil

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
    resized = cv2.resize(gray, (width, new_height))

    chars = ASCII_CHARS[::-1] if invert else ASCII_CHARS
    normalized = (resized.astype(np.float32) / 255) * (len(chars) - 1)
    indices = normalized.astype(np.uint8)

    lines = []
    for row in indices:
        line = "".join(chars[i] for i in row)
        lines.append(line)
    return "\n".join(lines)


def extract_frames(video_path, width, invert, max_frames=None):
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


def play_ascii(frames, fps, color=None, loop=True):
    color_code = COLOR_CODES.get(color, "") if color else ""
    reset = COLOR_CODES["reset"] if color else ""
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


def main():
    parser = argparse.ArgumentParser(
        description="Chef Code - Reproduce un video como animación ASCII en tu terminal"
    )
    parser.add_argument("video", help="Ruta al video o GIF (mp4, gif, mov, etc.)")
    parser.add_argument("--width", type=int, default=80, help="Ancho del arte ASCII en caracteres (default: 80)")
    parser.add_argument("--fps", type=int, default=15, help="Fotogramas por segundo de reproducción (default: 15)")
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros")
    parser.add_argument("--once", action="store_true", help="Reproduce una sola vez en vez de en bucle")
    parser.add_argument("--max-frames", type=int, default=None, help="Límite de fotogramas a procesar (útil para videos largos)")

    args = parser.parse_args()

    frames, source_fps = extract_frames(
        args.video, args.width, args.invert, max_frames=args.max_frames
    )

    print("▶️  Reproduciendo... (Ctrl + C para detener)\n")
    time.sleep(1)

    play_ascii(frames, fps=args.fps, color=args.color, loop=not args.once)


if __name__ == "__main__":
    main()
