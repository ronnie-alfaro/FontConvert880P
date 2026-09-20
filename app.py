"""Portable RT-880 font converter. Uploaded files remain in request memory."""
import io
import json
import math
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont

TRANSLATIONS = json.loads(Path(__file__).with_name('translations.json').read_text())

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
STYLES = {'Regular': 'DejaVuSans.ttf', 'Bold': 'DejaVuSans-Bold.ttf',
          'Italic': 'DejaVuSans-Oblique.ttf', 'Bold, Italic': 'DejaVuSans-BoldOblique.ttf'}


def defaults():
    return dict(fontfamily='DejaVu Sans', fontsize=26, fontstyle='Bold', bitmapwidth=24,
                bitmapheight=24, globalhoffset=0, globalvoffset=-4.8,
                globalhsize=1, globalvsize=1, legacy_border=True,
                glyphs=[dict(hoff=0, voff=0, hsize=1, vsize=1) for _ in range(95)])


def number(value, low, high):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'El valor debe estar entre {low} y {high}.')
    return value


def validate(data):
    cfg = defaults()
    cfg.update({k: v for k, v in data.items() if k in cfg})
    for key in ('bitmapwidth', 'bitmapheight'):
        n = number(cfg[key], 8, 96)
        if n % 8:
            raise ValueError('Las dimensiones deben ser múltiplos de 8 entre 8 y 96.')
        cfg[key] = int(n)
    cfg['fontsize'] = number(cfg['fontsize'], 1, 256)
    for key in ('globalhoffset', 'globalvoffset'):
        cfg[key] = number(cfg[key], -100, 100)
    for key in ('globalhsize', 'globalvsize'):
        cfg[key] = number(cfg[key], .02, 100)
    if not isinstance(cfg['glyphs'], list) or len(cfg['glyphs']) != 95:
        raise ValueError('Se requieren 95 caracteres.')
    cfg['glyphs'] = [{k: number(g[k], .02 if 'size' in k else -100, 100)
                      for k in ('hoff', 'voff', 'hsize', 'vsize')} for g in cfg['glyphs']]
    if not isinstance(cfg['legacy_border'], bool):
        raise ValueError('El borde de compatibilidad debe ser booleano.')
    for key in ('fontfamily', 'fontstyle'):
        if not isinstance(cfg[key], str) or not 1 <= len(cfg[key]) <= 200 or any(c in cfg[key] for c in '\r\n='):
            raise ValueError('Nombre o estilo de fuente inválido.')
    return cfg


def parse_definition(text):
    cfg = defaults()
    for line in text.lstrip('\ufeff').splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition('=')
        if not sep:
            raise ValueError('Definición .font880 inválida.')
        if key in ('hoff', 'voff', 'hsize', 'vsize'):
            index, value = value.split()
            index = int(index)
            if not 0 <= index < 95:
                raise ValueError('Índice de carácter inválido.')
            cfg['glyphs'][index][key] = float(value.replace(',', '.'))
        elif key in ('fontfamily', 'fontstyle'):
            cfg[key] = value
        elif key == 'legacy_border':
            cfg[key] = value.lower() == 'true'
        elif key in cfg and key != 'glyphs':
            cfg[key] = float(value.replace(',', '.'))
    return validate(cfg)


def definition(cfg):
    lines = [f'{k}={cfg[k]}' for k in defaults() if k not in ('glyphs', 'legacy_border')]
    lines.append(f"legacy_border={str(cfg['legacy_border']).lower()}")
    for i, glyph in enumerate(cfg['glyphs']):
        lines.extend(f'{key}={i} {value}' for key, value in glyph.items())
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def render(cfg, uploaded=None):
    source = io.BytesIO(uploaded) if uploaded else STYLES.get(cfg['fontstyle'])
    if not uploaded and cfg['fontfamily'] != 'DejaVu Sans':
        raise ValueError(f"Carga el archivo TTF/OTF de la fuente {cfg['fontfamily']} para continuar.")
    if source is None:
        raise ValueError('Carga el archivo de fuente para este estilo.')
    try:
        font = ImageFont.truetype(source, size=cfg['fontsize'])
    except OSError as exc:
        raise ValueError('No se pudo abrir la fuente TTF/OTF.') from exc
    w, h = cfg['bitmapwidth'], cfg['bitmapheight']
    result = []
    for index, transform in enumerate(cfg['glyphs']):
        character = chr(index + 32)
        left, top, right, bottom = font.getbbox(character)
        # Keep the font's vertical metrics and center the actual horizontal ink.
        width, height = max(1, right - left), max(1, bottom - top)
        ink = Image.new('L', (width, height))
        ImageDraw.Draw(ink).text((-left, -top), character, font=font, fill=255)
        sx = cfg['globalhsize'] * transform['hsize']
        sy = cfg['globalvsize'] * transform['vsize']
        x = (w - width) / 2 + cfg['globalhoffset'] + transform['hoff']
        y = top + cfg['globalvoffset'] + transform['voff']
        # Inverse mapping avoids allocating enormous intermediate scaled images.
        bitmap = ink.transform((w, h), Image.Transform.AFFINE,
                               (1 / sx, 0, -x, 0, 1 / sy, -y),
                               resample=Image.Resampling.BICUBIC)
        bitmap = bitmap.point(lambda p: 255 if p > 128 else 0, mode='1')
        if cfg['legacy_border']:
            draw = ImageDraw.Draw(bitmap)
            draw.line((w - 1, 0, w - 1, h - 1), fill=0)
            draw.line((0, h - 1, w - 1, h - 1), fill=0)
        result.append(bitmap)
    return result


