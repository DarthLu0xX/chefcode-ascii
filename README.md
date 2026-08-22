# 👨‍🍳 Chef Code ASCII

Convierte tus propias imágenes y videos en arte ASCII a color real directamente en tu terminal.

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

## 🚀 Empieza aquí: menú interactivo (`chefcode.py`)

La forma más fácil de usar esto — no necesitas memorizar ningún flag:

```bash
python chefcode.py
```

Te pregunta:

1. **¿Foto o video?**
2. La ruta de tu archivo (y un par de opciones simples: ancho, si degradar los bordes, etc.)
3. Te muestra la **vista previa** ahí mismo en tu terminal, a color real.
4. Solo si te gusta cómo quedó, te pregunta si quieres **guardarlo** para que aparezca cada vez que abras la terminal.

Por debajo usa las mismas dos herramientas de siempre — `fixed/` para imágenes y `video/` para animaciones — así que si prefieres controlar cada flag a mano, puedes seguir usándolas directamente (ver abajo).

---

## 🖼️ 1. Imagen fija (`fixed/ascii_fixed.py`)

Convierte una imagen en ASCII. Puedes verla en pantalla, guardarla como archivo de texto, o dejarla **instalada permanentemente** en tu terminal (Windows PowerShell).

### Uso básico

```bash
python fixed/ascii_fixed.py mi_imagen.jpg
```

### Opciones

| Opción        | Descripción                                              |
|---------------|------------------------------------------------------------|
| `--width`     | Ancho del arte en caracteres (default: 100)               |
| `--color`     | Color del texto: red, green, yellow, blue, magenta, cyan, white (ignorado con `--truecolor`) |
| `--truecolor` | Renderiza con bloques `▀` a color real (24-bit) en vez de ASCII por brillo. Se ve mucho más nítido — recomendado si tu terminal soporta color de 24 bits (Windows Terminal, la mayoría de terminales modernas) |
| `--sixel`     | Dibuja la imagen real, pixel por pixel (protocolo Sixel), en vez de simularla con texto — sin escalones, calidad de foto. Ignora `--truecolor`/`--color`/`--invert`/`--feather`. Experimental: requiere Windows Terminal 1.22+ |
| `--feather`   | Solo para fotos **sin** transparencia. Degrada los bordes hacia el color de fondo en vez de cortar en un rectángulo duro |
| `--bg-color`  | Color de fondo de tu terminal como `"R,G,B"` (default: `0,0,0` = negro), usado por `--feather` |
| `--invert`    | Invierte tonos claros/oscuros (ignorado con `--truecolor`/`--sixel`) |
| `--save`      | Guarda el resultado como archivo `.txt`                    |
| `--install`   | Deja el arte fijo en tu terminal (aparece cada vez que la abres) |

Si tu imagen es un **PNG con transparencia** (por ejemplo un recorte hecho con `remove.bg`), `--truecolor` respeta esa transparencia de verdad: no pinta ningún rectángulo de fondo, solo la silueta — como una estampa pegada en la terminal, no una foto con marco. `--feather` no aplica en ese caso (se ignora automáticamente) porque el recorte ya trae su propio borde limpio.

### ¿Bloques de color o Sixel?

`--truecolor` (bloques `▀`) es el modo por defecto recomendado: funciona en casi cualquier terminal moderna, pero por más ancho que uses siempre vas a notar un ligero "escalonado" en curvas, porque cada carácter solo puede pintar un color sólido.

`--sixel` dibuja la imagen pixel por pixel de verdad — cero escalones, calidad de foto real — pero es experimental: necesitas **Windows Terminal 1.22 o superior** (no funciona en la consola clásica de "Windows PowerShell"). **Pruébalo primero sin `--install`** para confirmar que tu terminal lo soporta; si en vez de la imagen ves texto/códigos raros, tu terminal no lo soporta todavía y debes usar `--truecolor`.

```bash
# 1. Prueba primero (sin --install)
python fixed/ascii_fixed.py mi_foto.png --sixel

# 2. Si se ve bien, instálalo
python fixed/ascii_fixed.py mi_foto.png --sixel --install
```

### Ejemplo: dejarlo fijo en tu terminal (modo clásico)

```bash
python fixed/ascii_fixed.py mi_logo.png --width 80 --color red --install
```

### Ejemplo: a color real (recomendado)

```bash
python fixed/ascii_fixed.py mi_logo.png --width 90 --truecolor --install
```

