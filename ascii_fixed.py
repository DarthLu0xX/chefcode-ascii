#!/usr/bin/env python3
"""
Chef Code - ASCII Fijo
------------------------
Convierte una imagen en arte ASCII y opcionalmente la deja
fija en tu terminal (aparece cada vez que la abres).

Uso:
    python ascii_fixed.py mi_imagen.jpg
    python ascii_fixed.py mi_imagen.jpg --width 100 --color green
    python ascii_fixed.py mi_imagen.jpg --install
"""

import argparse
import os
import sys
import platform
from PIL import Image

# Caracteres usados para representar distintos niveles de brillo,
# de más "vacío" a más "denso"
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

POWERSHELL_COLOR_MAP = {
    "red": "Red",
    "green": "Green",
    "yellow": "Yellow",
    "blue": "Blue",
    "magenta": "Magenta",
    "cyan": "Cyan",
    "white": "White",
}


def image_to_ascii(image_path, width=100, invert=False):
    """Convierte una imagen a una lista de líneas ASCII."""
    try:
        img = Image.open(image_path).convert("L")  # escala de grises
    except FileNotFoundError:
        print(f"❌ No se encontró la imagen: {image_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al abrir la imagen: {e}")
        sys.exit(1)

    # Las celdas de texto son más altas que anchas, así que compensamos
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * width * 0.55)
    img = img.resize((width, max(new_height, 1)))

    pixels = list(img.getdata()) if hasattr(img, "getdata") else list(img.get_flattened_data())
    chars = ASCII_CHARS[::-1] if invert else ASCII_CHARS

    ascii_str = "".join(chars[pixel * (len(chars) - 1) // 255] for pixel in pixels)

    lines = [
        ascii_str[i : i + width] for i in range(0, len(ascii_str), width)
    ]
    return lines


def print_ascii(lines, color=None):
    if color and color in COLOR_CODES:
        for line in lines:
            print(COLOR_CODES[color] + line + COLOR_CODES["reset"])
    else:
        for line in lines:
            print(line)


def save_ascii_txt(lines, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Arte ASCII guardado en: {output_path}")


def install_permanent(lines, color):
    """Agrega el arte ASCII al perfil de PowerShell para que
    aparezca cada vez que se abra la terminal (solo Windows)."""

    if platform.system() != "Windows":
        print("⚠️  La instalación automática solo está soportada en Windows (PowerShell).")
        print("    Puedes copiar manualmente el archivo .txt generado a tu shell de preferencia.")
        return

    import subprocess

    try:
        result = subprocess.run(
            ["powershell", "-Command", "echo $PROFILE"],
            capture_output=True, text=True, check=True
        )
        profile_path = result.stdout.strip()
    except Exception as e:
        print(f"❌ No se pudo obtener la ruta de $PROFILE: {e}")
        return

    profile_dir = os.path.dirname(profile_path)
    os.makedirs(profile_dir, exist_ok=True)

    ps_color = POWERSHELL_COLOR_MAP.get(color, "White")

    marker_start = "# >>> chefcode-ascii-fixed >>>"
    marker_end = "# <<< chefcode-ascii-fixed <<<"

    block_lines = [marker_start]
    for line in lines:
        safe_line = line.replace('"', '`"')
        block_lines.append(f'Write-Host "{safe_line}" -ForegroundColor {ps_color}')
    block_lines.append('Write-Host ""')
    block_lines.append('Write-Host "Chef Code 🍳 - Nuevas ideas cocinandose..." -ForegroundColor White')
    block_lines.append(marker_end)
    block = "\n".join(block_lines)

    existing = ""
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            existing = f.read()

    # Si ya se había instalado antes, lo reemplazamos en vez de duplicarlo
    if marker_start in existing and marker_end in existing:
        before = existing.split(marker_start)[0]
        after = existing.split(marker_end)[1]
        new_content = before + block + after
    else:
        new_content = existing + "\n\n" + block + "\n"

    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Instalado en tu perfil de PowerShell: {profile_path}")
    print("🔄 Cierra y vuelve a abrir la terminal para verlo.")


def main():
    parser = argparse.ArgumentParser(
        description="Chef Code - Convierte una imagen en arte ASCII para tu terminal"
    )
    parser.add_argument("image", help="Ruta a la imagen (jpg, png, etc.)")
    parser.add_argument("--width", type=int, default=100, help="Ancho del arte ASCII en caracteres (default: 100)")
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros")
    parser.add_argument("--install", action="store_true", help="Deja el arte fijo en tu terminal (PowerShell)")
    parser.add_argument("--save", metavar="ARCHIVO.txt", help="Guarda el resultado como archivo de texto")

    args = parser.parse_args()

    print("👨‍🍳 Cocinando tu arte ASCII...\n")
    lines = image_to_ascii(args.image, width=args.width, invert=args.invert)
    print_ascii(lines, color=args.color)

    if args.save:
        save_ascii_txt(lines, args.save)

    if args.install:
        install_permanent(lines, args.color or "white")


if __name__ == "__main__":
    main()