def pack(bitmaps):
    output = bytearray()
    for bitmap in bitmaps:
        for x in range(bitmap.width):
            for y in range(0, bitmap.height, 8):
                output.append(sum((1 << bit) for bit in range(8) if bitmap.getpixel((x, y + bit))))
    return bytes(output)


def c_source(cfg, data):
    name = re.sub(r'[^a-zA-Z0-9_]', '_', cfg['fontfamily'])
    stride = cfg['bitmapwidth'] * cfg['bitmapheight'] // 8
    lines = ['#include <stdint.h>', '', f"const uint8_t font{name}{cfg['bitmapwidth']}x{cfg['bitmapheight']}[] = {{"]
    for index in range(95):
        lines.append(f'    /* ASCII {index + 32} */')
        lines.append('    ' + ','.join(f'0x{b:02X}' for b in data[index * stride:(index + 1) * stride]) + ',')
    return ('\n'.join(lines) + '\n};\n').encode()


@app.get('/')
def index():
    return render_template('index.html', initial=defaults(), translations=TRANSLATIONS)


@app.get('/health')
def health():
    return jsonify(status='ok')


@app.post('/api/load')
def load():
    file = request.files.get('definition')
    if not file:
        raise ValueError('Selecciona una definición .font880.')
    return jsonify(parse_definition(file.read().decode('utf-8-sig')))


def export_name(cfg, extension, original=None):
    """Use the source font stem and output cell dimensions for every download."""
    name = (original or cfg['fontfamily']).replace('\\', '/').rsplit('/', 1)[-1]
    name = re.sub(r'\.(ttf|otf)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('.-') or 'font'
    return f"{name[:120]}-{cfg['bitmapwidth']}x{cfg['bitmapheight']}.{extension}"


@app.post('/api/<action>')
def convert(action):
    if action not in ('preview', 'definition', 'binary', 'source'):
        return jsonify(error='Acción desconocida.'), 404
    cfg = validate(json.loads(request.form.get('config', '{}')))
    uploaded = request.files.get('font')
    original = uploaded.filename if uploaded else None
    if action == 'definition':
        return send_file(io.BytesIO(definition(cfg)), mimetype='text/plain', as_attachment=True, download_name=export_name(cfg, 'font880', original))
    uploaded = request.files.get('font')
    bitmaps = render(cfg, uploaded.read() if uploaded else None)
    if action == 'preview':
        return jsonify(glyphs=[''.join('1' if p else '0' for p in bitmap.getdata()) for bitmap in bitmaps],
                       bytes=len(pack(bitmaps)))
    data = pack(bitmaps)
    if action == 'source':
        return send_file(io.BytesIO(c_source(cfg, data)), mimetype='text/plain', as_attachment=True, download_name=export_name(cfg, 'c', original))
    return send_file(io.BytesIO(data), mimetype='application/octet-stream', as_attachment=True, download_name=export_name(cfg, 'rmsfont', original))


@app.errorhandler(413)
def too_large(error):
    return jsonify(error='El archivo supera el límite de 12 MB.'), 413


@app.errorhandler(ValueError)
@app.errorhandler(TypeError)
@app.errorhandler(KeyError)
@app.errorhandler(AttributeError)
def invalid(error):
    message = str(error)
    if message not in TRANSLATIONS and not message.startswith(('El valor debe estar entre ', 'Carga el archivo TTF/OTF de la fuente ')):
        message = 'Datos inválidos.'
    return jsonify(error=message), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