Esto agrega el arte a tu perfil de PowerShell (`$PROFILE`). Cierra y vuelve a abrir la terminal para verlo.

> ⚠️ La instalación automática con `--install` solo está soportada en **Windows (PowerShell)** por ahora. En Mac/Linux, usa `--save` y agrega el archivo manualmente a tu `.bashrc` / `.zshrc`.
> 💡 `--truecolor` se ve mucho mejor en **Windows Terminal** que en la consola clásica de "Windows PowerShell" (conhost), que no siempre renderiza bien el color de 24 bits.

---

## 🎬 2. Video animado (`video/ascii_video.py`)

Convierte un video (mp4, mov) o GIF en una animación ASCII que se reproduce en tu terminal. Igual que las fotos, soporta `--truecolor` (bloques a color real) y `--feather` (bordes degradados).

### Uso básico

```bash
python video/ascii_video.py mi_video.mp4
```

### Opciones

| Opción         | Descripción                                              |
|-----------------|------------------------------------------------------------|
| `--width`       | Ancho del arte en caracteres (default: 80)                 |
| `--fps`         | Velocidad de reproducción en fotogramas por segundo (default: 15) |
| `--color`       | Color del texto (ignorado con `--truecolor`)               |
| `--truecolor`   | Renderiza con bloques `▀` a color real (24-bit), igual que en las fotos |
| `--sixel`       | Dibuja cada fotograma como imagen real (protocolo Sixel), sin escalones. Con GIF, respeta la transparencia real de cada fotograma (Pillow, no cv2). Experimental (Windows Terminal 1.22+). Ignora `--truecolor`/`--color`/`--invert`/`--feather` |
| `--feather`     | Solo con `--truecolor`. Degrada los bordes de cada fotograma hacia el fondo |
| `--bg-color`    | Color de fondo como `"R,G,B"` (default: `0,0,0`), usado por `--feather` |
| `--invert`      | Invierte tonos claros/oscuros (ignorado con `--truecolor`/`--sixel`) |
| `--once`        | Reproduce una sola vez en vez de en bucle infinito          |
| `--max-frames`  | Límite de fotogramas a procesar (útil para videos largos)  |
| `--install`     | Deja el video instalado para que se reproduzca al abrir la terminal |
| `--split-pane`  | Con `--install` y bucle infinito (sin `--once`): abre la animación en un panel nuevo de Windows Terminal en vez de ocupar la terminal principal — puedes seguir escribiendo comandos mientras se reproduce |
| `--split-ratio` | Fracción de la ventana que ocupa el panel nuevo con `--split-pane` (default: `0.3`) |

### Ejemplo: a color real, con bordes degradados

```bash
python video/ascii_video.py mi_video.mp4 --width 70 --truecolor --feather --once
```

### Ejemplo: Sixel, con transparencia real de GIF, "vivo" en un panel aparte

```bash
# 1. Prueba primero (sin --install, con --once para que termine solo)
python video/ascii_video.py mi_baile.gif --sixel --once

# 2. Si se ve bien, instálalo en bucle infinito en un panel nuevo,
#    para verlo mientras sigues trabajando en tu panel principal
python video/ascii_video.py mi_baile.gif --sixel --width 300 --install --split-pane
```

Presiona **Ctrl + C** en cualquier momento para detener la animación.

> 💡 Tip: videos cortos (5-15 segundos) funcionan mejor. Videos muy largos tardan más en procesarse antes de reproducirse.
> ⚠️ A diferencia de una imagen fija, `--install` en el video vuelve a correr Python cada vez que abres la terminal (con `--once`, para no bloquear la sesión en un loop infinito). Necesitas Python y las dependencias de este proyecto instaladas en la máquina donde uses la terminal.
> ⚠️ `--sixel` en video es más lento de procesar que `--truecolor` (cada fotograma se cuantiza a color real). Con `--install`, eso significa que **cada terminal nueva tarda esos mismos segundos en aparecer** antes de reproducir la animación — para un GIF de ~50 fotogramas cuenta con varios segundos de espera. Si te importa más la velocidad de arranque que la calidad, usa `--truecolor` en su lugar, o `--max-frames` para recortar el clip.

---

## 🍳 Sobre Chef Code

Contenido sobre IA, programación y automatización — nuevas ideas cocinándose cada semana.

Sígueme en Instagram: **@thechefcodee**
