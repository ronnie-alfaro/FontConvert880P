# FontConvert880P

**Turn TTF/OTF fonts into monochrome bitmap fonts for RT-880 RMS, using a browser.**

[English](README.md) · [Español](README_es.md)

FontConvert880P is an independent Python implementation of the FontConvert880 workflow. It provides an English/Spanish web interface for previewing, adjusting, saving, and exporting the 95 printable ASCII characters. Docker Compose packages the server and bundled fonts in one container, so the host does not need Python or a font installation.

## Conversion example

![Ghost.otf converted into 24 by 24 pixel characters, with a text preview and individual glyph controls](docs/images/ghost-font-preview.png)

The screenshot shows a user-supplied **Ghost.otf** font at **26 px**, converted into **24 × 24 px** cells. The global vertical offset is **4.7**, and both global scales are **1**. The uppercase **A**, labeled `A · 65`, is an example of a converted letter: its white pixels become set bits in the exported bitmap. Each card shows the character and its decimal ASCII code; the highlighted `! · 33` card is selected for individual adjustment.

The text preview displays `RT-880 123.456 MHz` using the converted characters. Each glyph uses **72 bytes**, producing a **6,840-byte** font for all 95 characters. The large on-screen pixels are a preview enlargement, not extra resolution in the output. Ghost.otf is shown as an example and is **not included** in this repository.

## Features

- Bundled DejaVu Sans: regular, bold, italic, and bold italic.
- Upload your own `.ttf` or `.otf` file.
- Adjustable font size and independent cell width and height.
- Global and per-character horizontal/vertical offset and scaling.
- Individual selection and cumulative uppercase, lowercase, number, and symbol groups.
- Monochrome character grid and editable sample text.
- Save/reopen `.font880` settings; export `.rmsfont` binary or `.c` source.
- One local container, with no account, database, or external conversion service.

## Quick start with Docker Compose

Install Docker with the Compose plugin, such as Docker Desktop, and start its engine. Copy or clone this project, open a terminal in its directory, then run:

```sh
docker compose up --build -d
```

Open **http://localhost:8800**. The first build needs Internet access to download the base image, Python dependencies, and DejaVu fonts. Once built, conversion works offline.

```sh
# Check service status and health
docker compose ps

# View recent logs
docker compose logs --tail=100

# Stop and remove the container
docker compose down

# Rebuild after updating the project files
docker compose up --build -d
```

### Port and network access

The default binding is `127.0.0.1:8800`; the container listens on port `8000`. To change the host port persistently, create `.env` beside `compose.yaml`:

```dotenv
PORT=8880
BIND_ADDRESS=127.0.0.1
```

Run `docker compose up -d` again and open **http://localhost:8880**. `.env` is ignored by Git.

For intentional access from a trusted local network, set `BIND_ADDRESS=0.0.0.0` and connect to `http://HOST_IP:PORT`. The application has no authentication or HTTPS configuration; direct public Internet deployment is outside this setup.

### Move to another computer

Copy the project directory, including `templates`, `Dockerfile`, `requirements.txt`, and `compose.yaml`, then run the quick-start command on the destination. You do not need to copy `.venv` or container data. If you use a custom `.env`, copy it separately as needed.

To continue an editing session, also bring the downloaded `.font880` definition and the original TTF/OTF file. The application does not store sessions on the server.

## Step-by-step usage

### 1. Choose a font

Use **Estilo incluido** to select a DejaVu Sans variant, or use **Cargar fuente TTF / OTF** to upload a file. **Familia** displays the active family or uploaded filename stem; it is read-only.

For a custom font, upload the actual bold or italic variant you want. The bundled-style selector is disabled for uploads and does not synthesize a style. **Usar DejaVu Sans** returns to the bundled bold font while retaining the other adjustments.

Set **Tamaño de fuente (px)** to control the font before it is placed inside a cell. A larger font does not enlarge the cell automatically: pixels outside its boundaries are clipped.

### 2. Set the cell and global adjustments

