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


def _open_flattened(image_path, bg_color=(0, 0, 0)):
    """Abre una imagen y, si tiene transparencia (PNG recortado, etc.),
    la compone sobre bg_color en vez de simplemente descartar el canal
    alfa. Descartar el alfa deja basura de color en los píxeles del
    borde del recorte, que es lo que se ve como "ruido"/halo pixelado
    alrededor de la figura."""
    try:
        raw = Image.open(image_path)
    except FileNotFoundError:
        print(f"❌ No se encontró la imagen: {image_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al abrir la imagen: {e}")
        sys.exit(1)

    if raw.mode in ("RGBA", "LA") or (raw.mode == "P" and "transparency" in raw.info):
        raw = raw.convert("RGBA")
        background = Image.new("RGBA", raw.size, bg_color + (255,))
        raw = Image.alpha_composite(background, raw)

    return raw.convert("RGB")


def image_to_ascii(image_path, width=100, invert=False, bg_color=(0, 0, 0)):
    """Convierte una imagen a una lista de líneas ASCII."""
    img = _open_flattened(image_path, bg_color).convert("L")

    # Las celdas de texto son más altas que anchas, así que compensamos
    aspect_ratio = img.height / img.width
    new_height = int(aspect_ratio * width * 0.55)
    img = img.resize((width, max(new_height, 1)), Image.LANCZOS)

    pixels = list(img.getdata()) if hasattr(img, "getdata") else list(img.get_flattened_data())
    chars = ASCII_CHARS[::-1] if invert else ASCII_CHARS

    ascii_str = "".join(chars[pixel * (len(chars) - 1) // 255] for pixel in pixels)

    lines = [
        ascii_str[i : i + width] for i in range(0, len(ascii_str), width)
    ]
    return lines


def _smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def _vignette_alpha(x, y, w, h, inner=0.72, outer=1.05):
    """1.0 en el centro, se degrada suave hacia 0.0 en las esquinas
    (radio elíptico), para que el borde de la imagen se funda con el
    fondo de la terminal en vez de cortar en seco."""
    cx, cy = (w - 1) / 2, (h - 1) / 2
    u = (x - cx) / (w / 2)
    v = (y - cy) / (h / 2)
    r = (u * u + v * v) ** 0.5
    return 1.0 - _smoothstep(inner, outer, r)


def image_to_ansi_truecolor(image_path, width=100, feather=False, bg_color=(0, 0, 0)):
    """Convierte una imagen a líneas con bloques semi-carácter (▀) a
    color verdadero (24-bit). Cada carácter representa 2 píxeles
    verticales: el color de fondo es el píxel de abajo y el de
    primer plano el de arriba. Mucho más fiel que el ASCII por brillo."""
    img = _open_flattened(image_path, bg_color)

    aspect_ratio = img.height / img.width
    out_height = int(round(width * aspect_ratio))
    out_height = max(out_height + (out_height % 2), 2)
    img = img.resize((width, out_height), Image.LANCZOS)
    pixels = img.load()
    bg_r, bg_g, bg_b = bg_color

    def blended(x, y):
        r, g, b = pixels[x, y]
        if not feather:
            return r, g, b
        a = _vignette_alpha(x, y, width, out_height)
        return (
            int(r * a + bg_r * (1 - a)),
            int(g * a + bg_g * (1 - a)),
            int(b * a + bg_b * (1 - a)),
        )

    lines = []
    for y in range(0, out_height, 2):
        row = []
        for x in range(width):
            r1, g1, b1 = blended(x, y)
            r2, g2, b2 = blended(x, y + 1)
            row.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
        row.append("\033[0m")
        lines.append("".join(row))
    return lines


def print_ascii(lines, color=None):
    if color and color in COLOR_CODES:
        for line in lines:
            print(COLOR_CODES[color] + line + COLOR_CODES["reset"])
    else:
        for line in lines:
            print(line)


def print_truecolor(lines):
    for line in lines:
        print(line)


def save_ascii_txt(lines, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Arte ASCII guardado en: {output_path}")


def _ps_escape_string(text):
    """Escapa un string para incrustarlo en un literal de PowerShell,
    reescribiendo caracteres no-ASCII (emoji, ESC, etc.) como
    $([char]N) para que funcione sin importar la codificación con la
    que PowerShell lea el archivo .ps1 (evita el bug de mojibake)."""
    out = []
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('`"')
        elif ch == '`':
            out.append('``')
        elif 0x20 <= code <= 0x7E:
            out.append(ch)
        elif code > 0xFFFF:
            # fuera del BMP: PowerShell/.NET necesita el par subrogado
            code -= 0x10000
            high = 0xD800 + (code >> 10)
            low = 0xDC00 + (code & 0x3FF)
            out.append(f'$([char]0x{high:04X})$([char]0x{low:04X})')
        else:
            out.append(f'$([char]0x{code:04X})')
    return "".join(out)


def install_permanent(lines, color, truecolor=False):
    """Agrega el arte ASCII al perfil de PowerShell para que
    aparezca cada vez que se abra la terminal (solo Windows)."""

    if platform.system() != "Windows":
        print("⚠️  La instalación automática solo está soportada en Windows (PowerShell).")
        print("    Puedes copiar manualmente el archivo .txt generado a tu shell de preferencia.")
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

    marker_start = "# >>> chefcode-ascii-fixed >>>"
    marker_end = "# <<< chefcode-ascii-fixed <<<"

    block_lines = [marker_start]
    if truecolor:
        for line in lines:
            block_lines.append(f'Write-Host "{_ps_escape_string(line)}"')
    else:
        ps_color = POWERSHELL_COLOR_MAP.get(color, "White")
        for line in lines:
            safe_line = line.replace('"', '`"')
            block_lines.append(f'Write-Host "{safe_line}" -ForegroundColor {ps_color}')
    block_lines.append('Write-Host ""')
    block_lines.append(f'Write-Host "{_ps_escape_string("Chef Code 🍳 - Nuevas ideas cocinandose...")}" -ForegroundColor White')
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
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto (ignorado con --truecolor)")
    parser.add_argument("--truecolor", action="store_true", help="Usa bloques a color real (24-bit) en vez de ASCII por brillo. Se ve mucho más nítido, requiere una terminal con soporte truecolor (Windows Terminal, la mayoría de terminales modernas).")
    parser.add_argument("--feather", action="store_true", help="Degrada los bordes de la imagen hacia el color de fondo, en vez de cortar en un rectángulo duro (solo con --truecolor).")
    parser.add_argument("--bg-color", default="0,0,0", help="Color de fondo de tu terminal como 'R,G,B' (default: 0,0,0 = negro), usado por --feather para fundir los bordes.")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros (ignorado con --truecolor)")
    parser.add_argument("--install", action="store_true", help="Deja el arte fijo en tu terminal (PowerShell)")
    parser.add_argument("--save", metavar="ARCHIVO.txt", help="Guarda el resultado como archivo de texto")

    args = parser.parse_args()

    print("👨‍🍳 Cocinando tu arte ASCII...\n")

    bg_color = tuple(int(c.strip()) for c in args.bg_color.split(","))

    if args.truecolor:
        lines = image_to_ansi_truecolor(args.image, width=args.width, feather=args.feather, bg_color=bg_color)
        print_truecolor(lines)
    else:
        lines = image_to_ascii(args.image, width=args.width, invert=args.invert, bg_color=bg_color)
        print_ascii(lines, color=args.color)

    if args.save:
        save_ascii_txt(lines, args.save)

    if args.install:
        install_permanent(lines, args.color or "white", truecolor=args.truecolor)


if __name__ == "__main__":
    main()
