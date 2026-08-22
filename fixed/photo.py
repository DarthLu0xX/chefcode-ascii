#!/usr/bin/env python3
"""
Terminal Perrona - Foto Fija
------------------------------
Convierte una imagen en algo que se ve real en tu terminal (a color
real o Sixel) y opcionalmente la deja fija ahí (aparece cada vez que
la abres).

Uso:
    python photo.py mi_imagen.jpg
    python photo.py mi_imagen.jpg --width 100 --color green
    python photo.py mi_imagen.jpg --install
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


def _open_raw(image_path):
    try:
        return Image.open(image_path)
    except FileNotFoundError:
        print(f"❌ No se encontró la imagen: {image_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al abrir la imagen: {e}")
        sys.exit(1)


def _has_alpha(img):
    return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)


def _resize_out_height(width, aspect_ratio):
    out_height = int(round(width * aspect_ratio))
    return max(out_height + (out_height % 2), 2)


def _sticker_lines(img, width, alpha_threshold=128):
    """Renderiza respetando la transparencia real del PNG: donde el
    píxel es transparente no se imprime ningún color de fondo, así se
    ve el fondo nativo de la terminal en vez de un rectángulo sólido —
    como una estampa pegada, no una foto con marco."""
    out_height = _resize_out_height(width, img.height / img.width)
    img = img.resize((width, out_height), Image.LANCZOS)
    px = img.load()

    lines = []
    for y in range(0, out_height, 2):
        parts = []
        for x in range(width):
            r1, g1, b1, a1 = px[x, y]
            r2, g2, b2, a2 = px[x, y + 1]
            top_opaque = a1 >= alpha_threshold
            bot_opaque = a2 >= alpha_threshold
            if not top_opaque and not bot_opaque:
                parts.append("\033[0m ")
            elif top_opaque and bot_opaque:
                parts.append(f"\033[0m\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
            elif top_opaque:
                parts.append(f"\033[0m\033[38;2;{r1};{g1};{b1}m▀")
            else:
                parts.append(f"\033[0m\033[38;2;{r2};{g2};{b2}m▄")
        parts.append("\033[0m")
        lines.append("".join(parts))
    return lines


def _rectangle_lines(img, width, feather=False, bg_color=(0, 0, 0)):
    """Renderiza como rectángulo sólido (para fotos sin transparencia),
    con degradado opcional de los bordes hacia bg_color."""
    out_height = _resize_out_height(width, img.height / img.width)
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


def image_to_ansi_truecolor(image_path, width=100, feather=False, bg_color=(0, 0, 0)):
    """Convierte una imagen a líneas con bloques semi-carácter (▀) a
    color verdadero (24-bit). Si la imagen tiene transparencia (PNG
    recortado), respeta esa transparencia de verdad — sin rectángulo
    de fondo — en vez de rellenarla con un color sólido."""
    raw = _open_raw(image_path)

    if _has_alpha(raw):
        if feather:
            print("ℹ️  --feather se ignora: la imagen ya tiene transparencia real, no necesita degradado artificial.")
        return _sticker_lines(raw.convert("RGBA"), width)

    return _rectangle_lines(raw.convert("RGB"), width, feather=feather, bg_color=bg_color)


def image_to_sixel(image_path, width=None, max_colors=256, alpha_threshold=128):
    """Codifica la imagen como una secuencia Sixel: la terminal dibuja
    la imagen de verdad, pixel por pixel, en vez de simularla con
    caracteres de color. Sin escalones — calidad de foto real, si tu
    terminal soporta Sixel (Windows Terminal, de forma experimental).
    Los píxeles transparentes se dejan sin dibujar (no se pintan)."""
    raw = _open_raw(image_path)
    has_alpha = _has_alpha(raw)
    img = raw.convert("RGBA") if has_alpha else raw.convert("RGB")

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

    # P2=1 en la introducción DCS: los píxeles "sin marcar" (transparentes)
    # se dejan tal cual en vez de rellenarse con un color de fondo.
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
    return "".join(out)


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


def print_sixel(data):
    print(data, end="")
    print()


def save_ascii_txt(lines, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Resultado guardado en: {output_path}")


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


MARKER_START = "# >>> chefcode-ascii-fixed >>>"
MARKER_END = "# <<< chefcode-ascii-fixed <<<"


def _get_profile_path():
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "echo $PROFILE"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ No se pudo obtener la ruta de $PROFILE: {e}")
        return None


def uninstall():
    """Quita la foto instalada del perfil de PowerShell, si hay una."""
    if platform.system() != "Windows":
        print("⚠️  Nada que desinstalar: la instalación automática solo aplica en Windows (PowerShell).")
        return

    profile_path = _get_profile_path()
    if not profile_path or not os.path.exists(profile_path):
        print("ℹ️  No había nada instalado.")
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()

    if MARKER_START not in content or MARKER_END not in content:
        print("ℹ️  No había ninguna foto instalada en tu perfil.")
        return

    before = content.split(MARKER_START)[0]
    after = content.split(MARKER_END)[1]
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(before + after)

    print(f"✅ Desinstalado de tu perfil de PowerShell: {profile_path}")
    print("🔄 Cierra y vuelve a abrir la terminal para verlo.")


def install_permanent(lines, color, truecolor=False):
    """Agrega el resultado al perfil de PowerShell para que
    aparezca cada vez que se abra la terminal (solo Windows)."""

    if platform.system() != "Windows":
        print("⚠️  La instalación automática solo está soportada en Windows (PowerShell).")
        print("    Puedes copiar manualmente el archivo .txt generado a tu shell de preferencia.")
        return

    profile_path = _get_profile_path()
    if not profile_path:
        return

    profile_dir = os.path.dirname(profile_path)
    os.makedirs(profile_dir, exist_ok=True)

    marker_start = MARKER_START
    marker_end = MARKER_END

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
        description="Terminal Perrona - Convierte una imagen en algo que se ve real en tu terminal"
    )
    parser.add_argument("image", nargs="?", default=None, help="Ruta a la imagen (jpg, png, etc.). No hace falta con --uninstall.")
    parser.add_argument("--uninstall", action="store_true", help="Quita la foto instalada de tu perfil de PowerShell y termina (no necesita ruta de imagen).")
    parser.add_argument("--width", type=int, default=None, help="Ancho en caracteres (modo texto) o en píxeles reales (--sixel). Default: 100 en modo texto, 300 con --sixel.")
    parser.add_argument("--color", choices=list(COLOR_CODES.keys())[:-1], default=None, help="Color del texto (ignorado con --truecolor)")
    parser.add_argument("--truecolor", action="store_true", help="Usa bloques a color real (24-bit) en vez de ASCII por brillo. Se ve mucho más nítido, requiere una terminal con soporte truecolor (Windows Terminal, la mayoría de terminales modernas).")
    parser.add_argument("--sixel", action="store_true", help="Dibuja la imagen real, pixel por pixel (protocolo Sixel), en vez de simularla con texto. Sin escalones — calidad de foto. Requiere una terminal con soporte Sixel (Windows Terminal 1.22+). Ignora --truecolor/--color/--invert/--feather.")
    parser.add_argument("--feather", action="store_true", help="Degrada los bordes hacia el color de fondo, en vez de cortar en un rectángulo duro. Solo aplica a fotos SIN transparencia; si el PNG ya tiene transparencia se ignora (se respeta esa transparencia real, sin caja).")
    parser.add_argument("--bg-color", default="0,0,0", help="Color de fondo de tu terminal como 'R,G,B' (default: 0,0,0 = negro), usado por --feather para fundir los bordes.")
    parser.add_argument("--invert", action="store_true", help="Invierte los tonos claros/oscuros (ignorado con --truecolor)")
    parser.add_argument("--install", action="store_true", help="Deja el arte fijo en tu terminal (PowerShell)")
    parser.add_argument("--save", metavar="ARCHIVO.txt", help="Guarda el resultado como archivo de texto")

    args = parser.parse_args()

    if args.uninstall:
        uninstall()
        return

    if not args.image:
        parser.error("falta la ruta de la imagen (o usa --uninstall)")

    print("👨‍🍳 Cocinando tu imagen...\n")

    bg_color = tuple(int(c.strip()) for c in args.bg_color.split(","))
    if args.width is None:
        args.width = 300 if args.sixel else 100

    if args.sixel:
        data = image_to_sixel(args.image, width=args.width)
        print_sixel(data)
        lines = [data]
    elif args.truecolor:
        lines = image_to_ansi_truecolor(args.image, width=args.width, feather=args.feather, bg_color=bg_color)
        print_truecolor(lines)
    else:
        lines = image_to_ascii(args.image, width=args.width, invert=args.invert, bg_color=bg_color)
        print_ascii(lines, color=args.color)

    if args.save:
        save_ascii_txt(lines, args.save)

    if args.install:
        install_permanent(lines, args.color or "white", truecolor=args.truecolor or args.sixel)


if __name__ == "__main__":
    main()