| Control | Range | Effect |
| --- | --- | --- |
| Font size | 1–256 px; UI step 0.1 | Changes the size used to rasterize the source font. |
| Cell width / height | 8–96 px, multiples of 8 | Sets the fixed output dimensions for every character. Rectangular cells are supported. |
| Offset X | −100 to 100; UI step 0.1 | Moves characters horizontally; positive values move right. |
| Offset Y | −100 to 100; UI step 0.1 | Moves characters vertically; positive values move down. |
| Scale X | 0.02–100; UI step 0.01 | Stretches or compresses the horizontal dimension. `1` is unchanged. |
| Scale Y | 0.02–100; UI step 0.01 | Stretches or compresses the vertical dimension. `1` is unchanged. |
| Compatible empty border | On / off | Forces the last row and last column to remain empty, matching the original exporter. On by default. |

Start with global adjustments to establish the overall size and vertical placement. A `0.8` scale compresses that axis; `1.2` enlarges it. Large scales or offsets can push a glyph outside its cell.

Global and individual offsets are added; scales are multiplied. Translation is applied before scaling, so scaling also affects the resulting displacement. A global X scale of `1.2` and an individual X scale of `0.8` produce an effective X scale of `0.96`.

### 3. Fine-tune characters

Click a card to toggle selection. Selected cards have a colored border. Group buttons add characters to the selection:

| Button | Selection |
| --- | --- |
| Todos | All 95 characters. |
| A–Z / a–z | Uppercase / lowercase ASCII letters. |
| 0–9 | Digits. |
| Símbolos | Remaining characters, including the space. |
| Quitar selección | Clears selection without changing adjustments. |

The **Caracteres seleccionados** controls use the same offset and scale ranges as the global controls. They become available when at least one character is selected.

**Changing any individual control applies all four displayed individual values to every selected character.** The controls initially show the first selected character's values, not an average. Clear the selection before correcting a single letter if you want to preserve other characters' different settings.

**Restablecer seleccionados** resets individual offsets to `0` and scales to `1`; global adjustments still apply. Changes refresh the preview automatically after the field value is committed, for example by leaving the field or using its arrows.

### 4. Inspect the preview

Use the grid to look for clipping, missing strokes, alignment, and spacing. A blank space character is normal. The sample text uses the same fixed-width bitmaps as export, without proportional spacing or kerning. Characters outside printable ASCII are skipped in this sample.

The preview and export use the same server rendering routine. Changing the sample text does not change which characters are exported: the output always contains the full set of 95.

### 5. Save or export

| Download | Contents | Use |
| --- | --- | --- |
| `ghost-24x24.font880` | Family/style metadata, font size, dimensions, global adjustments, 95 individual transforms, and border setting. | Resume editing. It contains neither the font file nor the rendered bitmaps. |
| `ghost-24x24.rmsfont` | Headerless packed monochrome pixels. | Use with software expecting the RT-880 RMS font layout. |
| `ghost-24x24.c` | A `const uint8_t` array, `<stdint.h>`, and ASCII comments. | Integrate the bitmap bytes into C code. |

Downloads automatically use the source font name and current cell dimensions: `ghost.ttf` at 24 × 24 produces `ghost-24x24.rmsfont`, `ghost-24x24.font880`, or `ghost-24x24.c`. Spaces and unsafe filename characters are replaced with hyphens. Export generates a file only: it does not connect to or flash a radio.

To resume, open the `.font880` file using **Abrir ajustes .font880**. For an external font, load its TTF/OTF **after** opening the definition: opening settings clears the currently uploaded file. A request to load the referenced font is expected until that file is supplied. Matching fonts and styles must be provided by the user; a definition cannot recover a missing font.

## How conversion works

1. The browser sends current settings and, if present, the uploaded font to Flask.
2. Pillow/FreeType rasterizes ASCII codes **32 through 126**, preserving vertical font metrics and horizontally centering the glyph's ink before adjustments.
3. Global and individual transforms place the glyph in its fixed-size cell. Pixels outside the cell are clipped.
4. Intensities greater than `128` become white/set pixels; other pixels become black/clear pixels. The optional empty border is applied.
5. Preview returns the pixels to browser canvases; export packs those same rendered pixels into bytes.

### Binary layout

There is no header or embedded dimension information. A consumer must know the cell width and height.

