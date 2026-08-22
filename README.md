# 👨‍🍳 Chef Code ASCII

Convierte tus propias imágenes y videos en arte ASCII directamente en tu terminal.

Dos herramientas, dos usos:

- **`fixed/`** → convierte una **imagen** en ASCII y déjala **fija** en tu terminal (aparece cada vez que la abres).
- **`video/`** → convierte un **video o GIF** en una **animación ASCII** que se reproduce en bucle (como los famosos `curl ascii.live/rick`, pero con tu propio contenido). Presiona `Ctrl + C` para detenerla.

Todo corre **localmente en tu computadora**. No se sube nada a ningún servidor — tu imagen o video nunca sale de tu PC.

---

## 📦 Requisitos

- Python 3.8 o superior
- pip

Instala las dependencias:

```bash
pip install -r requirements.txt
```

---

## 🖼️ 1. Imagen fija (`fixed/ascii_fixed.py`)

Convierte una imagen en ASCII. Puedes verla en pantalla, guardarla como archivo de texto, o dejarla **instalada permanentemente** en tu terminal (Windows PowerShell).

### Uso básico

```bash
python fixed/ascii_fixed.py mi_imagen.jpg
```

### Opciones

| Opción      | Descripción                                              |
|-------------|------------------------------------------------------------|
| `--width`   | Ancho del arte en caracteres (default: 100)               |
| `--color`   | Color del texto: red, green, yellow, blue, magenta, cyan, white |
| `--invert`  | Invierte tonos claros/oscuros                              |
| `--save`    | Guarda el resultado como archivo `.txt`                    |
| `--install` | Deja el arte fijo en tu terminal (aparece cada vez que la abres) |

### Ejemplo: dejarlo fijo en tu terminal

```bash
python fixed/ascii_fixed.py mi_logo.png --width 80 --color red --install
```

Esto agrega el arte a tu perfil de PowerShell (`$PROFILE`). Cierra y vuelve a abrir la terminal para verlo.

> ⚠️ La instalación automática con `--install` solo está soportada en **Windows (PowerShell)** por ahora. En Mac/Linux, usa `--save` y agrega el archivo manualmente a tu `.bashrc` / `.zshrc`.

---

## 🎬 2. Video animado (`video/ascii_video.py`)

Convierte un video (mp4, mov) o GIF en una animación ASCII que se reproduce en bucle en tu terminal.

### Uso básico

```bash
python video/ascii_video.py mi_video.mp4
```

### Opciones

| Opción         | Descripción                                              |
|-----------------|------------------------------------------------------------|
| `--width`       | Ancho del arte en caracteres (default: 80)                 |
| `--fps`         | Velocidad de reproducción en fotogramas por segundo (default: 15) |
| `--color`       | Color del texto                                            |
| `--invert`      | Invierte tonos claros/oscuros                              |
| `--once`        | Reproduce una sola vez en vez de en bucle infinito          |
| `--max-frames`  | Límite de fotogramas a procesar (útil para videos largos)  |

### Ejemplo

```bash
python video/ascii_video.py mi_video.mp4 --width 90 --fps 12 --color red
```

Presiona **Ctrl + C** en cualquier momento para detener la animación.

> 💡 Tip: videos cortos (5-15 segundos) funcionan mejor. Videos muy largos tardan más en procesarse antes de reproducirse.

---

## 🍳 Sobre Chef Code

Contenido sobre IA, programación y automatización — nuevas ideas cocinándose cada semana.

Sígueme en Instagram: **@thechefcodee**
