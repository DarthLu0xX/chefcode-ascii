#!/usr/bin/env python3
"""
Chef Code - Menú interactivo
------------------------------
Te pregunta qué quieres cargar (foto o video), te enseña una vista
previa de cómo quedaría en tu terminal, y solo si te gusta lo deja
guardado para que aparezca cada vez que la abras.

Uso:
    python chefcode.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixed"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "video"))

import ascii_fixed
import ascii_video


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    resp = input(f"{prompt}{suffix}: ").strip()
    return resp if resp else default


def ask_path(prompt):
    path = ask(prompt)
    while not path or not os.path.exists(path):
        path = ask("No encontré esa ruta, intenta de nuevo")
    return path


def ask_yes_no(prompt, default=True):
    hint = "S/n" if default else "s/N"
    resp = input(f"{prompt} ({hint}): ").strip().lower()
    if not resp:
        return default
    return resp.startswith("s")


def ask_int(prompt, default):
    resp = ask(prompt, str(default))
    try:
        return int(resp)
    except ValueError:
        return default


def run_photo():
    path = ask_path("📷 Ruta de tu imagen (jpg, png...)")

    print("\n¿Cómo la quieres renderizar?")
    print("  1) Bloques de color (texto) — funciona en casi cualquier terminal")
    print("  2) Sixel (imagen real, pixel por pixel) — sin escalones, pero experimental (Windows Terminal 1.22+)")
    mode = ask("Elige una opción", "1")

    if mode.strip() == "2":
        width = ask_int("Ancho en píxeles reales", 300)
        data = ascii_fixed.image_to_sixel(path, width=width)
        print()
        ascii_fixed.print_sixel(data)
        print()
        print("¿Se ve la foto de verdad, sin escalones? Si en vez de eso ves texto raro/basura,")
        print("tu terminal no soporta Sixel — responde 'n' abajo y usa la opción 1.")
        if ask_yes_no("¿Se ve bien? ¿Lo dejo fijo en tu terminal?", True):
            ascii_fixed.install_permanent([data], "white", truecolor=True)
        else:
            print("Ok, no se guardó nada. Puedes correr 'python chefcode.py' de nuevo cuando quieras.")
        return

    width = ask_int("Ancho del arte en caracteres", 60)
    feather = ask_yes_no("¿Degradar los bordes hacia el fondo?", True)

    lines = ascii_fixed.image_to_ansi_truecolor(path, width=width, feather=feather, bg_color=(0, 0, 0))
    print()
    ascii_fixed.print_truecolor(lines)
    print()

    if ask_yes_no("¿Se ve bien? ¿Lo dejo fijo en tu terminal?", True):
        ascii_fixed.install_permanent(lines, "white", truecolor=True)
    else:
        print("Ok, no se guardó nada. Puedes correr 'python chefcode.py' de nuevo cuando quieras.")


def run_video():
    path = ask_path("🎬 Ruta de tu video o GIF")

    print("\n¿Cómo lo quieres renderizar?")
    print("  1) Bloques de color (texto) — funciona en casi cualquier terminal")
    print("  2) Sixel (imagen real, pixel por pixel) — sin escalones, respeta transparencia de GIF, pero experimental (Windows Terminal 1.22+) y más lento de procesar")
    mode = ask("Elige una opción", "1")
    use_sixel = mode.strip() == "2"

    width = ask_int("Ancho en píxeles reales" if use_sixel else "Ancho del arte en caracteres", 300 if use_sixel else 70)
    max_frames_raw = ask("Límite de fotogramas a procesar (Enter = sin límite, recomendado para clips cortos)", "")
    max_frames = int(max_frames_raw) if max_frames_raw else None

    if use_sixel:
        frames, source_fps = ascii_video.extract_frames_sixel(path, width, max_frames=max_frames)
        fps = ask_int("FPS de reproducción", round(source_fps) or 15)
        print("\n▶️  Vista previa (una sola vuelta, Ctrl + C para saltarla)...\n")
        print("Si ves texto/códigos raros en vez de la animación, tu terminal no soporta Sixel.\n")
        ascii_video.play_ascii(frames, fps=fps, loop=False, sixel=True)
    else:
        feather = ask_yes_no("¿Degradar los bordes hacia el fondo?", True)
        fps = ask_int("FPS de reproducción", 15)
        frames, _ = ascii_video.extract_frames(
            path, width, invert=False, max_frames=max_frames,
            truecolor=True, feather=feather, bg_color=(0, 0, 0),
        )
        print("\n▶️  Vista previa (una sola vuelta, Ctrl + C para saltarla)...\n")
        ascii_video.play_ascii(frames, fps=fps, loop=False, truecolor=True)

    if ask_yes_no("¿Se ve bien? ¿Lo dejo para que se reproduzca al abrir la terminal?", True):
        once = not ask_yes_no("¿En bucle infinito (como si estuviera 'vivo')? Si dices que sí, la terminal no queda usable hasta que presiones Ctrl+C", False)
        if use_sixel:
            ascii_video.install_permanent(path, width, fps, sixel=True, once=once)
        else:
            ascii_video.install_permanent(path, width, fps, truecolor=True, feather=feather, once=once)
    else:
        print("Ok, no se guardó nada. Puedes correr 'python chefcode.py' de nuevo cuando quieras.")


def main():
    print("🍳 Chef Code - ASCII\n")
    print("¿Qué quieres cargar?")
    print("  1) Foto (fija)")
    print("  2) Video / GIF (animado)")

    choice = ask("Elige una opción", "1")

    if choice.strip() == "2":
        run_video()
    else:
        run_photo()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOk, cancelado. No se guardó nada.")