- Characters: ascending ASCII order, starting with space (`32`).
- Within a character: columns from left to right.
- Within a column: vertical groups of eight pixels, top to bottom.
- Within a byte: the top pixel is bit 0, the bottom pixel is bit 7.

For example, if only the first and eighth pixels in a vertical group are set, its byte is `10000001` in binary, or `0x81`.

```text
bytes per character = width × height / 8
bytes per font      = 95 × width × height / 8
```

| Cell | Bytes per character | Total bytes |
| --- | ---: | ---: |
| 8 × 16 | 16 | 1,520 |
| 24 × 24 | 72 | 6,840 |
| 32 × 32 | 128 | 12,160 |

`.font880` uses `key=value` text lines. Per-character indices run from `0` to `94`, corresponding to ASCII `32` to `126`. The reader accepts decimal points and commas. The extra `legacy_border` setting is ignored by the original Windows application.

## Runtime and data

Docker runs **Gunicorn → Flask → Pillow/FreeType** in one container. The interface uses HTML, CSS, and JavaScript without a frontend build step. The container runs as a non-root user with a read-only filesystem and a temporary `/tmp` mount.

Uploads and generated output are processed per request and are not saved as server-side projects. No persistent volumes or database are required. Requests are limited to **12 MB total**, including the font and settings. Conversion files are not sent to third-party services; when accessing another host, they are sent to that host's application server.

**Reloading or closing the page loses unsaved edits.** Download a definition and retain your source font before leaving.

## Compatibility and limits

- Output is limited to 95 printable ASCII characters. Accents, `ñ`, emoji, and other Unicode characters are not exported.
- Font coverage matters: a source font may display a missing-glyph symbol where it lacks a character. The screenshot includes examples of this behavior.
- Pillow/FreeType replaces Windows GDI+. Metrics and rasterization can differ, so imported definitions may need tuning. Pixel-identical output to the Windows tool is not guaranteed.
- Supported cell dimensions in the editor do not establish what a specific firmware version accepts. Check the receiving software's requirements.
- The binary layout is covered by automated tests; export has not been validated on physical radio hardware.
- The web interface defaults to English. Use **Language / Idioma** to switch to Spanish without losing your current work. Your choice is remembered in this browser. These documents are available in both languages; Spanish control names below correspond to the Spanish interface.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Docker cannot connect to its daemon | Start Docker Desktop or the Docker engine, then rerun Compose. |
| Port already in use | Set a different `PORT` in `.env` and run `docker compose up -d`. |
| Browser cannot connect | Check `docker compose ps`, logs, and the configured host port. |
| Font missing after opening settings | Upload the corresponding TTF/OTF after loading the definition. |
| Empty or clipped characters | Reduce font size/scales, restore individual values, and adjust global Y. Verify source-font character coverage. |
| Wrong letters change together | Clear selection and select only the character you intend to edit. |
| Upload rejected | Use a valid TTF/OTF and keep the full request below 12 MB. |
| Changes lost after refresh | Reopen the downloaded definition and reload its source font; there is no autosave. |

## Development and verification

For Docker-based tests, run from the project root (POSIX shell):

```sh
docker compose run --rm -v "$(pwd)/tests:/app/tests:ro" fontconvert python -m unittest discover -s tests -v
```

The suite covers bit ordering, definition round trips, decimal commas, border rendering, included styles, and API exports/invalid input.

For local development without Docker, use Python 3.12 and install the DejaVu Sans regular, bold, oblique, and bold-oblique font files where Pillow can find them:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Local development serves **http://localhost:8000**. In another terminal with the environment activated, run `python -m unittest discover -s tests -v`. The development server is separate from the Gunicorn setup used in Docker.

| Path | Purpose |
| --- | --- |
| `app.py` | Validation, rendering, definition handling, export, HTTP routes. |
| `templates/index.html` | Web interface, controls, and canvas previews. |
| `tests/test_app.py` | Converter and API tests. |
| `Dockerfile` / `compose.yaml` | Container build, service, networking, health check. |
| `docs/images/` | Documentation screenshots. |

The original Windows project remains separate; this repository contains the Python implementation.
